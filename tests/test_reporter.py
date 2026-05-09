from datetime import datetime, timedelta

from optimizer import ScheduleResult
from reporter import report
from slot_generator import TimeSlot
from task_parser import ParseError, ParsedTask


def _slot(h: int, m: int) -> TimeSlot:
    start = datetime(2026, 5, 9, h, m)
    return TimeSlot(start=start, end=start + timedelta(minutes=15))


def _task(id: str, content: str, duration_hours: float = 1.0) -> ParsedTask:
    return ParsedTask(id=id, content=content, duration_hours=duration_hours, slots_needed=4)


class TestReport:
    def test_scheduled_tasks_appear_in_stdout(self, capsys):
        result = ScheduleResult(scheduled=[(_task("1", "実装作業"), _slot(9, 0))])
        report(result, [])
        out = capsys.readouterr().out
        assert "09:00" in out
        assert "実装作業" in out
        assert "1.0h" in out

    def test_header_always_printed(self, capsys):
        report(ScheduleResult(), [])
        out = capsys.readouterr().out
        assert "スケジュール結果" in out

    def test_parse_errors_appear_in_stderr(self, capsys):
        errors = [ParseError(id="1", content="タスクA", reason="description が空です")]
        report(ScheduleResult(), errors)
        err = capsys.readouterr().err
        assert "[SKIP]" in err
        assert "タスクA" in err
        assert "description が空です" in err

    def test_unscheduled_tasks_appear_in_stderr(self, capsys):
        result = ScheduleResult(unscheduled=[_task("1", "大型タスク", duration_hours=8.0)])
        report(result, [])
        err = capsys.readouterr().err
        assert "[WARN]" in err
        assert "大型タスク" in err
        assert "8.0h" in err

    def test_parse_errors_not_in_stdout(self, capsys):
        errors = [ParseError(id="1", content="タスクA", reason="空")]
        report(ScheduleResult(), errors)
        out = capsys.readouterr().out
        assert "SKIP" not in out
        assert "タスクA" not in out

    def test_scheduled_tasks_not_in_stderr(self, capsys):
        result = ScheduleResult(scheduled=[(_task("1", "実装"), _slot(9, 0))])
        report(result, [])
        err = capsys.readouterr().err
        assert "実装" not in err

    def test_multiple_scheduled_tasks_in_order(self, capsys):
        result = ScheduleResult(
            scheduled=[
                (_task("1", "タスクA"), _slot(9, 0)),
                (_task("2", "タスクB"), _slot(10, 0)),
            ]
        )
        report(result, [])
        out = capsys.readouterr().out
        assert out.index("09:00") < out.index("10:00")
