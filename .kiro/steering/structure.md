---
inclusion: always
---

# Structure Steering

## モジュール構成（単一責務）

```
todoist/
├── scheduler.py       # CLI エントリポイント — parse_args + main() の統合
├── todoist_client.py  # MCP 通信 — TodoistClient + create_client_session()
├── task_parser.py     # パース — description から見積時間・slots_needed を抽出
├── slot_generator.py  # スロット生成 — TimeSlot 列を 15 分刻みで生成
├── optimizer.py       # 最適化 — CP-SAT でスロット割り当て、ScheduleResult を返す
├── reporter.py        # 出力 — stdout に結果、stderr に警告・エラー
├── tests/             # pytest テスト（モジュールごとに 1 ファイル）
└── .kiro/specs/       # cc-sdd 仕様書（requirements.md, design.md, tasks.md）
```

## 設計パターン

### データフロー
```
CLI args
  → generate_slots()          → list[TimeSlot]
  → client.fetch_tasks()      → list[dict]
  → parse()                   → (list[ParsedTask], list[ParseError])
  → schedule()                → ScheduleResult
  → client.update_task_due()  (副作用: Todoist 書き込み)
  → report()                  (副作用: stdout/stderr)
```

### 各モジュールの責務境界
- `slot_generator.py`: スロット生成のみ。Todoist・スケジューリングを知らない
- `task_parser.py`: パースのみ。スロット・MCP を知らない
- `optimizer.py`: CP-SAT のみ。I/O を一切持たない
- `reporter.py`: 出力のみ。ビジネスロジックを持たない
- `todoist_client.py`: MCP 通信のみ。最適化ロジックを知らない
- `scheduler.py`: 各モジュールを呼び出す統合層

### 命名規則
- モジュール: `snake_case.py`
- クラス: `PascalCase`（`ParsedTask`, `TimeSlot`, `ScheduleResult`, `ParseError`, `TodoistClient`）
- 関数: `snake_case`（`generate_slots`, `parse`, `schedule`, `report`）
- テスト補助関数: `_` プレフィックス（`_task()`, `_slot()`, `_slots_range()`）

### データクラス
`dataclass` / `dataclass(frozen=True)` を使用。`field(default_factory=list)` でミュータブルデフォルト値を管理。

## 仕様書の配置

新機能の仕様書は `.kiro/specs/<feature-name>/` に配置:
- `requirements.md`: EARS 形式の要件
- `design.md`: 技術設計（クラス・データフロー・制約）
- `tasks.md`: 実装タスク（`[x]` チェックボックス）
