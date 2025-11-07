from __future__ import annotations

import asyncio
from collections.abc import Sequence

from arch_me_later.modules.executor import (
    LineCallback,
    ModuleExecutor,
    ModuleSpec,
)


class OrchestrationError(Exception):
    """Raised when one or more modules fail in non-fail-fast mode."""

    def __init__(self, failures: dict[str, BaseException]):
        super().__init__(
            f"{len(failures)} module(s) failed: {', '.join(failures.keys())}"
        )
        self.failures = failures


class PipelineOrchestrator:
    """
    Run a DAG of modules with optional concurrency limits.

    Scheduling policy:
      - Dependencies are respected via topological "levels".
      - Each level runs with up to `concurrency` modules at once (guarded by a semaphore).
      - If `fail_fast=True`, any failure in a level cancels its siblings and aborts the run.
        Otherwise, execution continues and failures are collected and raised at the end.
    """

    def __init__(
        self,
        modules: Sequence[ModuleSpec],
        *,
        concurrency: int = 1,
        default_stdout_cb: LineCallback | None = None,
        default_stderr_cb: LineCallback | None = None,
        fail_fast: bool = True,
    ) -> None:
        if concurrency < 1:
            raise ValueError("concurrency must be >= 1")
        self._modules = {m.name: m for m in modules}
        if len(self._modules) != len(modules):
            raise ValueError("Duplicate module names are not allowed")
        self._concurrency = concurrency
        self._default_stdout_cb = default_stdout_cb or (lambda s: None)
        self._default_stderr_cb = default_stderr_cb
        self._levels = self._topological_levels()
        self._fail_fast = fail_fast

    def _topological_levels(self) -> list[list[str]]:
        """Return a list of levels, each a list of module names with no mutual deps."""
        # Validate deps exist
        for m in self._modules.values():
            for dep in m.deps:
                if dep not in self._modules:
                    raise ValueError(f"Module '{m.name}' depends on unknown '{dep}'")

        # Kahn's algorithm producing levels
        indeg: dict[str, int] = {name: 0 for name in self._modules}
        children: dict[str, list[str]] = {name: [] for name in self._modules}
        for name, m in self._modules.items():
            for dep in m.deps:
                indeg[name] += 1
                children[dep].append(name)

        levels: list[list[str]] = []
        frontier = [name for name, d in indeg.items() if d == 0]
        seen = 0

        while frontier:
            level = sorted(frontier)
            levels.append(level)
            new_frontier: list[str] = []
            for n in level:
                seen += 1
                for c in children[n]:
                    indeg[c] -= 1
                    if indeg[c] == 0:
                        new_frontier.append(c)
            frontier = new_frontier

        if seen != len(self._modules):
            raise ValueError("Dependency graph has a cycle")
        return levels

    async def _run_one(
        self,
        spec: ModuleSpec,
        sem: asyncio.Semaphore,
        results: dict[str, int],
    ) -> None:
        async with sem:
            exe = ModuleExecutor(
                module_path=spec.path, env=dict(spec.env) if spec.env else None
            )
            rc = await exe.execute(
                spec.cmd,
                stdout_cb=spec.stdout_cb or self._default_stdout_cb,
                stderr_cb=spec.stderr_cb
                if spec.stderr_cb is not None
                else self._default_stderr_cb,
                timeout=spec.timeout,
                check=spec.check,
            )
            results[spec.name] = rc

    async def run(self) -> dict[str, int]:
        """
        Execute the DAG. Returns a mapping of module name -> return code.
        - If fail_fast=True, the first failure aborts and propagates the error.
        - If fail_fast=False, all modules are attempted; failures are aggregated in
          OrchestrationError at the end (results still returns successes).
        """
        sem = asyncio.Semaphore(self._concurrency)
        results: dict[str, int] = {}
        failures: dict[str, BaseException] = {}

        for level in self._levels:
            if self._fail_fast and failures:
                break

            if self._fail_fast:
                # Fail fast: one error cancels siblings in this level.
                async with asyncio.TaskGroup() as tg:
                    for name in level:
                        spec = self._modules[name]

                        async def runner(s: ModuleSpec) -> None:
                            await self._run_one(s, sem, results)

                        tg.create_task(runner(spec))
                # Any exception inside runner will propagate and cancel the group,
                # aborting the whole orchestrator (as intended).
            else:
                # Collect errors, continue to next level.
                tasks = [
                    asyncio.create_task(
                        self._run_one(self._modules[name], sem, results)
                    )
                    for name in level
                ]
                done = await asyncio.gather(*tasks, return_exceptions=True)
                for name, res in zip(level, done):
                    if isinstance(res, BaseException):
                        failures[name] = res

        if failures and not self._fail_fast:
            raise OrchestrationError(failures)

        return results
