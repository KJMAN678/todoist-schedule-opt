# コンポーネント依存関係

```
scheduler.py (main entrypoint)
  ├── CLI (parse_args)
  │     └── argparse [stdlib]
  ├── SlotGenerator
  │     └── datetime [stdlib]
  ├── TodoistClient
  │     └── mcp [外部]
  ├── TaskParser
  │     └── (なし)
  ├── Scheduler
  │     └── ortools [外部]
  └── Reporter
        └── (なし)
```

## 外部依存

| ライブラリ | バージョン | 用途 |
|-----------|-----------|------|
| `mcp` | 1.27.0 | Todoist MCP クライアント |
| `ortools` | 9.15.6755 | CP-SAT スケジューリング最適化 |
