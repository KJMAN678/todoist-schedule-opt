# CLAUDE.md

このファイルはClaudeがこのリポジトリで作業する際のガイドです。実装・レビュー時の基準として参照してください。

## プロジェクト概要

Todoist の MCP (Model Context Protocol) サーバーに接続し、タスク操作を Python スクリプトから行うプロジェクト。

- MCP クライアント (`mcp`) で `https://ai.todoist.net/mcp` に Streamable HTTP 接続
- `ortools` CP-SAT ソルバーでタスクの最適スケジューリングを実装済み
- パッケージ管理: `uv` / Python バージョン: 3.13

## ディレクトリ構成

```
todoist/
├── scheduler.py       # スケジューラ本体（CLI エントリポイント）
├── todoist_client.py  # TodoistClient（MCP 通信ラッパー）
├── task_parser.py     # TaskParser — description から見積時間をパース
├── slot_generator.py  # SlotGenerator — 15分スロット列を生成
├── optimizer.py       # Scheduler — ortools CP-SAT で最適割り当て
├── reporter.py        # Reporter — stdout/stderr に結果出力
├── main.py            # 探索・動作確認用の簡易スクリプト（本番外）
├── pyproject.toml     # プロジェクト定義・依存パッケージ
├── uv.lock            # 依存ロックファイル（コミット対象）
├── .python-version    # Python バージョン固定 (3.13)
├── .env.local         # 環境変数（TODOIST_API_TOKEN）。git 管理外
├── aidlc-docs/        # AIDLC 設計ドキュメント（要件・設計）
└── .kiro/specs/       # cc-sdd 仕様書（requirements.md, design.md, tasks.md）
```

## 開発コマンド

```bash
# 依存インストール
uv sync

# スケジューラ実行
uv run --env-file .env.local python scheduler.py \
  --start 09:00 --end 18:00 \
  --lunch-start 12:00 --lunch-end 13:00

# CLI オプション一覧
uv run --env-file .env.local python scheduler.py --help

# 簡易動作確認（main.py）
uv run --env-file .env.local python main.py

# パッケージ追加
uv add <package>
```

> **注意**: README には `--env-file .env` と記載があるが、実際のファイルは `.env.local`。

## `scheduler.py` CLI 引数

| 引数 | 必須 | デフォルト | 説明 |
|------|------|-----------|------|
| `--project-id` | 任意 | `6gc6X66RQH7Qcmxh` | 対象プロジェクト ID |
| `--start` | **必須** | — | 作業開始時刻（HH:MM） |
| `--end` | **必須** | — | 作業終了時刻（HH:MM） |
| `--lunch-start` | 任意 | — | ランチ開始（HH:MM）。`--lunch-end` と対で指定 |
| `--lunch-end` | 任意 | — | ランチ終了（HH:MM）。`--lunch-start` と対で指定 |
| `--date` | 任意 | 実行日 | スケジュール対象日（YYYY-MM-DD） |

## 環境変数

| 変数名 | 説明 |
|--------|------|
| `TODOIST_API_TOKEN` | Todoist API トークン。`.env.local` に記述 |

`.env.local` はコミットしない（`.gitignore` 対象外のため手動で管理）。

## 実装ルール

- 各モジュールは単一責務で実装する（`slot_generator.py` はスロット生成のみ、等）
- MCP ツール呼び出しは `session.call_tool(tool_name, args_dict)` の形式
- **`scheduler.py` は `update-tasks` で `dueString` を直接設定する**（繰り返しタスクへの影響を許容するユーザー合意済み）
- **その他の日付変更には `reschedule-tasks` を使用する**（`update-tasks` は繰り返しパターンを破壊するため）
- ハードコードされた ID（`projectId`, タスク `id` など）は変更時にユーザー確認を取る

## テスト・確認

- 自動テストは未設定
- 動作確認は実行出力で行う（stdout にスケジュール結果、stderr に警告・エラー）
- Todoist 側の変更は即座に反映されるため、**本番データへの影響に注意**
- 実行前に `--help` で引数を確認する習慣をつける

## レビュー観点

- `TODOIST_API_TOKEN` や固有 ID がコードにハードコードされていないか
- `.env.local` をコミットしていないか
- `scheduler.py` 以外の箇所で `update-tasks` を使ってスケジュール変更していないか
- `uv.lock` の更新漏れがないか
- `optimizer.py` の CP-SAT 制約が要件（順序・重複なし・最大化）を満たしているか

## 注意事項

- このスクリプトは実際の Todoist データを変更するため、テスト時も本番に影響する
- カスタム PyPI レジストリ (`pypi.flatt.tech`) を使用している
- `--lunch-start` / `--lunch-end` は両方指定または両方省略。片方のみはエラー

## Claude への指示

- コードを変更する前に、変更対象の MCP ツールの仕様（引数・動作）を確認する
- ハードコードされた ID を変更する際は必ずユーザーに確認を取る
- 新しい MCP ツールを使う場合は、実行前に副作用の有無をユーザーに伝える
- 各モジュールは責務が明確に分かれているため、変更は該当モジュールのみに留める
- `optimizer.py` の CP-SAT モデルを変更する場合は設計書 (`.kiro/specs/todoist-scheduler/design.md`) を参照する
