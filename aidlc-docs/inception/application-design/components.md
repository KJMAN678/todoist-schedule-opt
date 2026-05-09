# コンポーネント定義

## C1: CLI (`cli.py` or `scheduler.py` の `parse_args`)
- `argparse` で引数をパースし、設定オブジェクトを返す
- 依存: なし

## C2: TodoistClient
- MCP `ClientSession` をラップし、タスク取得・更新を提供する
- 依存: `mcp`

## C3: TaskParser
- タスクの `description` から見積時間（float, 時間単位）をパースする
- 非数値の場合はエラー情報を返す
- 依存: なし

## C4: SlotGenerator
- `--start`, `--end`, `--lunch-start`, `--lunch-end` から 15 分スロット列を生成する
- 依存: `datetime`

## C5: Scheduler
- ortools CP-SAT ソルバーでタスク→スロット割り当てを最適化する
- 入力: タスクリスト（見積スロット数付き）、利用可能スロット列
- 出力: タスクごとの割り当て開始スロット（または未割り当て）
- 依存: `ortools`

## C6: Reporter
- スケジュール結果・スキップ情報を標準出力/stderr に出力する
- 依存: なし
