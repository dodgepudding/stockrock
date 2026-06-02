# Stockrock — A股选股（通达信公式 → Python 策略）

个人研究用途的 A 股全市场选股工具。将通达信选股条件粘贴给 AI 翻译成 Python 策略后，在 Web 界面一键扫描。

## OpenClaw / Hermes 插件

本仓库提供 Agent 自动安装说明与插件包：

| 文件 | 说明 |
|------|------|
| [AGENTS.md](AGENTS.md) | Agent 工作区：安装、启动、翻译公式、插件命令 |
| [TOOLS.md](TOOLS.md) | HTTP API（curl）参考 |
| [BOOTSTRAP.md](BOOTSTRAP.md) | 首次接入检查清单 |
| [PLUGIN.md](PLUGIN.md) | OpenClaw / Hermes 插件安装步骤 |
| [skills/stockrock/SKILL.md](skills/stockrock/SKILL.md) | 技能文件（`skill_view` / 工作区技能） |

```bash
# OpenClaw
openclaw plugins install --link ./plugins/stockrock
openclaw plugins enable stockrock && openclaw gateway restart

# Hermes
hermes plugins install ./plugins/stockrock --enable
```

## 功能

- 通达信语义指标库（`REF`、`MA`、`CROSS`、`HHV` 等）
- 可插拔行情源：默认 **AKShare**，可选 **Tushare Pro**
- 本地 Parquet 缓存，支持**增量更新**（仅下载缺失日期，非每次全量）
- Web 界面：选策略、看进度、导出 CSV
- **自选列表**：筛选结果一键加入自选，查看实时行情、移出自选（本地 `data/watchlist.json`）

## 环境要求

- Python 3.11+
- Node.js 18+（仅构建前端时需要）

## 安装

```bash
cd /path/to/stockrock
python3.12 -m venv .venv   # 需要 Python 3.11+
source .venv/bin/activate
pip install -e ".[dev]"

# 可选 Tushare
pip install -e ".[tushare]"

cp .env.example .env
```

## 启动

### 仅 API（开发）

```bash
uvicorn stockrock.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### API + 前端

```bash
cd web && npm install && npm run build && cd ..
uvicorn stockrock.api.main:app --host 0.0.0.0 --port 8000
```

浏览器打开 http://localhost:8000

### 前端开发模式

```bash
# 终端 1
uvicorn stockrock.api.main:app --port 8000 --reload

# 终端 2
cd web && npm install && npm run dev
```

访问 http://localhost:5173（Vite 代理 `/api` 到 8000）

## 通达信公式工作流

1. 在通达信写好「选股条件」，复制全文
2. 粘贴到对话中，说明要新增策略
3. AI 在 `stockrock/strategies/` 下新增模块并 `@register`
4. 重启 API 或热重载后，在 Web「策略」列表中选择并扫描

### 指标约定（与通达信对齐）

| 函数 | 含义 |
|------|------|
| `REF(X,n)` | n 根 K 线前的值，n=1 为昨日 |
| `CROSS(A,B)` | 今日 A>B 且昨日 A≤B |
| `MA(X,n)` | 含当根的 n 日简单均线 |

行情默认 **前复权（qfq）**。

## 新增策略示例

见 [`stockrock/strategies/example_ma_cross.py`](stockrock/strategies/example_ma_cross.py)。

## 配置

| 变量 | 说明 |
|------|------|
| `STOCKROCK_DATA_PROVIDER` | `akshare` 或 `tushare` |
| `TUSHARE_TOKEN` | Tushare Pro Token |
| `STOCKROCK_CACHE_DIR` | 缓存目录 |
| `STOCKROCK_CACHE_INCREMENTAL_OVERLAP_DAYS` | 增量更新时与缓存重叠天数（默认 5，防复权修正） |
| `STOCKROCK_LOOKBACK_DAYS` | 默认回看天数 |
| `STOCKROCK_SCREEN_WORKERS` | 全市场扫描并行线程数（默认 `min(16, CPU×2)`，适合 I/O 型行情拉取） |

全市场扫描使用线程池并行拉取 K 线与策略判定。线程过多可能触发 AKShare 等接口限流，可适当调低 `STOCKROCK_SCREEN_WORKERS`（例如 `4`）。

## 测试

```bash
pytest
```

## 免责声明

本软件仅供学习与研究，不构成投资建议。行情数据来自第三方接口，请遵守相应服务条款。
