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
# 1. Clone or use existing repo
cd /path/to/stockrock

# 2. Python environment
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 3. Config
cp .env.example .env

# 4. Frontend (optional, for Web UI)
cd web && npm install && npm run build && cd ..

# 5. Start API
uvicorn stockrock.api.main:app --host 0.0.0.0 --port 8000
```

Health check: `curl -s http://127.0.0.1:8000/api/health`

## Plugin install (OpenClaw)

From repo root or any machine with the repo:

```bash
openclaw plugins install --link /path/to/stockrock/plugins/stockrock
openclaw plugins enable stockrock
openclaw gateway restart
```

Load skill context: workspace `skills/stockrock/SKILL.md` or plugin-bundled skill.

## Plugin install (Hermes)

```bash
hermes plugins install /path/to/stockrock/plugins/stockrock --enable
# or from Git:
# hermes plugins install <owner>/stockrock --enable
```

Load in session: `skill_view("stockrock:stockrock")`

## Translate Tongdaxin → Python

1. Read formula; map `C/O/H/L/V` → `close/open/high/low/volume`
2. Add file under `stockrock/strategies/<id>.py` with `@register` class extending `Strategy`
3. Import from `stockrock.indicators.tdx` (and `cyq`, `board` if needed)
4. Register in `stockrock/strategies/base.py` `_load_builtin_strategies()`
5. Run `pytest`; restart API

Existing strategies: `ma_cross`, `limit_up_relay`, `uptrend_chips`, `low_sideways_build`, `soul_hook`, `mizhuang_qinniu`, `four_line_rise`, `mizhuang_rebound`, `qianfu_niugu`, `zhuangjia_taijiao`

## API (via terminal / curl)

| Action | Method | Path |
|--------|--------|------|
| List strategies | GET | `/api/strategies` |
| Start screen | POST | `/api/screen` |
| Job status | GET | `/api/screen/{job_id}` |
| Watchlist | GET | `/api/watchlist` |
| Add watchlist | POST | `/api/watchlist` |
| Quotes | GET | `/api/watchlist/quotes` |
| Remove | DELETE | `/api/watchlist/{code}` |

See repo `TOOLS.md` for JSON bodies.

## Screening tips

- First run is slow (AKShare); cache under `data/cache/` speeds reruns
- Use `max_symbols: 50` in POST body for testing
- `STOCKROCK_SCREEN_WORKERS` controls parallel scan threads (default ~8–16)

## Verification

```bash
pytest -q
curl -s http://127.0.0.1:8000/api/strategies | head
```
