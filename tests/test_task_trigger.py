import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from task_trigger import (
    TriggerResult,
    append_log,
    current_window,
    is_due_in_window,
    load_env_file,
)


def _window(h: int, m: int) -> tuple[datetime, datetime]:
    end = datetime(2026, 5, 10, h, m, tzinfo=timezone.utc)
    return end - timedelta(minutes=15), end


class TestLoadEnvFile:
    def test_parses_key_value(self, tmp_path: Path):
        f = tmp_path / ".env"
        f.write_text("FOO=bar\nBAZ=qux\n")
        assert load_env_file(f) == {"FOO": "bar", "BAZ": "qux"}

    def test_skips_comment_lines(self, tmp_path: Path):
        f = tmp_path / ".env"
        f.write_text("# comment\nKEY=value\n")
        assert load_env_file(f) == {"KEY": "value"}

    def test_skips_blank_lines(self, tmp_path: Path):
        f = tmp_path / ".env"
        f.write_text("\nKEY=value\n\n")
        assert load_env_file(f) == {"KEY": "value"}

    def test_returns_empty_for_missing_file(self, tmp_path: Path):
        assert load_env_file(tmp_path / "nonexistent") == {}

    def test_value_with_equals_sign(self, tmp_path: Path):
        f = tmp_path / ".env"
        f.write_text("TOKEN=abc=def\n")
        assert load_env_file(f) == {"TOKEN": "abc=def"}


class TestCurrentWindow:
    def test_truncates_to_15min_boundary(self):
        start, end = current_window()
        assert end.minute % 15 == 0
        assert end.second == 0
        assert end.microsecond == 0

    def test_window_is_15_minutes(self):
        start, end = current_window()
        assert end - start == timedelta(minutes=15)

    def test_returns_utc(self):
        start, end = current_window()
        assert start.tzinfo == timezone.utc
        assert end.tzinfo == timezone.utc


class TestIsDueInWindow:
    def test_matching_task_returns_true(self):
        window = _window(9, 15)
        task = {"due": {"date": "2026-05-10", "datetime": "2026-05-10T09:05:00Z"}}
        assert is_due_in_window(task, window) is True

    def test_no_due_returns_false(self):
        task = {"due": None}
        assert is_due_in_window(task, _window(9, 15)) is False

    def test_missing_due_returns_false(self):
        task = {}
        assert is_due_in_window(task, _window(9, 15)) is False

    def test_all_day_task_returns_false(self):
        task = {"due": {"date": "2026-05-10", "datetime": None}}
        assert is_due_in_window(task, _window(9, 15)) is False

    def test_different_date_returns_false(self):
        task = {"due": {"date": "2026-05-11", "datetime": "2026-05-11T09:05:00Z"}}
        assert is_due_in_window(task, _window(9, 15)) is False

    def test_due_at_window_start_is_included(self):
        window = _window(9, 15)  # [09:00, 09:15)
        task = {"due": {"date": "2026-05-10", "datetime": "2026-05-10T09:00:00Z"}}
        assert is_due_in_window(task, window) is True

    def test_due_at_window_end_is_excluded(self):
        window = _window(9, 15)  # [09:00, 09:15)
        task = {"due": {"date": "2026-05-10", "datetime": "2026-05-10T09:15:00Z"}}
        assert is_due_in_window(task, window) is False

    def test_due_before_window_returns_false(self):
        window = _window(9, 15)
        task = {"due": {"date": "2026-05-10", "datetime": "2026-05-10T08:59:00Z"}}
        assert is_due_in_window(task, window) is False


class TestAppendLog:
    def test_creates_parent_directory(self, tmp_path: Path):
        log = tmp_path / "nested" / "dir" / "log.jsonl"
        result = TriggerResult("id1", "task", "ok", "prompt", "output", "2026-05-10T00:00:00+00:00")
        append_log(result, log)
        assert log.exists()

    def test_writes_json_line(self, tmp_path: Path):
        log = tmp_path / "log.jsonl"
        result = TriggerResult("id1", "タスク名", "ok", "prompt", "output", "2026-05-10T00:00:00+00:00")
        append_log(result, log)
        data = json.loads(log.read_text())
        assert data["task_id"] == "id1"
        assert data["task_name"] == "タスク名"
        assert data["status"] == "ok"

    def test_appends_multiple_lines(self, tmp_path: Path):
        log = tmp_path / "log.jsonl"
        r1 = TriggerResult("id1", "t1", "ok", "", "", "2026-05-10T00:00:00+00:00")
        r2 = TriggerResult("id2", "t2", "skip_no_comment", "", "", "2026-05-10T00:01:00+00:00")
        append_log(r1, log)
        append_log(r2, log)
        lines = log.read_text().strip().splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["task_id"] == "id1"
        assert json.loads(lines[1])["task_id"] == "id2"
