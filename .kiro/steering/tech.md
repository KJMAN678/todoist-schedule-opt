---
inclusion: always
---

# Tech Steering

## スタック

| レイヤー | 技術 |
|---------|------|
| 言語 | Python 3.13 |
| パッケージ管理 | uv (`.python-version` + `pyproject.toml`) |
| 最適化エンジン | ortools CP-SAT (`ortools==9.15.6755`) |
| Todoist 通信 | MCP Streamable HTTP (`mcp==1.27.0`, `https://ai.todoist.net/mcp`) |
| 非同期 | asyncio + `asynccontextmanager` |
| テスト | pytest (`pytest==9.0.3`) |
| Lint/Format | ruff (`ruff==0.15.12`) |

## 主要な技術的決定

### MCP 通信パターン
```python
@asynccontextmanager
async def create_client_session():
    headers = {"Authorization": f"Bearer {os.environ.get('TODOIST_API_TOKEN')}"}
    async with streamablehttp_client(MCP_URL, headers=headers) as (r, w, _):
        async with ClientSession(r, w) as session:
            await session.initialize()
            yield TodoistClient(session)
```
セッション生成は `asynccontextmanager` でラップし、呼び出し側は `async with` で利用する。

### CP-SAT モデル設計
- `NewIntVar(0, n_slots)` でスタートインデックスを表現
- `NewBoolVar` で assigned フラグを管理
- `AddNoOverlap` でタスク重複を禁止
- ギャップ境界（ランチ等）をまたぐ配置は `AddBoolOr([ends_before, starts_after])` で禁止
- 目的関数: `Maximize(Σ assigned*(n_slots+1) - Σ starts)` — 割り当て最大化 > 早いスロット優先

### スロット生成
- 15 分刻みで `TimeSlot(start, end)` を生成
- ランチ時間帯（`lunch_start <= current < lunch_end`）はリストから除外
- ギャップは `slots[g+1].start != slots[g].end` で検出

### Todoist への書き込み
`scheduler.py` は `update-tasks` で `dueString` を直接設定する（繰り返しタスクへの影響を許容済み）。
それ以外の日付変更では `reschedule-tasks` を使用する。

## 環境変数

| 変数 | 用途 |
|------|------|
| `TODOIST_API_TOKEN` | Todoist MCP 認証トークン |
| `TODOIST_PROJECT_ID` | 対象プロジェクト ID（任意、CLI 引数でも指定可） |

実行: `uv run --env-file .env.local python scheduler.py`

## テスト規約

- `testpaths = ["tests"]`, `pythonpath = ["."]`（`pyproject.toml` で設定済み）
- ファイル名: `tests/test_<module>.py`
- ランチギャップ回帰テストは `TestScheduleLunchGap` クラスで管理
