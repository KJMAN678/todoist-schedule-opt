# 技術設計書: todoist-scheduler

## ファイル構成

```
todoist/
├── scheduler.py       # エントリポイント・main()・parse_args()
├── todoist_client.py  # TodoistClient（MCP 通信）
├── task_parser.py     # TaskParser, ParsedTask, ParseError
├── slot_generator.py  # SlotGenerator, TimeSlot
├── optimizer.py       # Scheduler, ScheduleResult（ortools CP-SAT）
└── reporter.py        # Reporter（stdout/stderr 出力）
```

既存の `main.py` は変更しない。

---

## モジュール詳細設計

### `scheduler.py`

```python
import asyncio
import argparse
from datetime import date, time

def parse_args() -> argparse.Namespace:
    """CLI 引数をパースして返す。"""

async def main() -> None:
    args = parse_args()
    # 1. スロット生成
    # 2. MCP 接続・タスク取得
    # 3. タスクパース
    # 4. スケジュール最適化
    # 5. API 更新
    # 6. レポート出力

if __name__ == "__main__":
    asyncio.run(main())
```

**バリデーション（parse_args 内）**:
- `--start` < `--end`
- `--lunch-start`/`--lunch-end` は両方指定または両方省略
- `--lunch-start` < `--lunch-end`、かつ `--start` <= `--lunch-start`、`--lunch-end` <= `--end`

---

### `slot_generator.py`

```python
from dataclasses import dataclass
from datetime import datetime, date, time, timedelta

SLOT_MINUTES = 15

@dataclass(frozen=True)
class TimeSlot:
    start: datetime
    end: datetime  # start + 15分

def generate_slots(
    target_date: date,
    work_start: time,
    work_end: time,
    lunch_start: time | None = None,
    lunch_end: time | None = None,
) -> list[TimeSlot]:
    """
    work_start から work_end まで SLOT_MINUTES 刻みのスロット列を生成する。
    lunch_start〜lunch_end に該当するスロットは除外する。
    """
```

**実装詳細**:
1. `current = datetime.combine(target_date, work_start)` から開始
2. `current + timedelta(minutes=SLOT_MINUTES) <= datetime.combine(target_date, work_end)` の間ループ
3. ランチ時間帯と重複するスロットをスキップ
4. スロットを list に追加して返す

---

### `task_parser.py`

```python
from dataclasses import dataclass
import math

@dataclass
class ParsedTask:
    id: str
    content: str
    duration_hours: float
    slots_needed: int  # ceil(duration_hours * 60 / 15)

@dataclass
class ParseError:
    id: str
    content: str
    reason: str

def parse(tasks: list[dict]) -> tuple[list[ParsedTask], list[ParseError]]:
    """
    タスクリストを受け取り、(ParsedTask[], ParseError[]) を返す。
    description が空または非数値の場合は ParseError に分類する。
    """
```

**slots_needed 計算**:
```python
slots_needed = math.ceil(duration_hours * 60 / 15)
# 例: 0.5h → ceil(30/15) = 2 スロット
# 例: 1.0h → ceil(60/15) = 4 スロット
# 例: 0.1h → ceil(6/15)  = 1 スロット（最小1スロット）
```

---

### `optimizer.py`

```python
from dataclasses import dataclass, field
from ortools.sat.python import cp_model
from .task_parser import ParsedTask
from .slot_generator import TimeSlot

@dataclass
class ScheduleResult:
    scheduled: list[tuple[ParsedTask, TimeSlot]] = field(default_factory=list)
    unscheduled: list[ParsedTask] = field(default_factory=list)

def schedule(tasks: list[ParsedTask], slots: list[TimeSlot]) -> ScheduleResult:
    """CP-SAT ソルバーでタスクをスロットに割り当てる。"""
```

**CP-SAT モデル**:

```python
model = cp_model.CpModel()
n_tasks = len(tasks)
n_slots = len(slots)

# 変数: タスク i の開始スロットインデックス
starts = [model.NewIntVar(0, n_slots, f"start_{i}") for i in range(n_tasks)]
# 変数: タスク i が割り当て可能か
assigned = [model.NewBoolVar(f"assigned_{i}") for i in range(n_tasks)]

for i, task in enumerate(tasks):
    sn = task.slots_needed
    # 境界制約: 収まらない場合は assigned=False
    model.Add(starts[i] + sn <= n_slots).OnlyEnforceIf(assigned[i])
    model.Add(starts[i] + sn > n_slots).OnlyEnforceIf(assigned[i].Not())
    # 未割り当ての場合は start を n_slots に固定（比較を簡単にするため）
    model.Add(starts[i] == n_slots).OnlyEnforceIf(assigned[i].Not())

# 重複なし制約: interval 変数を使用
intervals = []
for i, task in enumerate(tasks):
    # assigned=False のタスクはサイズ0のオプション区間
    interval = model.NewOptionalIntervalVar(
        starts[i], task.slots_needed, starts[i] + task.slots_needed,
        assigned[i], f"interval_{i}"
    )
    intervals.append(interval)
model.AddNoOverlap(intervals)

# 順序制約: 取得順を維持（両方 assigned の場合のみ）
for i in range(n_tasks - 1):
    both_assigned = model.NewBoolVar(f"both_{i}")
    model.AddBoolAnd([assigned[i], assigned[i+1]]).OnlyEnforceIf(both_assigned)
    model.Add(starts[i] < starts[i+1]).OnlyEnforceIf(both_assigned)

# 目的関数: assigned の合計最大化、タイブレーク: 早いスロット優先
model.Maximize(sum(assigned) * (n_slots + 1) - sum(starts[i] for i in range(n_tasks)))
```

---

### `todoist_client.py`

```python
import os
from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession

MCP_URL = "https://ai.todoist.net/mcp"

class TodoistClient:
    def __init__(self, session: ClientSession):
        self._session = session

    async def fetch_tasks(self, project_id: str, limit: int = 100) -> list[dict]:
        result = await self._session.call_tool(
            "find-tasks", {"projectId": project_id, "limit": limit}
        )
        return result.structuredContent["tasks"]

    async def update_task_due(self, task_id: str, due_string: str) -> None:
        await self._session.call_tool(
            "update-tasks",
            {"tasks": [{"id": task_id, "dueString": due_string}]}
        )

async def create_client_session():
    """コンテキストマネージャとして使用するファクトリ。"""
    headers = {"Authorization": f"Bearer {os.environ['TODOIST_API_TOKEN']}"}
    async with streamablehttp_client(MCP_URL, headers=headers) as (r, w, _):
        async with ClientSession(r, w) as session:
            await session.initialize()
            yield TodoistClient(session)
```

---

### `reporter.py`

```python
import sys
from .task_parser import ParsedTask, ParseError
from .slot_generator import TimeSlot
from .optimizer import ScheduleResult

def report(
    result: ScheduleResult,
    errors: list[ParseError],
) -> None:
    # stderr: パースエラー
    for err in errors:
        print(f"[SKIP] {err.content}: {err.reason}", file=sys.stderr)

    # stderr: 未スケジュール警告
    for task in result.unscheduled:
        print(
            f"[WARN] '{task.content}' ({task.duration_hours}h) は時間内に収まりませんでした",
            file=sys.stderr
        )

    # stdout: スケジュール結果
    print("=== スケジュール結果 ===")
    for task, slot in result.scheduled:
        print(
            f"  {slot.start.strftime('%H:%M')} [{task.duration_hours}h] {task.content}"
        )
```

---

## dueString フォーマット

```python
due_string = slot.start.strftime("%Y-%m-%d %H:%M")
# 例: "2026-05-09 09:00"
```

---

## 実行例

```bash
uv run --env-file .env.local python scheduler.py \
  --start 09:00 --end 18:00 \
  --lunch-start 12:00 --lunch-end 13:00
```

**出力例（stdout）:**
```
=== スケジュール結果 ===
  09:00 [1.0h] 仕様書レビュー
  10:00 [0.5h] デイリー準備
  10:30 [2.0h] 実装作業
  13:00 [1.5h] テスト
```

**警告例（stderr）:**
```
[SKIP] 買い物: description が数値ではありません ('来週まで')
[WARN] '大型リファクタリング' (8.0h) は時間内に収まりませんでした
```
