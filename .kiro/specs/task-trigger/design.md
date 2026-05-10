# 技術設計: task-trigger

## アーキテクチャ概要

```
cron (*/15 * * * *)
  └─ uv run python task_trigger.py
        │
        ├─ load_env_file(".env.local")        # 環境変数ロード
        ├─ load_config()                      # Config 構築
        ├─ current_window()                   # 15分ウィンドウ計算
        │
        └─ MCP Session (todoist_client.py)
              ├─ fetch_tasks(project_id)       # REQ-1,2,3
              │   └─ [filter: due in window]
              │
              └─ for each matching task:
                    ├─ fetch_comments(task_id) # REQ-5,6,7
                    │   └─ latest comment
                    ├─ run_claude(prompt)       # REQ-8,9,10,11
                    └─ append_log(result)       # REQ-12〜15
```

### アーキテクチャ判断

`scheduler.py` は6モジュール構成だが、`task_trigger.py` は I/O → MCP → subprocess → log という一直線のパイプラインのため **単一スクリプト構成**を採用する。モジュール分割は過剰になる。

既存の `todoist_client.py` に `fetch_comments()` メソッドを追加して再利用する。

---

## ファイル構成

```
todoist/
├── task_trigger.py        # (新規) トリガー本体
├── todoist_client.py      # (変更) fetch_comments() を追加
├── crontab.example        # (新規) cron 設定サンプル
└── .kiro/specs/task-trigger/
```

---

## データ型定義

### `task_trigger.py` 内のデータ型

```python
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Config:
    api_token: str
    project_id: str | None       # None → プロジェクト未指定（全タスク）
    workdir: Path
    log_path: Path
    timeout: int                 # claude 実行タイムアウト（秒）

@dataclass(frozen=True)
class Comment:
    id: str
    content: str
    posted_at: str               # ISO 8601 文字列

@dataclass
class TriggerResult:
    task_id: str
    task_name: str
    status: str                  # "ok" | "skip_no_comment" | "error"
    prompt_preview: str          # content 先頭 200 文字
    output: str                  # claude stdout（エラー時はメッセージ）
    timestamp: str               # UTC ISO 8601
```

### ログ出力スキーマ（JSON Lines 1 行のフィールド）

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `timestamp` | `str` | UTC ISO 8601 |
| `task_id` | `str` | Todoist タスク ID |
| `task_name` | `str` | タスク名 |
| `status` | `str` | `"ok"` / `"skip_no_comment"` / `"error"` |
| `prompt_preview` | `str` | プロンプト先頭 200 文字 |
| `output` | `str` | claude stdout または エラーメッセージ |

---

## コンポーネント設計

### 1. `task_trigger.py` — 関数一覧

#### `load_env_file(path: Path) -> dict[str, str]`
- `KEY=VALUE` 形式の `.env.local` をパースして dict を返す
- `#` コメント行・空行はスキップ
- 追加依存なし（標準ライブラリのみ）
- **対応要件**: REQ-17

#### `load_config() -> Config`
- `os.environ` から各変数を読み取り `Config` を構築
- `TODOIST_API_TOKEN` が未設定の場合は `KeyError` を自然に伝播させる
- `TASK_TRIGGER_WORKDIR` 省略時: `Path(__file__).parent`
- `TASK_TRIGGER_LOG` 省略時: `Path.home() / "Library/Logs/task-trigger/task-trigger.log"`
- `TASK_TRIGGER_TIMEOUT` 省略時: `300`
- **対応要件**: REQ-13

#### `current_window() -> tuple[datetime, datetime]`
- 現在 UTC 時刻を 15 分刻みに切り捨てて `window_start` を計算
- `window_end = window_start + timedelta(minutes=15)`
- 例: 09:17 → `(09:00, 09:15)`、09:15 → `(09:00, 09:15)`
- **対応要件**: REQ-1

#### `is_due_in_window(task: dict, window: tuple[datetime, datetime]) -> bool`
- `task["due"]` が `None` → `False`（REQ-3）
- `task["due"]["datetime"]` が `None`（終日タスク）→ `False`（REQ-3）
- `task["due"]["date"]` が今日でない → `False`（REQ-3）
- `due_dt = datetime.fromisoformat(task["due"]["datetime"])` を UTC に正規化
- `window_start <= due_dt < window_end` を返す
- **対応要件**: REQ-1, REQ-3

#### `run_claude(prompt: str, config: Config) -> tuple[str, bool]`
- `subprocess.run(["claude", "--print", prompt], capture_output=True, text=True, cwd=config.workdir, timeout=config.timeout)` を実行
- 戻り値: `(stdout, success)` — `success = returncode == 0`
- `FileNotFoundError` 時は `("claude コマンドが見つかりません", False)` を返し呼び出し元で終了処理
- **対応要件**: REQ-8, REQ-9, REQ-11

#### `append_log(result: TriggerResult, log_path: Path) -> None`
- `log_path.parent.mkdir(parents=True, exist_ok=True)`（REQ-14）
- `json.dumps(asdict(result), ensure_ascii=False)` を `\n` 付きで追記
- **対応要件**: REQ-12, REQ-14, REQ-15

#### `async def trigger_task(task: dict, client: TodoistClient, config: Config) -> TriggerResult`
- 1 タスクの処理単位（コメント取得 → claude 実行 → result 生成）
- `find-comments` の MCP エラーは `try/except` でキャッチし `status="error"` を返す（NFR-3）
- **対応要件**: REQ-5, REQ-6, REQ-7, REQ-8

#### `async def main() -> None`
- `.env.local` 読み込み → `load_config()` → `current_window()`
- `create_client_session()` で MCP 接続
- `fetch_tasks()` で全タスク取得 → `is_due_in_window()` でフィルタ
- 合致 0 件 → ログ記録して `return`（REQ-4）
- 合致タスクを順次 `trigger_task()` 処理（REQ-10）
- **対応要件**: REQ-1〜4, REQ-10

---

### 2. `todoist_client.py` — 追加メソッド

#### `async def fetch_comments(self, task_id: str) -> list[dict]`

```
MCP ツール: find-comments
引数: {"taskId": task_id}
戻り値: result.structuredContent["comments"]  → list[dict]
各要素のフィールド: id, task_id, content, posted_at
```

- **対応要件**: REQ-5

---

### 3. `crontab.example`

```
# Todoist task-trigger — 15分ごとに実行
# crontab -e で編集し、以下の行を追加する（パスは環境に合わせて変更）
*/15 * * * * cd /path/to/todoist && /path/to/uv run python task_trigger.py >> /tmp/task-trigger-cron.log 2>&1
```

- `uv` のフルパスが必要（cron は `$PATH` を引き継がない）
- stdout/stderr は別途 `/tmp/task-trigger-cron.log` に追記（デバッグ用）
- アプリログは `TASK_TRIGGER_LOG` で指定されたファイルに JSON Lines で記録
- **対応要件**: REQ-16

---

## データフロー（シーケンス）

```
cron
 │
 ▼
task_trigger.main()
 ├─ load_env_file(".env.local") → os.environ に反映
 ├─ load_config()               → Config
 ├─ current_window()            → (window_start, window_end)
 │
 └─ async with create_client_session() as client:
       │
       ├─ client.fetch_tasks(project_id)
       │   └─ filter: is_due_in_window → matching_tasks
       │
       ├─ [matching_tasks == 0] → append_log("対象タスクなし") → return
       │
       └─ for task in matching_tasks:
             │
             ├─ client.fetch_comments(task["id"])
             │   ├─ [0件] → TriggerResult(status="skip_no_comment")
             │   └─ [1件+] → latest = max(comments, key=lambda c: c["posted_at"])
             │
             ├─ run_claude(latest["content"], config)
             │   ├─ [FileNotFoundError] → log error → sys.exit(1)
             │   └─ (output, success) → TriggerResult(status="ok" or "error")
             │
             └─ append_log(result, config.log_path)
```

---

## 要件トレーサビリティ

| 要件 | 対応コンポーネント |
|------|--------------------|
| REQ-1 | `current_window()`, `is_due_in_window()`, `main()` |
| REQ-2 | `load_config()` (`TODOIST_PROJECT_ID`) |
| REQ-3 | `is_due_in_window()` |
| REQ-4 | `main()` (0件チェック) |
| REQ-5 | `TodoistClient.fetch_comments()` |
| REQ-6 | `trigger_task()` (`max(posted_at)`) |
| REQ-7 | `trigger_task()` (コメント0件スキップ) |
| REQ-8 | `run_claude()` (`claude --print`) |
| REQ-9 | `run_claude()` (`cwd=config.workdir`) |
| REQ-10 | `main()` (順次ループ) |
| REQ-11 | `run_claude()` (`FileNotFoundError`) |
| REQ-12 | `append_log()` |
| REQ-13 | `load_config()` (`TASK_TRIGGER_LOG`) |
| REQ-14 | `append_log()` (`mkdir(parents=True)`) |
| REQ-15 | `append_log()` (JSON Lines) |
| REQ-16 | `crontab.example` |
| REQ-17 | `load_env_file()` |
| NFR-1 | `uv run python task_trigger.py` |
| NFR-2 | `load_config()` (ハードコードなし) |
| NFR-3 | `trigger_task()` (try/except で継続) |
| NFR-4 | `load_config()` (`TASK_TRIGGER_TIMEOUT`) |
