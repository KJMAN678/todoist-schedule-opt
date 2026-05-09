### todoist で管理しているタスクをスケジュール最適化する

```bash
# 始業時間、終了時間、ランチタイムの開始/終了時間を引数で与えて最適化実行
$ uv run --env-file .env python scheduler.py \
  --start 09:00 --end 18:00 \
  --lunch-start 12:00 --lunch-end 13:00
```

#### 最適化実行前

<img src="images/optimized_before.png" width=200>

#### 最適化実行後

<img src="images/optimized_after.png" width=200>

```bash
$ uv run ruff check --fix
$ uv run ruff format
$ uv run --env-file .env pytest tests/ -v
```

- .env.local をコピーして .env を作成
- todoist の対象のプロジェクトの ID と API Key を更新すること
