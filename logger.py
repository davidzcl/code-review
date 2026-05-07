"""
全局日志系统

基于单例模式实现，提供：
- 日志轮转（RotatingFileHandler）
- 控制台 + 文件双重输出
- 线程安全（初始化锁 + logging 模块原生线程安全）
- 多级别支持：DEBUG / INFO / WARNING / ERROR / CRITICAL
- 组件级别日志记录（get_logger）
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from threading import Lock
from typing import Dict, Optional

from config import (
    LOG_BACKUP_COUNT,
    LOG_DATE_FORMAT,
    LOG_DIR,
    LOG_FORMAT,
    LOG_LEVEL,
    LOG_MAX_BYTES,
)


# 默认配置（从 config 模块读取，config 已通过 dotenv 加载 .env）
_LOG_LEVEL = LOG_LEVEL.upper()

LEVEL_MAP: Dict[str, int] = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def _resolve_log_dir() -> Path:
    """确定日志目录路径"""
    if LOG_DIR:
        return Path(LOG_DIR).resolve()
    return Path.cwd() / "logs"


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


class ReviewLogger:
    """全局日志管理器（单例）

    管理日志基础设施（handlers、formatters），
    各组件通过 get_logger() 获取子 logger。
    """

    _instance: Optional["ReviewLogger"] = None
    _lock: Lock = Lock()
    _initialized: bool = False

    def __new__(cls) -> "ReviewLogger":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return

            level = LEVEL_MAP.get(_LOG_LEVEL, logging.INFO)
            log_dir = _ensure_dir(_resolve_log_dir())

            formatter = logging.Formatter(
                fmt=LOG_FORMAT,
                datefmt=LOG_DATE_FORMAT,
            )

            self._root_logger = logging.getLogger("review")
            self._root_logger.setLevel(level)
            self._root_logger.handlers.clear()
            self._root_logger.propagate = False

            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            console_handler.setFormatter(formatter)
            self._root_logger.addHandler(console_handler)

            file_handler = RotatingFileHandler(
                filename=str(log_dir / "review.log"),
                maxBytes=LOG_MAX_BYTES,
                backupCount=LOG_BACKUP_COUNT,
                encoding="utf-8",
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            self._root_logger.addHandler(file_handler)

            self._level = level
            self._log_dir = log_dir
            self._initialized = True

    @property
    def log_dir(self) -> Path:
        return self._log_dir

    def get_logger(self, name: str) -> logging.Logger:
        """获取组件级别的子 logger

        Args:
            name: 组件名称，如 'tools.diff_parser'、'agents.security'

        Returns:
            review.{name} 的子 logger，共享根 logger 的 handlers
        """
        return self._root_logger.getChild(name)

    def debug(self, message: str, *args, **kwargs) -> None:
        self._root_logger.debug(message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs) -> None:
        self._root_logger.info(message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs) -> None:
        self._root_logger.warning(message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs) -> None:
        self._root_logger.error(message, *args, **kwargs)

    def critical(self, message: str, *args, **kwargs) -> None:
        self._root_logger.critical(message, *args, **kwargs)

    def set_level(self, level_name: str) -> None:
        """运行时动态调整日志级别

        Args:
            level_name: DEBUG / INFO / WARNING / ERROR / CRITICAL
        """
        level = LEVEL_MAP.get(level_name.upper())
        if level is None:
            raise ValueError(f"不支持的日志级别: {level_name}")
        self._root_logger.setLevel(level)
        for handler in self._root_logger.handlers:
            handler.setLevel(level)
        self._level = level


logger = ReviewLogger()
