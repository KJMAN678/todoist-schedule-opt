# アプリケーション設計書

## 処理フロー

```
[CLI引数パース]
      │
      ▼
[SlotGenerator] → 作業可能スロット列（15分刻み、ランチ除外）
      │
      ▼
[TodoistClient.fetch_tasks] → 生タスクリスト
      │
      ▼
[TaskParser.parse] → ParsedTask[] + ParseError[]
      │                    │
      │            (stderr に報告)
      ▼
[Scheduler.schedule] → ScheduleResult
      │                  scheduled[]
      │                  unscheduled[] → (stderr に警告)
      ▼
[TodoistClient.update_task_due] × scheduled件数
      │
      ▼
[Reporter.report] → stdout にスケジュール結果
```

## ファイル構成

```
todoist/
├── scheduler.py       # エントリポイント + main() + parse_args()
├── todoist_client.py  # TodoistClient (MCP通信)
├── task_parser.py     # TaskParser, ParsedTask, ParseError
├── slot_generator.py  # SlotGenerator, TimeSlot
├── optimizer.py       # Scheduler, ScheduleResult (ortools)
└── reporter.py        # Reporter
```

## CP-SAT モデル設計

### 変数
- `start[i]`: タスク i の開始スロットインデックス（整数変数、0 〜 len(slots)-1）
- `assigned[i]`: タスク i がスケジュール可能か（ブール変数）

### 制約
1. **連続スロット**: タスク i のスロット `start[i]` 〜 `start[i] + slots_needed[i] - 1` がすべて利用可能
2. **重複なし**: 任意の 2 タスクのスロット範囲が重複しない
3. **順序制約**: 取得順を維持（`start[i] < start[i+1]` when both assigned）
4. **境界**: `start[i] + slots_needed[i] <= len(slots)` でなければ `assigned[i] = False`

### 目的関数
- `assigned[i]` の合計を最大化（できるだけ多くのタスクを割り当てる）
- タイブレーク: 早いスロットを優先（makespan 最小化）

## CLI 引数仕様

```
python scheduler.py \
  [--project-id PROJECT_ID] \
  --start HH:MM \
  --end HH:MM \
  [--lunch-start HH:MM] \
  [--lunch-end HH:MM] \
  [--date YYYY-MM-DD]
```

### バリデーション
- `--start` < `--end`
- `--lunch-start` と `--lunch-end` は両方指定 or 両方省略
- `--lunch-start` < `--lunch-end`
- `--lunch-start` >= `--start` かつ `--lunch-end` <= `--end`

## dueString フォーマット

`update-tasks` に渡す `dueString` は `"YYYY-MM-DD HH:MM"` 形式。  
例: `"2026-05-09 09:00"`

## エラーハンドリング方針

| エラー種別 | 挙動 |
|-----------|------|
| `description` が空または非数値 | stderr に報告してそのタスクをスキップ、処理継続 |
| タスクが時間内に収まらない | stderr に警告、未スケジュールのまま継続 |
| CLI 引数不正 | argparse がエラー表示して exit(2) |
| MCP API エラー | 例外を再送出してスタックトレース表示 |
