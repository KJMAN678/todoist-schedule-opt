# Research Log: task-trigger

## Discovery 種別: Extension（既存 MCP パターンの拡張）

## Summary

既存の `todoist_client.py` の `TodoistClient` クラスと `create_client_session()` パターンを再利用する。
追加が必要な MCP ツールは `find-comments`（`taskId` を引数に取るコメント取得ツール）のみ。
`claude --print` は非インタラクティブモードで動作し、stdout をキャプチャ可能。

---

## Architecture Decision Records

### ADR-1: 単一スクリプト構成を採用

- **決定**: `task_trigger.py` を単一ファイルで実装する
- **理由**: I/O → MCP → subprocess → log という一直線のパイプラインであり、モジュール分割のメリットよりコストが上回る
- **代替案**: `scheduler.py` と同様の6モジュール構成 → 過剰、却下

### ADR-2: `.env.local` をスクリプト内でパース

- **決定**: `load_env_file()` で `.env.local` を読み込む（`python-dotenv` 不使用）
- **理由**: cron は呼び出し元のシェル環境変数を引き継がない。追加依存を増やさずに解決できる
- **代替案**: crontab に直接 `env` を記述 → 秘密情報が crontab に残るリスク、却下

### ADR-3: `todoist_client.py` に `fetch_comments()` を追加

- **決定**: 既存の `TodoistClient` クラスにメソッドを追加して再利用する
- **理由**: MCP セッション管理ロジック（`asynccontextmanager`）の重複を避ける
- **代替案**: `task_trigger.py` 内で独立したMCPクライアントを実装 → 重複、却下

### ADR-4: 時刻マッチングは「現在時刻から直前15分ウィンドウ」方式

- **決定**: `window_end = current_time_truncated_to_15min`、`window_start = window_end - 15min`
- **理由**: cron は厳密に :00/:15/:30/:45 に実行されないことがある。直前ウィンドウ方式ならタスクの取りこぼしを防げる
- **注意**: `due.datetime` は UTC で比較する（Todoist API は UTC で返す）

### ADR-5: `claude --print` のプロセス実行に `subprocess.run()` を使用

- **決定**: `subprocess.run(["claude", "--print", prompt], capture_output=True, ...)`
- **理由**: シンプル。asyncio サブプロセスより理解しやすく、claude の実行はブロッキングで問題ない（順次実行）
- **代替案**: `asyncio.create_subprocess_exec` → 並列実行不要なので過剰
