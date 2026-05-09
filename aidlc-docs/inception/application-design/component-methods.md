# コンポーネントメソッド定義

## C2: TodoistClient

```python
async def fetch_tasks(project_id: str, limit: int = 100) -> list[dict]
    # find-tasks ツールを呼び出しタスクリストを返す

async def update_task_due(task_id: str, due_string: str) -> None
    # update-tasks ツールで dueString を更新する
```

## C3: TaskParser

```python
@dataclass
class ParsedTask:
    id: str
    content: str
    duration_hours: float  # 見積時間（時間単位）
    slots_needed: int       # ceil(duration_hours * 60 / 15)

@dataclass
class ParseError:
    id: str
    content: str
    reason: str

def parse(tasks: list[dict]) -> tuple[list[ParsedTask], list[ParseError]]
    # 各タスクをパース。数値変換失敗はParseErrorに分類
```

## C4: SlotGenerator

```python
@dataclass
class TimeSlot:
    start: datetime  # スロット開始時刻
    end: datetime    # スロット終了時刻（start + 15分）

def generate_slots(
    date: date,
    work_start: time,
    work_end: time,
    lunch_start: time | None,
    lunch_end: time | None,
) -> list[TimeSlot]
    # 15分スロット列を生成。ランチ時間帯のスロットを除外して返す
```

## C5: Scheduler

```python
@dataclass
class ScheduleResult:
    scheduled: list[tuple[ParsedTask, TimeSlot]]  # (タスク, 割り当て開始スロット)
    unscheduled: list[ParsedTask]                  # 時間超過で未割り当て

def schedule(tasks: list[ParsedTask], slots: list[TimeSlot]) -> ScheduleResult
    # CP-SAT ソルバーでタスクを連続スロットに割り当てる
    # 制約: 各タスクは slots_needed 個の連続スロットを占有
    # 目的: タスクを取得順に詰めて配置（順序制約）
```

## C6: Reporter

```python
def report(result: ScheduleResult, errors: list[ParseError]) -> None
    # stdout: スケジュール済みタスクの一覧（名前・開始時刻・見積時間）
    # stderr: ParseError と未スケジュールタスクの警告
```
