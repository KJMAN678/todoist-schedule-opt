import argparse
import asyncio
import os
from datetime import date, time

from slot_generator import generate_slots
from task_parser import parse
from optimizer import schedule
from todoist_client import create_client_session
from reporter import report

DEFAULT_PROJECT_ID = os.environ.get("TODOIST_PROJECT_ID")


def _parse_time(value: str) -> time:
    try:
        h, m = value.split(":")
        return time(int(h), int(m))
    except (ValueError, AttributeError):
        raise argparse.ArgumentTypeError(
            f"時刻は HH:MM 形式で指定してください: '{value}'"
        )


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"日付は YYYY-MM-DD 形式で指定してください: '{value}'"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Todoist タスク最適スケジューリング")
    parser.add_argument("--project-id", default=DEFAULT_PROJECT_ID)
    parser.add_argument("--start", required=True, type=_parse_time, metavar="HH:MM")
    parser.add_argument("--end", required=True, type=_parse_time, metavar="HH:MM")
    parser.add_argument(
        "--lunch-start", type=_parse_time, metavar="HH:MM", default=None
    )
    parser.add_argument("--lunch-end", type=_parse_time, metavar="HH:MM", default=None)
    parser.add_argument(
        "--date", type=_parse_date, default=date.today(), metavar="YYYY-MM-DD"
    )

    args = parser.parse_args()

    if args.start >= args.end:
        parser.error("--start は --end より前の時刻を指定してください")

    lunch_args = (args.lunch_start, args.lunch_end)
    if any(x is not None for x in lunch_args) and not all(
        x is not None for x in lunch_args
    ):
        parser.error(
            "--lunch-start と --lunch-end は両方指定するか、両方省略してください"
        )

    if args.lunch_start and args.lunch_end:
        if args.lunch_start >= args.lunch_end:
            parser.error("--lunch-start は --lunch-end より前の時刻を指定してください")
        if args.lunch_start < args.start or args.lunch_end > args.end:
            parser.error(
                "ランチ時間帯は作業時間帯（--start〜--end）の内側に収まるように指定してください"
            )

    return args


async def main() -> None:
    args = parse_args()

    slots = generate_slots(
        target_date=args.date,
        work_start=args.start,
        work_end=args.end,
        lunch_start=args.lunch_start,
        lunch_end=args.lunch_end,
    )

    async with create_client_session() as client:
        raw_tasks = await client.fetch_tasks(args.project_id)
        parsed_tasks, errors = parse(raw_tasks)
        result = schedule(parsed_tasks, slots)

        for task, slot in result.scheduled:
            due_string = slot.start.strftime("%Y-%m-%d %H:%M")
            await client.update_task_due(task.id, due_string)

    report(result, errors)


if __name__ == "__main__":
    asyncio.run(main())
