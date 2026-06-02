# Stockrock — Tools（Agent API 参考）

默认基址：`http://127.0.0.1:8000`（可通过环境或 OpenClaw 插件配置 `apiBase` 覆盖）。

## Health

```bash
curl -s "$BASE/api/health"
```

## 策略列表

```bash
curl -s "$BASE/api/strategies"
```

## 启动选股任务

```bash
curl -s -X POST "$BASE/api/screen" \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_id": "limit_up_relay",
    "provider": "akshare",
    "lookback_days": 120,
    "exclude_st": true,
    "exclude_bj": true,
    "include_kcb": true,
    "include_cyb": true,
    "max_symbols": 50,
    "strategy_params": { "cost_period": 60 }
  }'
```

返回：`{"job_id":"<uuid>"}`

### 查询进度 / 结果

```bash
JOB_ID="<uuid>"
curl -s "$BASE/api/screen/$JOB_ID"
```

SSE 进度：

```bash
curl -N "$BASE/api/screen/$JOB_ID/events"
```

## 自选列表

```bash
# 列表
curl -s "$BASE/api/watchlist"

# 添加一只
curl -s -X POST "$BASE/api/watchlist" \
  -H "Content-Type: application/json" \
  -d '{"code":"600519","name":"贵州茅台"}'

# 批量添加（筛选结果）
curl -s -X POST "$BASE/api/watchlist/batch" \
  -H "Content-Type: application/json" \
  -d '{"items":[{"code":"600519","name":"贵州茅台"},{"code":"000001","name":"平安银行"}]}'

# 行情
curl -s "$BASE/api/watchlist/quotes"

# 移出
curl -s -X DELETE "$BASE/api/watchlist/600519"
```

## 终端一键启动服务

```bash
cd /path/to/stockrock && source .venv/bin/activate
uvicorn stockrock.api.main:app --host 127.0.0.1 --port 8000
```

或使用入口：`stockrock`（安装后 `pyproject` scripts）。

## Web UI

构建后访问：`http://127.0.0.1:8000/`（`web/dist` 由 FastAPI 挂载）。

开发模式：`cd web && npm run dev`（5173 代理 `/api`）。
