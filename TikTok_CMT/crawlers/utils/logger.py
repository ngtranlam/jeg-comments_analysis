import threading
import time
import logging
import datetime

from pathlib import Path
from rich.logging import RichHandler
from logging.handlers import TimedRotatingFileHandler


class Singleton(type):
    _instances = {}
    _lock: threading.Lock = threading.Lock()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __call__(cls, *args, **kwargs):
        key = (cls, args, frozenset(kwargs.items()))
        with cls._lock:
            if key not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[key] = instance
        return cls._instances[key]

    @classmethod
    def reset_instance(cls, *args, **kwargs):
        key = (cls, args, frozenset(kwargs.items()))
        with cls._lock:
            if key in cls._instances:
                del cls._instances[key]


class LogManager(metaclass=Singleton):
    def __init__(self):
        if getattr(self, "_initialized", False):
            return

        self.logger = logging.getLogger("Douyin_TikTok_Download_API_Crawlers")
        self.logger.setLevel(logging.INFO)
        self.log_dir = None
        self._initialized = True

    def setup_logging(self, level=logging.INFO, log_to_console=False, log_path=None):
        self.logger.handlers.clear()
        self.logger.setLevel(level)

        if log_to_console:
            ch = RichHandler(
                show_time=False,
                show_path=False,
                markup=True,
                keywords=(RichHandler.KEYWORDS or []) + ["STREAM"],
                rich_tracebacks=True,
            )
            ch.setFormatter(logging.Formatter("{message}", style="{", datefmt="[%X]"))
            self.logger.addHandler(ch)

        if log_path:
            self.log_dir = Path(log_path)
            self.ensure_log_dir_exists(self.log_dir)
            log_file_name = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S.log")
            log_file = self.log_dir.joinpath(log_file_name)
            fh = TimedRotatingFileHandler(
                log_file, when="midnight", interval=1, backupCount=99, encoding="utf-8"
            )
            fh.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
            )
            self.logger.addHandler(fh)

    @staticmethod
    def ensure_log_dir_exists(log_path: Path):
        log_path.mkdir(parents=True, exist_ok=True)

    def clean_logs(self, keep_last_n=10):
        if not self.log_dir:
            return
        all_logs = sorted(self.log_dir.glob("*.log"))
        if keep_last_n == 0:
            files_to_delete = all_logs
        else:
            files_to_delete = all_logs[:-keep_last_n]
        for log_file in files_to_delete:
            try:
                log_file.unlink()
            except PermissionError:
                self.logger.warning(
                    f"Cannot delete log file {log_file}, it is being used by another process"
                )

    def shutdown(self):
        for handler in self.logger.handlers:
            handler.close()
            self.logger.removeHandler(handler)
        self.logger.handlers.clear()
        time.sleep(1)


def log_setup(log_to_console=True):
    logger = logging.getLogger("Douyin_TikTok_Download_API_Crawlers")
    if logger.hasHandlers():
        return logger

    temp_log_dir = Path("./logs")
    temp_log_dir.mkdir(exist_ok=True)

    log_manager = LogManager()
    log_manager.setup_logging(
        level=logging.INFO, log_to_console=log_to_console, log_path=temp_log_dir
    )

    log_manager.clean_logs(1000)

    return logger


logger = log_setup()
