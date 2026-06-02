---
name: stockrock
description: Install and operate Stockrock A-share screener — translate Tongdaxin formulas, run scans, manage watchlist
version: 0.1.0
metadata:
  hermes:
    tags: [stock, a-share, tongdaxin, screener, quant]
    category: finance
---

# Stockrock（A股选股）

## When to Use

- User pastes **通达信选股/指标公式** and wants Python strategy code
- User wants to **run full-market screening** or check **watchlist quotes**
- User asks to install/configure Stockrock in OpenClaw or Hermes workspace

## Quick Install (first time)

```bash
cd /path/to/stockrock
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
cd web && npm install && npm run build && cd ..
uvicorn stockrock.api.main:app --host 0.0.0.0 --port 8000
```

Health: `curl -s http://127.0.0.1:8000/api/health`

## Plugin install (OpenClaw)

```bash
openclaw plugins install --link /path/to/stockrock/plugins/stockrock
openclaw plugins enable stockrock
openclaw gateway restart
```

## Plugin install (Hermes)

```bash
hermes plugins install /path/to/stockrock/plugins/stockrock --enable
```

Session: `skill_view("stockrock:stockrock")`

## Translate Tongdaxin → Python

1. Map `C/O/H/L/V` → DataFrame columns
2. Add `stockrock/strategies/<id>.py` + `@register`
3. Register in `stockrock/strategies/base.py`
4. `pytest` then restart API

Details: repo `AGENTS.md` and `TOOLS.md`.
