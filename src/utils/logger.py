"""日志工具 — 双输出（stderr + 按天滚动文件），模块级 logger"""

from __future__ import annotations

import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

_LOGGER_NAME_ROOT = "book-reader"
_INITIALIZED = False


def _log_dir() -> Path:
    """日志目录：~/.claude-book-reader/logs/"""
    from core.config import Config
    try:
        return Config().data_dir / "logs"
    except Exception:
        return Path.home() / ".claude-book-reader" / "logs"


def init_logging(level: int = logging.INFO, log_to_file: bool = True) -> None:
    """初始化根 logger。幂等。

    - 控制台输出到 stderr
    - 文件按天滚动，保留 7 天
    """
    global _INITIALIZED
    if _INITIALIZED:
        return

    root = logging.getLogger(_LOGGER_NAME_ROOT)
    root.setLevel(level)
    root.propagate = False

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # stderr handler
    sh = logging.StreamHandler(sys.stderr)
    sh.setLevel(level)
    sh.setFormatter(fmt)
    root.addHandler(sh)

    # rotating file handler
    if log_to_file:
        try:
            log_dir = _log_dir()
            log_dir.mkdir(parents=True, exist_ok=True)
            fh = TimedRotatingFileHandler(
                log_dir / "app.log",
                when="midnight",
                interval=1,
                backupCount=7,
                encoding="utf-8",
            )
            fh.setLevel(level)
            fh.setFormatter(fmt)
            root.addHandler(fh)
        except Exception as e:  # pragma: no cover
            root.warning("Failed to initialize file logger: %s", e)

    _INITIALIZED = True


def get_logger(name: str) -> logging.Logger:
    """模块级 logger。`name` 通常传 `__name__`。"""
    if not _INITIALIZED:
        init_logging()
    if name.startswith(_LOGGER_NAME_ROOT):
        return logging.getLogger(name)
    return logging.getLogger(f"{_LOGGER_NAME_ROOT}.{name}")


# 兼容旧调用 setup_logger
def setup_logger(name: str = _LOGGER_NAME_ROOT, level: int = logging.INFO) -> logging.Logger:
    init_logging(level=level)
    return get_logger(name)
