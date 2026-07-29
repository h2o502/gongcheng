---
slug: gongyi
displayName: 工艺
version: 1.3.2
summary: AI 协同编程的项目记忆中继站，SQLite 知识库 + 开发/审查/交接三模式。
license: MIT
name: gongyi
description: |
  工艺 (gongyi) — AI 协同编程的项目记忆中继站（原 MemBridge 通忆）。

  解决的核心问题：在 AI 开发、人类审查、AI 继续开发的循环中，
  信息如何在人、AI、不同 session、不同 agent 之间无损传递。

  工作方式：
  1. AI 开发完 → 增量更新 SQLite 知识库（记录变更、约束、API、符号）
  2. 交接给人类 → 导出审查清单（REVIEW.md）和变更摘要（CHANGELOG.md）
  3. 人类确认后 → 新 AI 读 CONTEXT.md 建立心智模型，按需查询继续开发
  4. 版本完成 → 导出完整项目说明书（PROJECT_SPEC.md）

  三种模式：
  - 开发模式：AI 直接查询 SQLite，精确拉取上下文（500 token 内定位）
  - 审查模式：人类快速查看 AI 做了什么、是否踩红线
  - 交接模式：完整 Markdown 文档，跨 session / agent / 团队传递

  触发场景（写入）：
  "修改代码后更新记忆"、"版本交接"、"导出项目说明书"
  触发场景（查询）：
  "查询项目约束/红线"、"改 X 模块前要查什么"、"接手 session 前查最近变更"、
  "重构影响面评估"、"这个 API 谁在用"、"数据库表结构查询"、"ADR 决策追溯"
license: MIT
---

# 工艺 (gongyi) — AI 协同编程的记忆中继站

> 原 MemBridge（通忆），"工"字系列通用 skill。
> 知识库路径由 `gongkong/config.yaml` 的 `memory.db_path` 注入。

一个知识库，三种工作模式：

| 模式 | 格式 | 使用者 | 场景 |
|------|------|--------|------|
| **开发模式** | SQLite + CONTEXT.md | AI | 日常开发时按需查询精确信息 |
| **审查模式** | 变更摘要 + 审查清单 | 人类 | 快速查看 AI 做了什么，有没有踩红线 |
| **交接模式** | 完整 Markdown | 人类/其他AI/新session | 项目交接、团队共建、新人上手 |

## 开发循环工作流

这个 skill 设计为支撑"大循环套小循环"的开发模式：

```
版本迭代（大循环）
├── AI 开发 → build_db.py --incremental → 知识库更新
├── 人类审查 → export_md.py --review → 审查清单
├── AI 继续开发 → build_db.py --incremental → 知识库更新
├── 人类审查 → export_md.py --review → 审查清单
├── ... 重复 ...
└── 版本完成 → export_md.py → 完整 PROJECT_SPEC.md
```

## 核心架构

```
项目目录/
├── .ai/                              # memory.db_path 由 gongkong/config.yaml 注入
│   ├── project.ai.db        # SQLite 知识库（开发模式核心）
│   ├── CONTEXT.md           # L1 导航文件（AI 首次读取）
│   ├── build_db.py          # 构建脚本（也可从 skill 目录调用）
│   ├── query_db.py          # AI 查询脚本（支持 SQL 直传）
│   ├── export_md.py         # 导出脚本（SQLite → 完整 Markdown）
│   └── init_project.sh      # 快速初始化（可选）
└── docs/
    └── PROJECT_SPEC.md      # 交接模式输出（由 export_md.py 生成）
```

**注意**：知识库路径（`.ai/project.ai.db`）由 `gongkong/config.yaml` 的 `memory.db_path` 字段提供，相对 `project.root`。换项目时改 config.yaml 即可。

## 查询决策树（AI 改动前必查）

> **只读查询不需要 build**。DB 已存在时直接调 `query_db.py`；DB 不存在则降级读 `CONTEXT.md` 或源码，并在本轮改完代码后跑一次 `build_db.py` 首次构建。

| 信号 | 查哪张表 | 示例 SQL |
|------|---------|---------|
| 会话启动 / 接手 session | change_log + constraints + meta | 见下方"会话启动查询序列" |
| 改 X 模块前 | constraints | `SELECT rule, severity FROM constraints WHERE affected_modules LIKE '%X%' AND severity IN ('forbidden','critical')` |
| 评估重构影响面 | symbols + api_routes | `SELECT name, called_by FROM symbols WHERE module_id IN (SELECT id FROM modules WHERE name='X')`；`SELECT method, path, handler FROM api_routes WHERE handler LIKE '%X%'` |
| 排查某函数 | symbols | `SELECT signature, calls, called_by, line_number FROM symbols WHERE name='X'` |
| 追溯某决策 | decisions | `SELECT title, context, decision, consequences FROM decisions WHERE code='ADR-001'` |
| 查表结构 | tables | `SELECT purpose, fields, relations FROM tables WHERE name='X'` |
| 查某模块详情 | modules | `SELECT responsibility, entry_func, file_path, deps, constraints FROM modules WHERE name='X'` |
| 查认证相关 API | api_routes | `SELECT method, path, handler FROM api_routes WHERE auth != 'none'` |

### 会话启动查询序列

新 session 启动时（与 gongyou 协议1 配合），若 DB 存在，跑一次以下三连查建立心智模型：

```bash
python query_db.py <db> --sql "SELECT timestamp, module, change_type, description, author FROM change_log ORDER BY id DESC LIMIT 10"
python query_db.py <db> --sql "SELECT rule, affected_modules FROM constraints WHERE severity='forbidden'"
python query_db.py <db> --sql "SELECT key, value FROM meta"
```

> DB 不存在时降级：读 `CONTEXT.md` → 读 `PROJECT_MEMORY.md` → 读源码。本轮改完代码后由 `build_db.py` 首次构建。

## 工作流程

### 首次接入项目

1. **扫描项目** — 运行 `init_project.sh` 或 `build_db.py` 解析源码，填充 SQLite
2. **生成 CONTEXT.md** — 自动产出 ~500 token 的 L1 导航文件
3. **注入约束模板** — 初始红线规则（金额、安全、权限等）
4. **AI 首次读取** — 新 AI session 先读 CONTEXT.md 建立心智模型

### 日常开发循环

```bash
# AI 开发完一段代码后 — 增量更新知识库（几秒完成）
cd <project.root>/.ai && python3 build_db.py <project.root> --incremental --author 'AI-session-xxx'

# AI 按需查询
cd <project.root>/.ai && python3 query_db.py "这次循环改了什么"       # 查看最近变更
cd <project.root>/.ai && python3 query_db.py billing                  # 查 billing 约束
cd <project.root>/.ai && python3 query_db.py --sql "SELECT rule FROM constraints WHERE severity='forbidden'"
```

AI 有两种查询方式：
- **自然语言模式** — `query_db.py "用户创建 token 的流程"` → 自动匹配 SQL
- **SQL 直传模式** — `query_db.py --sql "SELECT ..."` → AI 直接写 SQL 精确查询

### 交接给人类审查

```bash
# 生成变更摘要（diff 模式）
cd <project.root>/.ai && python3 export_md.py project.ai.db --diff -o CHANGELOG.md

# 生成人类审查清单
cd <project.root>/.ai && python3 export_md.py project.ai.db --review -o REVIEW.md
```

CHANGELOG.md 包含：最近变更列表、变更统计、可能违反约束的警告。
REVIEW.md 包含：变更概览、约束审查清单（标记 forbidden/critical）、变更影响面、审查确认 checkbox。

### 人类审查后交还给 AI

人类看完 REVIEW.md，确认 checkbox，然后 AI 继续下一轮开发。每次循环：
1. AI 改代码 → `build_db.py --incremental` 更新知识库
2. `export_md.py --review` 生成审查清单给人类
3. 人类确认 → 回到第 1 步

### 版本迭代完成时

```bash
# 导出完整 Markdown 文档
cd <project.root>/.ai && python3 export_md.py project.ai.db --output docs/PROJECT_SPEC.md
```

生成的 Markdown 包含：
- 项目概述与一句话定位
- 系统架构分层图（Mermaid）
- 完整 API 路由清单
- 数据库 ER 图 + 字段说明
- 关键业务链路（Sequence Diagram）
- 核心模块清单与依赖关系
- 所有 ADR 决策记录
- 全部约束（按严重度分级）
- 配置项清单
- 变更日志

## 脚本说明

### `scripts/build_db.py` — 构建/更新知识库

```bash
python build_db.py <项目路径> [--output <db路径>] [--incremental] [--force]
```

**功能**：
1. 自动检测项目语言（Go/Python/JS/TS）
2. 扫描源码文件，提取模块、符号、API 路由
3. 解析数据库表定义
4. 收集代码中的决策注释和约束
5. 构建/更新 SQLite 数据库
6. 自动生成/更新 CONTEXT.md

**增量模式**（`--incremental`）：
- 只扫描变更过的文件（对比文件 mtime）
- 保留手工维护的 ADR 和约束
- 更新 change_log 表记录变更

### `scripts/query_db.py` — AI 查询接口

```bash
# 自然语言查询
python query_db.py <db路径> "用户创建 token 的流程"

# SQL 直传（AI 专用）
python query_db.py <db路径> --sql "SELECT name, responsibility FROM modules WHERE layer='billing'"

# 指定输出格式
python query_db.py <db路径> "列出所有 API" --format json|table|md
```

**AI 查询优先级**：
1. 如果提供 `--sql`，直接执行 SQL
2. 尝试匹配预定义的自然语言模式
3. 退化为多表 LIKE 搜索

### `scripts/export_md.py` — 导出完整 Markdown

```bash
python export_md.py <db路径> [--output <输出路径>] [--include-diagrams]
```

**输出内容**：
- 项目概述（meta 表）
- 架构分层图（modules 表 → Mermaid flowchart）
- API 完整清单（api_routes 表 → 表格）
- 数据库 ER 图（tables 表 → Mermaid erDiagram）
- 字段说明（tables.fields → 表格）
- 关键业务链路（data_flow 表 → Mermaid sequenceDiagram）
- 核心模块索引（modules 表 → 表格）
- ADR 决策记录（decisions 表 → 分级标题）
- 约束清单（constraints 表 → 按 severity 分组）
- 配置项（config 表 → 表格）
- 变更日志（change_log 表 → 表格）

### `scripts/init_project.sh` — 快速初始化

```bash
bash init_project.sh <项目路径>
```

在项目下创建 `.ai/` 目录，复制所有脚本，自动运行首次构建。

## 表结构

详见 `references/schema.md`。

核心 8 张表：
- `meta` — 项目元信息
- `modules` — 模块骨架
- `symbols` — 符号表
- `api_routes` — API 路由
- `tables` — 数据库表
- `decisions` — ADR 决策记录
- `constraints` — 业务约束
- `config` — 配置项

可选 2 张表：
- `data_flow` — 数据流文档
- `change_log` — 代码变更日志

## 最佳实践

### 给 AI 的建议

1. **首次接触项目** — 先读 `CONTEXT.md`，不要直接读源码
2. **查询精确信息** — 用 `query_db.py --sql` 而不是读整个 spec
3. **修改代码前** — 查 constraints 表中 related module 的 forbidden/critical 规则
4. **修改代码后** — 运行 `build_db.py --incremental` 更新知识库
5. **需要交接时** — 运行 `export_md.py` 生成完整文档

### 两套 memory 分工（避免重复查询）

| 记忆源 | 存什么 | 何时查 |
|--------|--------|--------|
| trae memory（`/root/.trae-cn/memory`） | 跨会话用户偏好、项目硬约束、话题历史 | 会话启动 memory pass、需要历史决策脉络 |
| gongyi SQLite | 项目代码结构化知识：模块/符号/API/表/ADR/约束/变更日志 | 改代码前查影响面、查具体模块约束、追溯 ADR |

**规则**：问"人/会话/偏好"→ trae memory；问"代码/模块/表/决策"→ gongyi。

### 给人类的建议

1. **查看项目全貌** — 直接读 `docs/PROJECT_SPEC.md`
2. **查看决策历史** — 读 `PROJECT_SPEC.md` 的 ADR 章节
3. **查看红线** — 读约束清单中标记为 forbidden 的条目
4. **手工补充 ADR** — 可以在数据库中直接 INSERT 到 decisions 表

## 与其他工字 skill 的协作

- **gongcheng**：gongyi 是 gongcheng 工作类型表第 4 行（写入）+ 第 4b 行（查询）的执行 skill
- **gongkong**：知识库路径由 `gongkong/config.yaml` 的 `memory.db_path` 注入
- **gongyou**：协议1 启动时执行"会话启动查询序列"拉最近变更+红线；协议2 改动前检查第 1 步先查 gongyi `constraints`（`affected_modules` 命中目标模块）+ `symbols.called_by`（反向依赖），DB 不存在才降级到 `check-impact.sh` 的本地 `#@` 索引
- **gongsheji**：设计阶段可查询 gongyi 了解现有架构和约束

## 适用场景

- 复杂项目的 AI 辅助开发
- 跨 session / agent 的工作交接
- 团队共建项目（不同人负责不同模块）
- 新人（人类或 AI）快速上手
- 代码审查前的结构了解
- 项目文档自动化维护
