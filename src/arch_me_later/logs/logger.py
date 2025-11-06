from __future__ import annotations

import logging
from datetime import datetime
from enum import IntEnum
from pathlib import Path
from typing import TYPE_CHECKING

from rich.markup import escape

if TYPE_CHECKING:
    from textual.widgets import RichLog


class LogLevel(IntEnum):
    DEBUG = 10
    LOG = 15
    INFO = 20
    STATUS = 25
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


class Logger:
    """Project-wide singleton logger.

    Configure once with a Textual RichLog widget and optional log directory,
    then call Logger.info/debug/... anywhere without creating new objects.
    """

    _logger: logging.Logger | None = None
    _configured: bool = False

    @classmethod
    def configure(
        cls, log_widget: "RichLog", log_dir: Path | None = None
    ) -> logging.Logger:
        if cls._configured and cls._logger is not None:
            return cls._logger

        if log_dir is None:
            log_dir = Path.home() / ".local" / "state" / "arch_me_later" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file: Path = log_dir / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}.log"

        logging.addLevelName(LogLevel.LOG, "LOG")
        logging.addLevelName(LogLevel.STATUS, "STATUS")

        logger: logging.Logger = logging.getLogger("arch_me_later")
        logger.setLevel(LogLevel.DEBUG)
        logger.propagate = False

        # File handler (add once)
        if not any(isinstance(h, ArchMeFileHandler) for h in logger.handlers):
            file_handler: ArchMeFileHandler = ArchMeFileHandler(log_file)
            file_formatter = logging.Formatter(
                fmt="[{asctime}][{levelname}] {message}",
                style="{",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            file_handler.setFormatter(file_formatter)
            file_handler.setLevel(LogLevel.DEBUG)
            logger.addHandler(file_handler)
            _write_log_header(logger, log_file)

        # Widget handler (replace existing to point to current widget)
        for h in list(logger.handlers):
            if isinstance(h, ArchMeWidgetHandler):
                logger.removeHandler(h)
        widget_handler: ArchMeWidgetHandler = ArchMeWidgetHandler(log_widget)
        widget_handler.setLevel(LogLevel.LOG)
        logger.addHandler(widget_handler)

        cls._logger = logger
        cls._configured = True
        return logger

    @classmethod
    def get(cls) -> logging.Logger:
        if cls._logger is None:
            return logging.getLogger("arch_me_later")
        return cls._logger

    @classmethod
    def debug(cls, msg: str, *args, **kwargs) -> None:
        cls.get().debug(msg, *args, **kwargs)

    @classmethod
    def log(cls, msg: str, *args, **kwargs) -> None:
        cls.get().log(LogLevel.LOG, msg, *args, **kwargs)

    @classmethod
    def info(cls, msg: str, *args, **kwargs) -> None:
        cls.get().info(msg, *args, **kwargs)

    @classmethod
    def status(cls, msg: str, *args, **kwargs) -> None:
        cls.get().log(LogLevel.STATUS, msg, *args, **kwargs)

    @classmethod
    def warning(cls, msg: str, *args, **kwargs) -> None:
        cls.get().warning(msg, *args, **kwargs)

    @classmethod
    def error(cls, msg: str, *args, **kwargs) -> None:
        cls.get().error(msg, *args, **kwargs)

    @classmethod
    def critical(cls, msg: str, *args, **kwargs) -> None:
        cls.get().critical(msg, *args, **kwargs)


def get_logger(log_widget: "RichLog", log_dir: Path | None = None) -> logging.Logger:
    """Backward-compatible helper: configure the singleton and return it."""
    return Logger.configure(log_widget=log_widget, log_dir=log_dir)


def _write_log_header(logger: logging.Logger, log_file: Path) -> None:
    # Write a formatted header to the log file only
    header = (
        "========================================\n"
        "         Arch Me Later Log File        \n"
        f"        Created on {datetime.now()}        \n"
        "========================================\n\n"
    )
    with log_file.open("a", encoding="utf-8") as f:
        f.write(header)
    msg = f"Log file created at {log_file}"
    logger.debug(msg)


class ArchMeFileHandler(logging.FileHandler):
    def __init__(
        self, filename: str | Path, mode: str = "a", encoding: str = "utf-8"
    ) -> None:
        super().__init__(filename, mode, encoding)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = escape(record.getMessage())
            record.msg = message
            record.args = None
        except Exception:
            pass
        super().emit(record)


class ArchMeWidgetHandler(logging.Handler):
    def __init__(self, log_widget: RichLog) -> None:
        super().__init__()
        self.log_widget = log_widget

    def emit(self, record: logging.LogRecord) -> None:
        log_entry = self.format(record)
        if self.log_widget:
            app = getattr(self.log_widget, "app", None)
            if not app:
                return
            try:
                import threading

                if hasattr(app, "_thread_id") and threading.get_ident() != getattr(
                    app, "_thread_id"
                ):
                    app.call_from_thread(self.log_widget.write, log_entry)
                else:
                    self.log_widget.write(log_entry)
            except Exception:
                self.log_widget.write(log_entry)

    def format(self, record: logging.LogRecord) -> str:
        msg = record.getMessage()
        timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        level = record.levelno
        match level:
            case LogLevel.DEBUG:
                formated_msg = f"[{timestamp}][dim][DEBUG][/dim] {msg}"
            case LogLevel.LOG:
                formated_msg = f"[{timestamp}][cyan][LOG][/cyan] {msg}"
            case LogLevel.INFO:
                formated_msg = f"[{timestamp}][green][INFO][/green] {msg}"
            case LogLevel.STATUS:
                formated_msg = f"[{timestamp}][blue][STATUS][/blue] {msg}"
            case LogLevel.WARNING:
                formated_msg = f"[{timestamp}][yellow][WARNING][/yellow] {msg}"
            case LogLevel.ERROR:
                formated_msg = f"[{timestamp}][red][ERROR][/red] {msg}"
            case LogLevel.CRITICAL:
                formated_msg = f"[{timestamp}][bold red][CRITICAL][/bold red] {msg}"
            case _:
                formated_msg = f"[{timestamp}] {msg}"

        return formated_msg
