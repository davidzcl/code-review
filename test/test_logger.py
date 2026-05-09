import datetime
import logging
from pathlib import Path

import pytest

from logger import LevelFilter, ReviewLogger


class TestLevelFilter:
    def test_accepts_error(self):
        f = LevelFilter(logging.ERROR, logging.CRITICAL)
        assert f.filter(_make_record(logging.ERROR))
        assert f.filter(_make_record(logging.CRITICAL))

    def test_rejects_info(self):
        f = LevelFilter(logging.ERROR, logging.CRITICAL)
        assert not f.filter(_make_record(logging.DEBUG))
        assert not f.filter(_make_record(logging.INFO))
        assert not f.filter(_make_record(logging.WARNING))

    def test_info_filter_accepts_low(self):
        f = LevelFilter(0, logging.WARNING)
        assert f.filter(_make_record(logging.DEBUG))
        assert f.filter(_make_record(logging.INFO))
        assert f.filter(_make_record(logging.WARNING))

    def test_info_filter_rejects_high(self):
        f = LevelFilter(0, logging.WARNING)
        assert not f.filter(_make_record(logging.ERROR))
        assert not f.filter(_make_record(logging.CRITICAL))


class TestReviewLoggerSingleton:
    def test_singleton(self, patched_logger_no_init):
        a = ReviewLogger()
        b = ReviewLogger()
        assert a is b

    def test_get_logger_child(self, patched_logger):
        child = patched_logger.get_logger("test.comp")
        assert child.name == "review.test.comp"
        assert child.parent is patched_logger._root_logger


class TestLogSeparation:
    """error 日志与 info 日志完全分离。"""

    def test_error_writes_to_error_log(self, patched_logger, tmp_log_dir):
        patched_logger.error("err msg")
        error_log = tmp_log_dir / "error.log"
        info_log = tmp_log_dir / "info.log"
        assert error_log.exists()
        content = error_log.read_text("utf-8")
        assert "err msg" in content

    def test_info_does_not_write_to_error_log(self, patched_logger, tmp_log_dir):
        patched_logger.info("info msg")
        error_log = tmp_log_dir / "error.log"
        assert error_log.exists()
        content = error_log.read_text("utf-8")
        assert "info msg" not in content

    def test_info_writes_to_info_log(self, patched_logger, tmp_log_dir):
        patched_logger.info("info msg")
        info_log = tmp_log_dir / "info.log"
        assert info_log.exists()
        content = info_log.read_text("utf-8")
        assert "info msg" in content

    def test_error_does_not_write_to_info_log(self, patched_logger, tmp_log_dir):
        patched_logger.error("err msg")
        info_log = tmp_log_dir / "info.log"
        assert info_log.exists()
        content = info_log.read_text("utf-8")
        assert "err msg" not in content

    def test_warning_goes_to_info_not_error(self, patched_logger, tmp_log_dir):
        patched_logger.warning("warn msg")
        info_log = tmp_log_dir / "info.log"
        error_log = tmp_log_dir / "error.log"
        assert "warn msg" in info_log.read_text("utf-8")
        assert "warn msg" not in error_log.read_text("utf-8")

    def test_critical_goes_to_error_not_info(self, patched_logger, tmp_log_dir):
        patched_logger.critical("crit msg")
        info_log = tmp_log_dir / "info.log"
        error_log = tmp_log_dir / "error.log"
        assert "crit msg" in error_log.read_text("utf-8")
        assert "crit msg" not in info_log.read_text("utf-8")


class TestDailyFiles:
    def test_daily_file_created_on_init(self, patched_logger, tmp_log_dir):
        today = datetime.date.today().isoformat()
        error_daily = tmp_log_dir / f"error.{today}.log"
        info_daily = tmp_log_dir / f"info.{today}.log"
        assert error_daily.exists()
        assert info_daily.exists()

    def test_daily_file_receives_correct_records(self, patched_logger, tmp_log_dir):
        today = datetime.date.today().isoformat()
        patched_logger.error("daily err")
        patched_logger.info("daily info")
        error_daily = tmp_log_dir / f"error.{today}.log"
        info_daily = tmp_log_dir / f"info.{today}.log"
        assert "daily err" in error_daily.read_text("utf-8")
        assert "daily info" in info_daily.read_text("utf-8")
        assert "daily info" not in error_daily.read_text("utf-8")
        assert "daily err" not in info_daily.read_text("utf-8")


class TestCleanup:
    def _create_old_file(self, log_dir: Path, prefix: str, days_ago: int) -> Path:
        date = datetime.date.today() - datetime.timedelta(days=days_ago)
        f = log_dir / f"{prefix}.{date.isoformat()}.log"
        f.write_text("old content", encoding="utf-8")
        return f

    def test_removes_expired_files(self, tmp_log_dir):
        old = self._create_old_file(tmp_log_dir, "error", 10)
        ReviewLogger._cleanup_daily_logs(tmp_log_dir, 7)
        assert not old.exists()

    def test_keeps_recent_files(self, tmp_log_dir):
        recent = self._create_old_file(tmp_log_dir, "error", 3)
        ReviewLogger._cleanup_daily_logs(tmp_log_dir, 7)
        assert recent.exists()

    def test_keeps_edge_day(self, tmp_log_dir):
        edge = self._create_old_file(tmp_log_dir, "info", 7)
        ReviewLogger._cleanup_daily_logs(tmp_log_dir, 7)
        assert edge.exists()

    def test_skips_non_matching_files(self, tmp_log_dir):
        unrelated = tmp_log_dir / "review.log"
        unrelated.write_text("content", encoding="utf-8")
        random_file = tmp_log_dir / "random.txt"
        random_file.write_text("content", encoding="utf-8")
        ReviewLogger._cleanup_daily_logs(tmp_log_dir, 7)
        assert unrelated.exists()
        assert random_file.exists()

    def test_info_and_error_both_cleaned(self, tmp_log_dir):
        old_error = self._create_old_file(tmp_log_dir, "error", 10)
        old_info = self._create_old_file(tmp_log_dir, "info", 15)
        ReviewLogger._cleanup_daily_logs(tmp_log_dir, 7)
        assert not old_error.exists()
        assert not old_info.exists()

    def test_malformed_date_skipped(self, tmp_log_dir):
        bad = tmp_log_dir / "error.bad-date.log"
        bad.write_text("content", encoding="utf-8")
        ReviewLogger._cleanup_daily_logs(tmp_log_dir, 7)
        assert bad.exists()


def _make_record(levelno: int) -> logging.LogRecord:
    return logging.LogRecord(
        name="test",
        level=levelno,
        pathname="",
        lineno=0,
        msg="test",
        args=(),
        exc_info=None,
    )