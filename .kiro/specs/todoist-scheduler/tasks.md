# 実装タスク: todoist-scheduler

## 進捗サマリー
- メジャータスク数: 6
- サブタスク数: 18
- 要件カバレッジ: REQ-1〜19, NFR-1〜4

---

## Task 1: `slot_generator.py` の実装
**対応要件**: REQ-5, REQ-6, REQ-7, REQ-8

- [x] 1.1: `TimeSlot` dataclass を定義する（`start: datetime`, `end: datetime`）
- [x] 1.2: `generate_slots()` を実装する（15分刻みスロット生成、ランチ除外）
- [x] 1.3: ランチ引数の両方指定/省略バリデーションを `scheduler.py` の `parse_args` に追加

---

## Task 2: `task_parser.py` の実装
**対応要件**: REQ-3, REQ-4, REQ-8

- [x] 2.1: `ParsedTask`, `ParseError` dataclass を定義する
- [x] 2.2: `parse()` を実装する（float パース、`slots_needed` 計算）
- [x] 2.3: description が空・空白・非数値の各ケースでエラーを生成することを確認

---

## Task 3: `optimizer.py` の実装
**対応要件**: REQ-9〜14

- [x] 3.1: `ScheduleResult` dataclass を定義する
- [x] 3.2: CP-SAT モデルを構築する（変数定義・境界制約・重複なし制約・順序制約）
- [x] 3.3: 目的関数を設定する（assigned 最大化 + 早いスロット優先）
- [x] 3.4: ソルバー結果を `ScheduleResult` に変換して返す

---

## Task 4: `todoist_client.py` の実装
**対応要件**: REQ-1, REQ-2, REQ-15, REQ-16

- [x] 4.1: `TodoistClient` クラスを実装する（`fetch_tasks`, `update_task_due`）
- [x] 4.2: `create_client_session()` async コンテキストマネージャを実装する
- [x] 4.3: `TODOIST_API_TOKEN` が未設定の場合の KeyError が自然に伝播することを確認

---

## Task 5: `reporter.py` の実装
**対応要件**: REQ-18, REQ-19

- [x] 5.1: `report()` を実装する（stdout にスケジュール結果、stderr にエラー・警告）

---

## Task 6: `scheduler.py` エントリポイントの実装
**対応要件**: REQ-1〜19, NFR-1〜4 すべて統合

- [x] 6.1: `parse_args()` を実装する（全引数定義・バリデーション）
- [x] 6.2: `main()` で各モジュールを呼び出す処理フローを実装する
- [x] 6.3: スケジュール済みタスクへの `update_task_due()` 一括呼び出しを実装する
- [x] 6.4: `uv run --env-file .env.local python scheduler.py --start 09:00 --end 18:00` で正常動作を確認する
