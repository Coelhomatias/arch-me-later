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
    """Project-wide singleton logger with late RichLog registration support."""

    _logger: logging.Logger | None = None
    _configured: bool = False

    @classmethod
    def configure(
        cls, log_widget: "RichLog | None" = None, log_dir: Path | None = None
    ) -> logging.Logger:
        """Configure the application logger.

        Can be called early (without a widget) to set up file logging,
        and later a RichLog widget can be registered via `register_rich_log`.
        If a widget is provided here, it will be attached as well.
        """

        # Ensure custom levels are registered every time; harmless if repeated
        logging.addLevelName(LogLevel.LOG, "LOG")
        logging.addLevelName(LogLevel.STATUS, "STATUS")

        # Create or reuse the logger singleton
        logger: logging.Logger = (
            cls._logger
            if cls._logger is not None
            else logging.getLogger("arch_me_later")
        )
        logger.setLevel(LogLevel.DEBUG)
        logger.propagate = False

        # Ensure file handler exists (create log directory/file lazily)
        if log_dir is None:
            log_dir = Path.home() / ".local" / "state" / "arch_me_later" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        # Only create a new file handler once per process
        if not any(isinstance(h, ArchMeFileHandler) for h in logger.handlers):
            log_file: Path = log_dir / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}.log"
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

        # Optionally attach a RichLog widget handler now
        if log_widget is not None:
            cls._attach_widget_handler(logger, log_widget)

        cls._logger = logger
        cls._configured = True
        return logger

    @classmethod
    def register_rich_log(cls, log_widget: RichLog) -> None:
        """Register or replace the RichLog handler after widget initialization.

        Safe to call multiple times; the previous widget handler will be replaced.
        Automatically configures the logger (file handler) if not done yet.
        """
        # Ensure base config exists
        if not cls._configured or cls._logger is None:
            cls.configure(log_widget=None)

        assert cls._logger is not None  # for type checkers
        cls._attach_widget_handler(cls._logger, log_widget)

    @staticmethod
    def _attach_widget_handler(logger: logging.Logger, log_widget: RichLog) -> None:
        # Remove any existing widget handlers to avoid duplicates
        for h in list(logger.handlers):
            if isinstance(h, ArchMeWidgetHandler):
                logger.removeHandler(h)
        widget_handler: ArchMeWidgetHandler = ArchMeWidgetHandler(log_widget)
        widget_handler.setLevel(LogLevel.LOG)
        logger.addHandler(widget_handler)

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
        # Create a copy to avoid mutating the original record (which goes to other handlers)
        try:
            original_msg = record.msg
            original_args = record.args
            # Escape markup for plain text file output
            record.msg = escape(record.getMessage())
            record.args = None
            super().emit(record)
        except Exception:
            super().emit(record)
        finally:
            # Restore original so other handlers get unescaped markup
            record.msg = original_msg
            record.args = original_args


class ArchMeWidgetHandler(logging.Handler):
    def __init__(self, log_widget: RichLog) -> None:
        super().__init__()
        self.log_widget = log_widget

    def emit(self, record: logging.LogRecord) -> None:
        try:
            log_entry = self.format(record)
            if self.log_widget:
                self.log_widget.write(log_entry)
        except Exception:
            self.handleError(record)

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
