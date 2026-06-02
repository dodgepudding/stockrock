# Stockrock — OpenClaw / Hermes 插件安装

## 目录结构

```
stockrock/
├── AGENTS.md              # Agent 工作区总说明（自动安装流程）
├── TOOLS.md               # HTTP API 工具文档
├── BOOTSTRAP.md           # 首次接入检查清单
├── openclaw.plugin.json   # 以整个 repo 安装时的清单
├── skills/stockrock/SKILL.md
└── plugins/stockrock/     # 推荐插件包路径
    ├── openclaw.plugin.json
    ├── plugin.yaml        # Hermes
    ├── __init__.py        # Hermes register(skills)
    └── skills/stockrock/SKILL.md
```

## OpenClaw

```bash
# 方式 A：仅插件包（推荐）
openclaw plugins install --link /path/to/stockrock/plugins/stockrock
openclaw plugins enable stockrock
openclaw gateway restart

# 方式 B：整个仓库作为插件（含根 skills/）
openclaw plugins install --link /path/to/stockrock
openclaw plugins enable stockrock
openclaw gateway restart
```

验证：

```bash
openclaw plugins inspect stockrock --runtime --json
```

文档：<https://docs.openclaw.ai/plugins>

## Hermes

```bash
hermes plugins install /path/to/stockrock/plugins/stockrock --enable
hermes plugins list
```

会话中加载技能：

```text
skill_view("stockrock:stockrock")
```

文档：<https://hermes-agent.nousresearch.com/docs/user-guide/features/plugins>

## 与本仓库服务的关系

插件**不替代** Python 服务：Agent 仍需按 `AGENTS.md` 安装依赖并启动 `uvicorn`，再通过 `TOOLS.md` 中的 HTTP API 或 Web UI 操作。

## 从 OpenClaw 迁移到 Hermes

官方命令：`hermes claw migrate`（迁移配置、技能、记忆等）。Stockrock 策略代码仍在仓库内，无需迁移。
