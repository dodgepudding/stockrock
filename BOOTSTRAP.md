# Stockrock — 首次接入检查清单（BOOTSTRAP）

> OpenClaw 首次 bootstrap 时可按本清单执行；完成后可删除本文件。

## 检查项

- [ ] Python 3.11+ 可用（推荐 3.12）
- [ ] `pip install -e ".[dev]"` 成功
- [ ] `.env` 已从 `.env.example` 复制
- [ ] `web/dist` 已构建（或用户仅用 API）
- [ ] `curl http://127.0.0.1:8000/api/health` 返回 `{"status":"ok"}`
- [ ] `pytest -q` 通过

## 插件（可选）

- [ ] OpenClaw: `openclaw plugins install --link ./plugins/stockrock && openclaw plugins enable stockrock`
- [ ] Hermes: `hermes plugins install ./plugins/stockrock --enable`

## 合并到工作区记忆

将以下要点写入 agent 长期说明（若适用）：

- Stockrock API 默认 `http://127.0.0.1:8000`
- 新通达信公式 → `stockrock/strategies/` + 注册
- 详细流程见 `AGENTS.md`、`TOOLS.md`、`skills/stockrock/SKILL.md`

完成后删除本 `BOOTSTRAP.md`。
