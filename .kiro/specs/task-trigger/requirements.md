# 要件定義: task-trigger

## 概要

macOS の launchd で 15 分ごとに Todoist タスクをチェックし、現在時刻に due time が合致するタスクがあれば、そのタスクの **Todoist コメント**をプロンプトとして `claude` CLI に渡して自動実行する。実行結果はログファイルに記録する。

> **注記**: `description` フィールドは既存の `scheduler.py` がタスクの見積時間（float）入力に使用しているため、プロンプト用途には使用しない。代わりに Todoist MCP API の `find-comments` ツールでタスクに付いたコメントを取得する。

---

## 機能要件（EARS 形式）

### 1. タスクチェック（ポーリング）

- **REQ-1**: task-trigger は起動時に、当日かつ現在時刻の 15 分刻みウィンドウ（例: 09:15 起動 → 09:00〜09:15 の範囲）内に due datetime が設定されているタスクを Todoist MCP API の `find-tasks` ツールで取得しなければならない。
- **REQ-2**: 対象プロジェクトは環境変数 `TODOIST_PROJECT_ID` で指定する。省略時は全インボックスを対象とする。
- **REQ-3**: due date が当日でないタスク、および due time が未設定のタスクは対象外とする。
- **REQ-4**: 合致するタスクが 0 件の場合、ログに「対象タスクなし」を記録してスクリプトを正常終了しなければならない。

### 2. プロンプト取得（Todoist コメント）

- **REQ-5**: task-trigger は合致したタスクに対して Todoist MCP API の `find-comments` ツールを呼び出し、そのタスクのコメント一覧を取得しなければならない。
- **REQ-6**: 複数コメントが存在する場合、最新のコメント（`posted_at` が最大のもの）の `content` をプロンプトテキストとして使用しなければならない。
- **REQ-7**: コメントが 1 件も存在しないタスクは実行をスキップし、スキップした旨をログに記録して処理を継続しなければならない。

### 3. Claude Code 実行

- **REQ-8**: task-trigger はコメントのテキストを `claude --print` コマンドのプロンプトとして渡し、サブプロセスとして実行しなければならない。
- **REQ-9**: `claude` コマンドの実行ディレクトリは環境変数 `TASK_TRIGGER_WORKDIR` で指定できる。省略時はスクリプトと同じディレクトリを使用する。
- **REQ-10**: 複数タスクが合致した場合、タスクごとに順次 `claude` を実行しなければならない。
- **REQ-11**: `claude` コマンドが見つからない場合（`FileNotFoundError`）はエラーをログに記録してスクリプトを終了しなければならない。

### 4. ログ記録

- **REQ-12**: 各タスクの実行結果（成功/失敗・claude の stdout・実行 UTC 日時・タスク ID・タスク名・プロンプト先頭 200 文字）をログファイルに追記しなければならない。
- **REQ-13**: ログファイルのデフォルトパスは `~/Library/Logs/task-trigger/task-trigger.log` とし、環境変数 `TASK_TRIGGER_LOG` で上書き可能とする。
- **REQ-14**: ログファイルの親ディレクトリが存在しない場合は自動的に作成しなければならない。
- **REQ-15**: ログは 1 行 JSON 形式（JSON Lines）で記録し、タイムスタンプ・タスク ID・タスク名・ステータス・出力を含める。

### 5. cron 設定

- **REQ-16**: `*/15 * * * *` で動作する crontab エントリのサンプルを `crontab.example` ファイルとして提供しなければならない。
- **REQ-17**: cron はシェル環境変数を引き継がないため、スクリプト内で `.env.local` を読み込んで環境変数（`TODOIST_API_TOKEN` 等）を設定しなければならない。

---

## 非機能要件

- **NFR-1**: Python 3.13、`uv run python task_trigger.py` で実行可能であること。
- **NFR-2**: Todoist 認証は `TODOIST_API_TOKEN` 環境変数を使用する。コードにトークンをハードコードしてはならない。
- **NFR-3**: Todoist MCP API エラーはログに記録し、スクリプトを終了せず次のタスクへ処理を継続する。
- **NFR-4**: `claude` の実行タイムアウトは環境変数 `TASK_TRIGGER_TIMEOUT` で設定可能とし、デフォルトは 300 秒とする。

---

## 環境変数仕様

| 変数名 | 必須 | デフォルト | 説明 |
|--------|------|-----------|------|
| `TODOIST_API_TOKEN` | **必須** | — | Todoist MCP 認証トークン |
| `TODOIST_PROJECT_ID` | 任意 | None（全タスク） | 対象プロジェクト ID |
| `TASK_TRIGGER_WORKDIR` | 任意 | スクリプトディレクトリ | `claude` 実行ディレクトリ |
| `TASK_TRIGGER_LOG` | 任意 | `~/Library/Logs/task-trigger/task-trigger.log` | ログファイルパス |
| `TASK_TRIGGER_TIMEOUT` | 任意 | `300` | `claude` 実行タイムアウト（秒）。launchd の 15 分間隔に収めたい場合は 800 秒が実質上限 |

---

## スコープ外

- GUI / 設定画面
- タスク完了後の Todoist ステータス更新（完了マーク）
- 複数ユーザー対応
- Windows / Linux 対応（macOS cron 専用）
- 二重起動防止（ロックファイル）— 一旦保留
