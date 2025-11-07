from __future__ import annotations

import asyncio
import asyncio.subprocess
import inspect
import os
import signal
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from arch_me_later.logs import logger

if TYPE_CHECKING:
    pass

LineCallback = Callable[[str], None] | Callable[[str], Awaitable[None]]


@dataclass(frozen=True)
class ModuleSpec:
    """
    Declarative spec for a single module run.
    - name: unique identifier
    - cmd: argv-style command to execute
    - path: working directory for the module (defaults used inside executor)
    - env: additional environment vars for the module
    - timeout: optional timeout in seconds (None means no timeout)
    - check: raise on non-zero exit if True
    - deps: list of names this module depends on; all must complete first
    - stdout_cb / stderr_cb: per-module streaming callbacks (optional).
        If None, Orchestrator defaults are used. If stderr_cb is None at execution
        time, stderr is merged into stdout.
    """

    name: str
    cmd: Sequence[str]
    path: Path
    env: Mapping[str, str] | None = None
    timeout: float | None = None
    check: bool = True
    deps: list[str] = field(default_factory=list)
    stdout_cb: LineCallback | None = None
    stderr_cb: LineCallback | None = None


class ProcessError(RuntimeError):
    def __init__(self, cmd: Sequence[str], returncode: int):
        super().__init__(f"Command failed with exit code {returncode}: {list(cmd)}")
        self.cmd = list(cmd)
        self.returncode = returncode


class ModuleExecutor:
    """Executor for managing module subprocesses."""

    def __init__(self, module_path: Path, env: dict[str, str] | None = None) -> None:
        self.module_path: Path = module_path
        self.process: asyncio.subprocess.Process | None = None
        self.env: dict[str, str] = self._build_env(env)

    def _build_env(self, env: dict[str, str] | None) -> dict[str, str]:
        base_env = os.environ.copy()
        if env:
            base_env.update(env)
        return base_env

    async def _dispatch(self, cb: LineCallback, text: str) -> None:
        """Run a callback without blocking the event loop."""
        try:
            if inspect.iscoroutinefunction(cb):
                await cb(text)
            else:
                await asyncio.to_thread(cb, text)
        except Exception:
            # Log the exception from the callback without blocking the loop.
            await asyncio.to_thread(logger.error, "Callback raised", exc_info=True)

    async def _read_stream(
        self,
        stream: asyncio.StreamReader,
        cb: LineCallback,
        *,
        encoding: str = "utf-8",
        errors: str = "replace",
        strip_newline: bool = True,
    ) -> None:
        """Read a stream line-by-line and feed lines to cb()."""
        while True:
            line = await stream.readline()
            if not line:
                break
            text = line.decode(encoding, errors)
            if strip_newline:
                text = text.rstrip("\r\n")
            await self._dispatch(cb, text)

    async def execute(
        self,
        cmd: Sequence[str],
        *,
        stdout_cb: LineCallback,
        stderr_cb: LineCallback | None = None,
        cwd: str | Path | None = None,
        env: dict[str, str] | None = None,
        encoding: str = "utf-8",
        errors: str = "replace",
        timeout: float | None = None,
        check: bool = False,
        terminate_grace: float = 5.0,
    ) -> int:
        """
        Spawn a subprocess and stream its output.

        Returns the exit code. If check=True, raises ProcessError on non-zero exit.
        """
        # Default working directory is the module's path; accept Path for convenience.
        cwd_path = str(cwd) if cwd is not None else str(self.module_path)

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
            if stderr_cb is not None
            else asyncio.subprocess.STDOUT,
            cwd=cwd_path,
            env=self._build_env(env),
            start_new_session=True,  # new session/PGID so we can kill the whole tree
        )
        self.process = proc

        tasks: list[asyncio.Task[None]] = []
        if proc.stdout is not None:
            tasks.append(
                asyncio.create_task(
                    self._read_stream(
                        proc.stdout, stdout_cb, encoding=encoding, errors=errors
                    )
                )
            )

        if stderr_cb is not None and proc.stderr is not None:
            tasks.append(
                asyncio.create_task(
                    self._read_stream(
                        proc.stderr, stderr_cb, encoding=encoding, errors=errors
                    )
                )
            )
        try:
            if timeout is None:
                rc = await proc.wait()
            else:
                rc = await asyncio.wait_for(proc.wait(), timeout=timeout)

            if tasks:
                await asyncio.gather(*tasks)

            if check and rc != 0:
                raise ProcessError(cmd, rc)
            return rc

        except (asyncio.TimeoutError, asyncio.CancelledError):
            if proc.returncode is None:
                try:
                    if hasattr(os, "killpg"):
                        os.killpg(proc.pid, signal.SIGTERM)
                    elif hasattr(signal, "CTRL_BREAK_EVENT"):
                        proc.send_signal(signal.CTRL_BREAK_EVENT)
                    else:
                        proc.terminate()
                except ProcessLookupError:
                    pass

                try:
                    await asyncio.wait_for(proc.wait(), timeout=terminate_grace)
                except asyncio.TimeoutError:
                    try:
                        if hasattr(os, "killpg") and hasattr(signal, "SIGKILL"):
                            os.killpg(proc.pid, signal.SIGKILL)
                        else:
                            proc.kill()
                    except ProcessLookupError:
                        pass
                    await proc.wait()

            for t in tasks:
                t.cancel()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            raise

        except Exception:
            if proc.returncode is None:
                try:
                    if hasattr(os, "killpg") and hasattr(signal, "SIGKILL"):
                        os.killpg(proc.pid, signal.SIGKILL)
                    else:
                        proc.kill()
                except ProcessLookupError:
                    pass
                await proc.wait()
            for t in tasks:
                t.cancel()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            raise

        finally:
            self.process = None
