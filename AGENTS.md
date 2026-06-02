# Stockrock — Agent 工作区说明

本仓库可作为 **OpenClaw / Hermes** 工作区使用。Agent 在此项目中应能**自动完成安装、启动服务、翻译通达信公式、调用选股 API**。

## 首次自动安装（推荐顺序）

当用户要求使用 Stockrock 且环境未就绪时，按序执行：

```bash
REPO="$(pwd)"   # 或用户提供的 stockrock 绝对路径
cd "$REPO"

# Python 3.11+
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

test -f .env || cp .env.example .env

# Web 静态资源（若 web/dist 不存在）
if [ ! -d web/dist ]; then
  (cd web && npm install && npm run build)
fi

# 后台启动 API（若 8000 未监听）
if ! curl -sf http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
  nohup uvicorn stockrock.api.main:app --host 127.0.0.1 --port 8000 \
    > /tmp/stockrock-api.log 2>&1 &
  sleep 2
fi

curl -s http://127.0.0.1:8000/api/health
pytest -q
```

安装失败时：检查 Python 版本、网络（AKShare）、`web/node_modules` 权限。

## OpenClaw 插件安装

```bash
openclaw plugins install --link /absolute/path/to/stockrock/plugins/stockrock
openclaw plugins enable stockrock
openclaw gateway restart
openclaw plugins inspect stockrock --runtime --json
```

本仓库根目录另有 `openclaw.plugin.json`（将整个 repo 作为技能包时可用 `openclaw plugins install --link .`）。

配置示例（`openclaw.json`）：

```json5
{
  plugins: {
    entries: {
      stockrock: {
        enabled: true,
        config: {
          repoPath: "/absolute/path/to/stockrock",
          apiBase: "http://127.0.0.1:8000",
        },
      },
    },
  },
}
```

## Hermes 插件安装

```bash
hermes plugins install /absolute/path/to/stockrock/plugins/stockrock --enable
hermes plugins list
```

项目内启用（可选）：

```bash
export HERMES_ENABLE_PROJECT_PLUGINS=true
mkdir -p .hermes/plugins
ln -sf ../../plugins/stockrock .hermes/plugins/stockrock
```

加载技能：`skill_view("stockrock:stockrock")`（见 `skills/stockrock/SKILL.md`）。

## 核心职责

| 任务 | 做法 |
|------|------|
| 通达信公式 → 策略 | 新建 `stockrock/strategies/*.py`，用 `tdx`/`cyq`/`board`，`@register` 并改 `base.py` |
| 运行选股 | `POST /api/screen`，轮询 `GET /api/screen/{job_id}` 或 SSE |
| 自选 | `POST /api/watchlist`，行情 `GET /api/watchlist/quotes` |
| 验证 | `pytest` + `curl /api/health` |

API 详情见 [TOOLS.md](TOOLS.md)。

## 环境变量（`.env`）

| 变量 | 说明 |
|------|------|
| `STOCKROCK_DATA_PROVIDER` | `akshare`（默认）或 `tushare` |
| `STOCKROCK_SCREEN_WORKERS` | 全市场扫描并行线程数 |
| `STOCKROCK_WATCHLIST_PATH` | 自选 JSON 路径 |
| `TUSHARE_TOKEN` | Tushare 可选 |

## 相关文件

| 文件 | 用途 |
|------|------|
| [TOOLS.md](TOOLS.md) | HTTP API 与 curl 示例 |
| [skills/stockrock/SKILL.md](skills/stockrock/SKILL.md) | OpenClaw/Hermes 技能正文 |
| [BOOTSTRAP.md](BOOTSTRAP.md) | 首次接入工作区时的检查清单 |
| [README.md](README.md) | 人类用户安装说明 |
| [plugins/stockrock/](plugins/stockrock/) | Hermes/OpenClaw 插件目录 |

## 约束

- 仅供个人研究，不构成投资建议
- 勿将 `.env` 中的 Token 提交到 Git
- `WINNER`/筹码类指标为 OHLCV 近似，与通达信可能有偏差
