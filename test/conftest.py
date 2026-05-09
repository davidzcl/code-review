import logging
import tempfile
from pathlib import Path

import pytest

from logger import ReviewLogger, LevelFilter


@pytest.fixture
def tmp_log_dir() -> Path:
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def patched_logger(monkeypatch, tmp_log_dir: Path) -> ReviewLogger:
    monkeypatch.setattr("logger.LOG_DIR", str(tmp_log_dir))
    monkeypatch.setattr("logger.LOG_RETENTION_DAYS", 7)
    monkeypatch.setattr("logger.LOG_MAX_BYTES", 1024)
    monkeypatch.setattr("logger.LOG_BACKUP_COUNT", 2)
    monkeypatch.setattr("logger.LOG_LEVEL", "DEBUG")
    monkeypatch.setattr("logger._LOG_LEVEL", "DEBUG")
    monkeypatch.setattr("logger._resolve_log_dir", lambda: tmp_log_dir)
    monkeypatch.setattr("logger._ensure_dir", lambda p: p)
    ReviewLogger._instance = None
    ReviewLogger._initialized = False
    _root = logging.getLogger("review")
    _root.handlers.clear()
    _root.setLevel(logging.DEBUG)
    _root.propagate = True
    logger = ReviewLogger()
    assert logger is not None
    yield logger
    for h in _root.handlers[:]:
        _root.removeHandler(h)
        h.close()
    ReviewLogger._instance = None
    ReviewLogger._initialized = False


@pytest.fixture
def patched_logger_no_init(monkeypatch, tmp_log_dir: Path) -> None:
    monkeypatch.setattr("logger.LOG_DIR", str(tmp_log_dir))
    monkeypatch.setattr("logger.LOG_RETENTION_DAYS", 7)
    monkeypatch.setattr("logger.LOG_MAX_BYTES", 1024)
    monkeypatch.setattr("logger.LOG_BACKUP_COUNT", 2)
    monkeypatch.setattr("logger.LOG_LEVEL", "DEBUG")
    monkeypatch.setattr("logger._LOG_LEVEL", "DEBUG")
    monkeypatch.setattr("logger._resolve_log_dir", lambda: tmp_log_dir)
    monkeypatch.setattr("logger._ensure_dir", lambda p: p)
    ReviewLogger._instance = None
    ReviewLogger._initialized = False
    _root = logging.getLogger("review")
    _root.handlers.clear()
    _root.setLevel(logging.DEBUG)
    _root.propagate = True
    yield
    for h in _root.handlers[:]:
        _root.removeHandler(h)
        h.close()
    ReviewLogger._instance = None
    ReviewLogger._initialized = False


def make_log_record(
    levelno: int,
    msg: str = "test",
    name: str = "review",
) -> logging.LogRecord:
    levelname = logging.getLevelName(levelno)
    return logging.LogRecord(
        name=name,
        level=levelno,
        pathname="",
        lineno=0,
        msg=msg,
        args=(),
        exc_info=None,
    )