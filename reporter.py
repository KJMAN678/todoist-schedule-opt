import sys
from task_parser import ParseError
from optimizer import ScheduleResult


def report(result: ScheduleResult, errors: list[ParseError]) -> None:
    for error in errors:
        print(f"[SKIP] {error.content}: {error.reason}", file=sys.stderr)

    for task in result.unscheduled:
        print(
            f"[WARN] '{task.content}' ({task.duration_hours}h) は時間内に収まりませんでした",
            file=sys.stderr,
        )

    print("=== スケジュール結果 ===")
    for task, slot in result.scheduled:
        print(
            f"  {slot.start.strftime('%H:%M')} [{task.duration_hours}h] {task.content}"
        )
