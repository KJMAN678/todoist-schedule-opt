import math
from dataclasses import dataclass


@dataclass
class ParsedTask:
    id: str
    content: str
    duration_hours: float
    slots_needed: int


@dataclass
class ParseError:
    id: str
    content: str
    reason: str


def parse(tasks: list[dict]) -> tuple[list[ParsedTask], list[ParseError]]:
    parsed = []
    errors = []

    for task in tasks:
        task_id = task["id"]
        content = task["content"]
        description = task.get("description", "")

        if not description or not description.strip():
            errors.append(
                ParseError(id=task_id, content=content, reason="description が空です")
            )
            continue

        try:
            duration_hours = float(description)
        except ValueError:
            errors.append(
                ParseError(
                    id=task_id,
                    content=content,
                    reason=f"description が数値ではありません ('{description}')",
                )
            )
            continue

        slots_needed = max(1, math.ceil(duration_hours * 60 / 15))
        parsed.append(
            ParsedTask(
                id=task_id,
                content=content,
                duration_hours=duration_hours,
                slots_needed=slots_needed,
            )
        )

    return parsed, errors
