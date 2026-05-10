import asyncio
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from todoist_client import TodoistClient, create_client_session


class ClaudeNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class Config:
    api_token: str
    project_id: str | None
    workdir: Path
    log_path: Path
    timeout: int


@dataclass
class TriggerResult:
    task_id: str
    task_name: str
    status: str  # "ok" | "skip_no_comment" | "error" | "no_tasks"
    prompt_preview: str
    output: str
    timestamp: str  # UTC ISO 8601


def load_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    result = {}
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" in stripped:
            key, _, value = stripped.partition("=")
            result[key] = value
    return result


def load_config() -> Config:
    return Config(
        api_token=os.environ["TODOIST_API_TOKEN"],
        project_id=os.environ.get("TODOIST_PROJECT_ID"),
        workdir=Path(os.environ.get("TASK_TRIGGER_WORKDIR", Path(__file__).parent)),
        log_path=Path(
            os.environ.get(
                "TASK_TRIGGER_LOG",
                Path.home() / "Library/Logs/task-trigger/task-trigger.log",
            )
        ),
        timeout=int(os.environ.get("TASK_TRIGGER_TIMEOUT", "300")),
    )


def current_window() -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    # Truncate to 15-minute boundary
    truncated_minutes = (now.minute // 15) * 15
    window_end = now.replace(minute=truncated_minutes, second=0, microsecond=0)
    window_start = window_end - timedelta(minutes=15)
    return window_start, window_end


def is_due_in_window(task: dict, window: tuple[datetime, datetime]) -> bool:
    window_start, window_end = window
    due = task.get("due")
    if due is None:
        return False
    if due.get("datetime") is None:
        return False
    if due.get("date") != str(window_end.date()):
        return False
    due_dt = datetime.fromisoformat(due["datetime"])
    # Ensure timezone-aware for comparison
    if due_dt.tzinfo is None:
        due_dt = due_dt.replace(tzinfo=timezone.utc)
    return window_start <= due_dt < window_end


def run_claude(prompt: str, config: Config) -> tuple[str, bool]:
    try:
        result = subprocess.run(
            ["claude", "--print", prompt],
            capture_output=True,
            text=True,
            cwd=config.workdir,
            timeout=config.timeout,
        )
        return result.stdout, result.returncode == 0
    except FileNotFoundError:
        raise ClaudeNotFoundError("claude command not found")
    except subprocess.TimeoutExpired:
        return f"タイムアウト（{config.timeout}秒）", False


def append_log(result: TriggerResult, log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(result), ensure_ascii=False) + "\n")


async def trigger_task(task: dict, client: TodoistClient, config: Config) -> TriggerResult:
    timestamp = datetime.now(timezone.utc).isoformat()
    task_id = task["id"]
    task_name = task.get("content", "")

    try:
        comments = await client.fetch_comments(task_id)
    except Exception as e:
        return TriggerResult(
            task_id=task_id,
            task_name=task_name,
            status="error",
            prompt_preview="",
            output=str(e),
            timestamp=timestamp,
        )

    if not comments:
        return TriggerResult(
            task_id=task_id,
            task_name=task_name,
            status="skip_no_comment",
            prompt_preview="",
            output="",
            timestamp=timestamp,
        )

    latest = max(comments, key=lambda c: c.get("posted_at", ""))
    prompt = latest.get("content", "")
    prompt_preview = prompt[:200]

    output, success = run_claude(prompt, config)

    return TriggerResult(
        task_id=task_id,
        task_name=task_name,
        status="ok" if success else "error",
        prompt_preview=prompt_preview,
        output=output,
        timestamp=timestamp,
    )


async def main() -> None:
    env_path = Path(__file__).parent / ".env"
    os.environ.update(load_env_file(env_path))

    config = load_config()
    window = current_window()

    try:
        async with create_client_session() as client:
            tasks = await client.fetch_tasks(config.project_id)
            due_tasks = [t for t in tasks if is_due_in_window(t, window)]

            if not due_tasks:
                append_log(
                    TriggerResult(
                        task_id="",
                        task_name="",
                        status="no_tasks",
                        prompt_preview="",
                        output="",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    ),
                    config.log_path,
                )
                return

            for task in due_tasks:
                result = await trigger_task(task, client, config)
                append_log(result, config.log_path)
    except ClaudeNotFoundError as e:
        append_log(
            TriggerResult(
                task_id="",
                task_name="",
                status="error",
                prompt_preview="",
                output=str(e),
                timestamp=datetime.now(timezone.utc).isoformat(),
            ),
            config.log_path,
        )
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
