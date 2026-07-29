---
slug: gongcheng
displayName: 工成 · Vibecoding 全生命周期 AI 工程 Skill
version: 1.3.2
summary: 覆盖 Vibecoding 全生命周期的工程编排层，用 PlantUML 固化架构，具备自我迭代能力。v1.3 明确 gongxu（工需）与 gongchan（工产）分工，gongxu 产出工需建议书作为 gongchan 的强制输入。
license: MIT
name: gongcheng
description: |
  首个必须加载的通用工程编排 Skill。
  沉淀自多个 AI 项目落地实战经验，贯穿需求澄清、产品设计、架构设计、代码实现、文档沉淀与持续复盘。
  以 PlantUML 记录项目架构，以规则驱动工作流自我迭代。
  服务器代码更新由 gongkong/config.yaml 配置；开源版仅含模板，请勿提交账号密码。
tags:
  - vibecoding
  - project-design
  - plantuml
  - self-improvement
  - ai-engineering
  - architecture
  - chinese
---

# 工成 (gongcheng) — Vibecoding 全生命周期 AI 工程 Skill

> **首个必须加载的通用工程编排 Skill**。沉淀自多个 AI 项目落地实战经验，贯穿需求澄清、产品设计、架构设计、代码实现、文档沉淀与持续复盘。
> **不含项目专属配置**：Gitea 地址、SSH 别名、部署路径等全部由 `gongkong/config.yaml` 注入。
> 以 PlantUML 记录项目架构，以规则驱动工作流自我迭代。开源版仅含模板，请勿提交账号密码。

本包是 gongcheng 及其子 skill 的开源发布形态。gongcheng 既是包名也是核心编排 skill，
其余工字系列子 skill（gongwen/gongxu/gongchan/gongsheji/gongyi/gonghua/gongtu/gongyou/gongshu/gongkong）和工具层（tools/ 下含 md2docx/md2html/svg/pdf/excel/ppt/docx）作为子目录包含在本包中。

---

## 一、强制规则（不可违反）

任何涉及以下类型的工作，**必须先加载对应子 skill**：

| # | 工作类型 | 必须加载的通用 skill | 项目配置（由 gongkong/config.yaml 注入） | 违反后果 |
|---|---------|---------------------|------------------------------------------|---------|
| 1 | **修改代码/提交代码/部署** | gongsheji + gongyou | `git.repositories`（项目仓库列表） | 代码无法追溯，禁止操作 |
| 2 | **文档创建/转换（.md ↔ .docx / .html）** | md2docx + md2html | - | 格式不规范，禁止操作 |
| 3 | **项目设计/架构决策/方案规划** | gongsheji | - | 缺少规范流程，禁止操作 |
| 4 | **改动代码/更新项目状态** | gongyi | `memory.db_path`（知识库路径） | 知识库不同步，禁止操作 |
| 5 | **界面设计/前端页面开发/视觉改造** | gonghua | - | 防止 AI 生成千篇一律的通用界面，确保设计质量 |
| 6 | **服务器文件上传/远程脚本执行/SSH 部署** | gongkong（部署层） | `ssh` + `deploy.remote_root` + `deploy.remote_ps1` | 禁止在远程命令中拼 heredoc 或复杂引号字符串 |
| 7 | **画图/架构图/类图/流程图渲染** | gongtu | - | 文本图源码无法可视化 |
| 8 | **改动前影响检查/踩坑标注** | gongyou | `high_risk_files`（高风险文件清单） | 修 B 破 A，破坏未知依赖 |
| 9 | **方案审问/需求澄清/商业三问** | gongwen | - | 需求未澄清就写代码，返工率极高 |
| 10 | **Office 文档读写（.xlsx/.pptx/.docx/.pdf）** | tools/excel + tools/ppt + tools/docx + tools/pdf | - | 直接改 OOXML 易破坏样式/公式/布局 |
| 11 | **SVG 图形创建/优化** | tools/svg | - | 缺 viewBox/无障碍属性，可伸缩性与可访问性差 |
| 12 | **数据库读写/批量数据操作** | gongshu | `db.connections`（数据库连接清单）+ `db.sensitive_fields`（敏感字段） | 数据不可恢复，禁止操作 |

**额外红线（代码修改时必须遵守）**：
- **禁止使用全局字符串替换**（如 `sed -i s/old/new/ file`、Python `content.replace(old,new)`、PowerShell `-replace` 等）。搜索到的匹配项可能分布在不相关的函数/模块中，修改一处却破坏多处。
- **正确做法**：先定位到具体行/函数，用精确的行级或范围级方式修改（`sed -i 123s/old/new/` 按行号替换、在本地用工具读取-精确编辑-回写、或直接用 file edit 操作）。每次修改后必须编译/测试确认无误。

**额外红线（数据操作时必须遵守）**：
- **禁止无备份执行 L3/L4 数据操作**（批量 UPDATE/DELETE、DROP/TRUNCATE、覆盖敏感字段）。必须先 `CREATE TABLE backup_<table>_<date> AS SELECT ...` 备份受影响行，再执行。
- **禁止覆盖敏感字段前不导出原值**（password_hash/token/secret/balance 等）。必须先 `CREATE TABLE audit_<table>_<date> AS SELECT id, <敏感字段>, NOW() FROM ...` 记录原值。
- **禁止无 WHERE 的 UPDATE/DELETE**。如必须全表操作，按 L4 处理，需用户二次确认。
- **禁止默认选择破坏性更大的指令理解**。遇到歧义必须追问（详见 gongshu 协议4）。
- **正确做法**：先 EXPLAIN/COUNT 预估影响 → 备份 → 生成回滚 SQL → 用户确认 → 执行 → 验证 → 审计日志。

**检查流程**（每次开始工作前执行）：
1. **加载 gongkong**：读取 `gongkong/config.yaml`，注入项目专属配置（git 仓库/SSH/部署路径/memory 路径/高风险文件清单）
2. **识别工作类型**（代码/文档/设计/部署/画图/其他）
3. **逐一对照上表**，确认对应通用 skill 已加载，项目配置已注入
4. **评估是否能直接 SSH**：如遇到写入失败、复杂嵌套命令、网络超时等问题 → 降级使用项目配置的远程执行通道
5. **评估是否有多个互不干涉的任务**：设计任务拆分 → 通过项目配置的任务派发机制并行执行
6. **如有遗漏，先加载 skill 再继续**
7. **工作完成后**，确认所有变更已 commit + push + 同步知识库

---

## 二、Git 代码管理规范（通用纪律）

> 项目专属信息（Gitea 地址、仓库列表、SSH 别名）由 `gongkong/config.yaml` 提供。
> 本节只包含通用 Git 纪律，适用于任何项目。

### 2.1 核心原则（不可违反）

| # | 原则 | 说明 |
|---|------|------|
| 1 | 所有代码必须进 Git | 任何修改过的代码文件，必须提交到 Git 仓库，禁止留在本地不提交 |
| 2 | 禁止手工 bak | 不准创建 xxx.bak xxx.bak2 等手工备份文件。版本历史本身就是备份 |
| 3 | 修改后必须提交 | 改完代码后，必须执行提交流程，不得遗留未提交的修改 |
| 4 | 先提交再走人 | session 结束前，必须确保所有修改都已 commit + push |

### 2.2 提交流程（必须严格遵守）

```
第 1 步：确认改了哪些项目（项目源码路径由 gongkong/config.yaml 的 project.root 提供）

第 2 步：将修改同步到对应仓库目录
  rsync -a --exclude='.git' --exclude='node_modules' --exclude='*.bak' \
    --exclude='*.db' --exclude='*.sqlite' --exclude='*.log' \
    --exclude='uploads/' --exclude='.env' \
    <project.root>/<项目名>/ <git.repositories[i].local_path>/

第 3 步：进入对应仓库，提交
  cd <git.repositories[i].local_path>
  git add -A
  git commit -m "描述你改了什么"
  git push

第 4 步：确认推送成功
  git log --oneline -3
```

### 2.3 commit message 规范

格式：`<类型>: <简短描述>`

类型：
- `feat` - 新功能
- `fix` - 修 bug
- `docs` - 文档
- `style` - 代码格式
- `refact` - 重构
- `config` - 配置变更
- `init` - 初始化

### 2.4 回滚操作

**安全回滚（推荐，保留历史记录）**：
```bash
cd <repo.local_path>
git revert HEAD
git push
```

**强制回滚（会丢失中间提交，必须用户明确确认后执行）**：
```bash
cd <repo.local_path>
git reset --hard <目标版本号>
git push -f
```

### 2.5 红线规则

- 不创建 .bak 文件：任何时候都禁止创建 *.bak *.bak.* 文件。Git 历史就是最好的备份
- 不提交大文件：.db .sqlite node_modules/ uploads/ *.log 禁止提交
- 不强制推送：git push -f 需要用户明确说"强制推送"才能执行
- 不遗留未提交修改：session 结束前必须检查并提交所有修改
- 不直接改 Git 镜像目录下的文件：应该改源码目录，再 rsync 同步
- 敏感信息处理：自建 Gitea 时密码、token 不用脱敏；公共仓库须脱敏

### 2.6 前端资源版本管理

当修改前端静态资源（如 `chat.css`、`chat.js`）时，**必须同步更新所有引用这些资源的 HTML 文件中的版本号**。

HTML 通过 `?v=xxx` 查询参数引用资源。只修改 CSS/JS 但不更新版本号，浏览器会使用缓存的旧文件。

**正确流程**：
1. 修改 CSS/JS 文件内容
2. 更新文件内部的版本注释（如 `v3.1` → `v4.0`）
3. 同步更新所有 HTML 文件中的引用版本号（`?v=3.1` → `?v=4.0`）

版本号命名：语义化版本号（v1.0, v1.1, v2.0），小改小版本，大改大版本。

### 2.7 自动快照（可选）

项目可配置每天凌晨自动遍历所有仓库，有修改则自动 commit + push。
commit message: `auto-snapshot: [日期] 自动备份`

---

## 三、子 Skill 索引

> 本包目录结构：gongcheng 本身是根 skill，其余工字系列 skill 是子目录，工具类在 `tools/` 下。

### 3.1 工字系列子 skill

按 Vibecoding 工作流顺序排列：

```
gongwen（工问）→ gongxu（工需）→ gongchan（工产）→ gongsheji（工设计）
       ↓              ↓                  ↓                  ↓
   商业方案      工需清单/标准       产品设计/PRD         代码实现
```

横向守护与记忆：`gongyou`（文件守护）、`gongshu`（数据守护）、`gongtu`（图渲染）、`gonghua`（前端实现）、`gongyi`（项目记忆）、`gongkong`（项目配置）

#### gongwen（工问）
- **位置**：`gongwen/`
- **功能**：方案审问与方案底稿。把客户文档/口述想法通过追问、压力测试、矛盾检测逼问成结构化方案底稿
- **产出**：`draft.yaml` + `PROPOSAL.md` + `PENDING.md`，定稿后移交 gongxu 或 gongchan
- **商业三问**：商业项目必填"卖什么/给谁/为什么买你的"，含反模式检测
- **触发场景**：客户给方案文档要实现、想法需要追问清楚、写 spec 前先审问需求

#### gongxu（工需）
- **位置**：`gongxu/`
- **功能**：工程需求自驱引擎。让人类和 AI 在工程协作中自然生长出"需要做什么"，建立自驱标准并持续反刍
- **产出**：《任务信号卡》《追问清单》《工需标准 v1.0》《工需清单》《自生需求补充》《工需建议书》
- **落地路径**：`docs/gongxu/GX-YYYYMMDD-XXX/`
- **边界**：不画图、不写代码、不写具体数据字段
- **触发场景**：用户开始新工程任务、发现理解偏差、交付前验收需求完整性
- **与 gongchan 关系**：gongxu 产出是 gongchan 的**强制输入**

#### gongchan（工产）
- **位置**：`gongchan/`
- **功能**：从需求澄清到产品设计的完整流程。接收 gongxu 工需建议书，产出 PRD/架构/数据/界面/开发交接文档
- **输入**：优先读取 `docs/gongxu/GX-YYYYMMDD-XXX/03_needs.md` 和 `02_standard_v1.md`；如无则执行内置快速需求澄清
- **核心机制**：4 大阶段 18 步，含 demon、分项开会、架构反刍、数据设计、界面设计
- **边界**：不做商业价值判断、不替代 gongxu 建立验收标准
- **触发场景**：新产品设计、系统重设计、从零规划产品
- **与 gongxu 关系**：阶段二/三必须逐项对照工需清单，缺失时回退 gongxu

#### gongsheji（工设计）
- **位置**：`gongsheji/`
- **功能**：严格工程设计工作流。先写 spec → 写 plan → 小步执行（优先 TDD）→ 评审完成
- **触发场景**：新功能设计、架构决策、方案规划、重大重构

#### gonghua（工画）
- **位置**：`gonghua/`
- **功能**：防止 AI 生成千篇一律的通用界面。读取需求后推断设计方向，输出有辨识度的前端页面
- **核心机制**：先做 "Design Read" → 设置三个旋钮（DESIGN_VARIANCE / MOTION_INTENSITY / VISUAL_DENSITY）→ 选择设计系统或原生 CSS
- **触发场景**：新建前端页面、界面视觉改造、组件 UI 设计

#### gongtu（工图）
- **位置**：`gongtu/`
- **功能**：把 PlantUML/Mermaid/D2/Graphviz 等 27 种图源码渲染成 SVG/PNG/PDF 图片
- **依赖**：Kroki（MIT 协议），默认公网 API，可自部署
- **触发场景**：画架构图/类图/时序图/流程图、转 SVG、markdown 图源码可视化

#### gongyou（工优）
- **位置**：`gongyou/`
- **功能**：连续性任务守护。强制改动前影响检查、渐进式记忆加载、踩坑标注
- **4 个协议**：会话启动 / 改动前检查 / 踩坑标注 / 状态更新
- **高风险清单**：由 `gongkong/config.yaml` 的 `high_risk_files` 提供
- **触发场景**：会话启动时、修改任何文件前、发生修 B 破 A 时、会话结束

#### gongshu（工数）
- **位置**：`gongshu/`
- **功能**：数据安全守护。强制风险分级、备份、确认门禁、审计日志
- **4 个协议**：风险分级 / 备份+确认门禁 / 审计日志 / 歧义追问
- **4 级风险**：L1 只读 / L2 单行写 / L3 批量写 / L4 不可逆
- **敏感字段清单**：password_hash/token/secret/balance 等，覆盖时自动升级为 L4
- **高风险 SQL 黑名单**：10 类禁止直接执行的 SQL 模式
- **触发场景**：任何数据库读写前、批量数据操作、覆盖敏感字段、遇到歧义指令
- **与 gongyou 互补**：gongyou 守文件，gongshu 守数据

#### gongyi（工艺）
- **位置**：`gongyi/`
- **功能**：AI 协同编程的项目记忆中继站。增量更新 SQLite 知识库，支持开发/审查/交接三种模式
- **脚本**：`build_db.py`（构建库）、`query_db.py`（查询）、`export_md.py`（导出文档）
- **知识库路径**：由 `gongkong/config.yaml` 的 `memory.db_path` 提供
- **触发场景**：修改代码后更新记忆、查询项目上下文、版本交接

#### gongkong（工控）
- **位置**：`gongkong/`
- **功能**：项目配置注入层。读取同目录 `config.yaml`，向 gongcheng 提供项目专属配置
- **配置文件**：`config.yaml`（真实配置，含密码，**不上传**）+ `config.yaml.example`（脱敏模板，上传）
- **触发场景**：gongcheng 启动时自动加载

### 3.2 工具层

#### 3.2.1 文档转换工具

##### md2docx（工具）
- **位置**：`tools/md2docx/`
- **功能**：Markdown 与 Word 双向转换，支持合并单元格、Mermaid 图表渲染、代码高亮、中文排版优化
- **调用方式**：`python md2docx.py input.md output.docx` 或反向
- **触发场景**：创建/编辑项目文档（.md/.docx）、导出报告
- **注意**：属于 tools/ 工具层，不是工程 skill；不改名（有硬编码路径依赖）

##### md2html（工具）
- **位置**：`tools/md2html/`
- **功能**：Markdown 转 HTML，自动将 ASCII 流程图转换为 Mermaid 语法，浏览器端渲染
- **调用方式**：`python md2html.py input.md output.md` 或 `python md2html.py --html input.md output.html`
- **触发场景**：把设计文档/会议纪要转成可在线浏览的 HTML、将文本流程图转为可视化图表
- **注意**：范围最小化（A最小），目前只处理 ASCII → Mermaid；复杂图请继续用 gongtu 或 PlantUML

#### 3.2.2 Office 文档工具

##### excel（工具）
- **位置**：`tools/excel/`
- **功能**：Microsoft Excel 工作簿读写。公式、日期、类型、格式、合并单元格、模板保真（openpyxl/pandas）
- **触发场景**：处理 `.xlsx/.xlsm/.xls/.csv`、需保留公式/格式/工作簿结构时

##### ppt（工具）
- **位置**：`tools/ppt/`
- **功能**：Microsoft PowerPoint 演示文稿读写。布局、模板、占位符、备注、图表、视觉 QA（python-pptx）
- **触发场景**：处理 `.pptx`、需保留布局/占位符/模板保真时

##### docx（工具）
- **位置**：`tools/docx/`
- **功能**：Microsoft Word 文档读写。样式、编号、修订追踪、表格、节、兼容性检查（OOXML 感知编辑）
- **触发场景**：处理 `.docx`、含修订追踪/域/表格/模板、需往返编辑不漂移时
- **与 md2docx 区别**：md2docx 专做 Markdown↔Word 转换；docx 处理原生 .docx 的深度编辑（OOXML 级）

##### pdf（工具）
- **位置**：`tools/pdf/`
- **功能**：PDF 处理工具集。文本/表格抽取、生成新 PDF、合并/拆分、表单填写（pypdf 等）
- **触发场景**：抽取 PDF 内容、合并/拆分文档、填表单、批量处理 PDF

#### 3.2.3 图形工具

##### svg（工具）
- **位置**：`tools/svg/`
- **功能**：创建和优化 SVG 图形，覆盖 viewBox 缩放、无障碍（role="img"+title）、SVGO 优化、内联 vs `<img>` 嵌入、currentColor 主题化
- **辅助文件**：`viewbox.md` / `accessibility.md` / `optimization.md` / `embedding.md` / `styling.md`
- **触发场景**：手写 SVG 图标/图形、优化现有 SVG、确保可访问性与可伸缩性

## 四、工作流规范（通用骨架）

### 4.1 产品/需求设计完整流程

```
用户提出需求
  │
  ├─ 1. 加载 gongcheng（当前 step，通用编排）
  ├─ 2. 加载 gongkong → 读取 config.yaml 注入项目配置
  │
  ├─ 3. 判断需求清晰度
  │     ├─ 商业价值/目标/约束模糊 → 加载 gongwen → 输出方案底稿
  │     ├─ 工程需求不清晰 → 加载 gongxu → 输出工需建议书
  │     └─ 已有 gongxu 产出 → 直接进入 gongchan
  │
  ├─ 4. 加载 gongchan → 读取 docs/gongxu/GX-YYYYMMDD-XXX/ 工需清单和标准
  ├─ 5. gongchan 阶段一：demon + 分项开会 + 语音转录
  ├─ 6. gongchan 阶段二：模块设计 + 架构汇总 + 反刍 + 工需标准校准
  ├─ 7. gongchan 阶段三：底层架构一致性检查 + 数据结构 + 界面设计
  ├─ 8. gongchan 阶段四：开发交接清单 → 交给 gongsheji
  ├─ 9. 同步记忆 → 加载 gongyi → build_db --incremental
  └─ 10. 如涉及文档 → 加载 md2docx/md2html → 生成/更新文档
```

### 4.2 代码修改完整流程

```
用户提出需求
  │
  ├─ 1. 加载 gongcheng（当前 step，通用编排）
  ├─ 2. 加载 gongkong → 读取 config.yaml 注入项目配置
  ├─ 3. 判断工作类型 → 加载对应通用子 skill
  ├─ 4. gongyou 协议2（改动前文件影响检查，高风险等用户确认）
  ├─ 4b. 如涉及数据库 → gongshu 协议1（数据风险分级）+ 协议2（备份+确认门禁）
  ├─ 5. 如需设计 → 加载 gongsheji → 写 spec/plan
  ├─ 6. 修改代码 → gongkong 处理部署（用 config.yaml 的 SSH/部署配置）
  ├─ 7. git commit + push（用 config.yaml 的 git 仓库配置）
  ├─ 8. 同步记忆 → 加载 gongyi → build_db --incremental
  ├─ 9. 如涉及文档 → 加载 md2docx → 生成/更新文档
  └─ 10. 如涉及数据操作 → gongshu 协议3（写入审计日志）
```

### 4.3 数据操作完整流程

```
需要执行 SQL / 数据库操作
  │
  ├─ 1. 加载 gongcheng → 加载 gongshu
  ├─ 2. gongshu 协议1：风险分级
  │     ├─ L1 只读 → 直接执行
  │     ├─ L2 单行写 → 记录日志后执行
  │     ├─ L3 批量写 → 进入协议2
  │     └─ L4 不可逆/敏感字段 → 进入协议2（加强）
  │
  ├─ 3. gongshu 协议2：备份 + 确认门禁
  │     ├─ 步骤1：CREATE TABLE backup_xxx AS SELECT ...（备份受影响行）
  │     ├─ 步骤2：生成回滚 SQL → /tmp/rollback_xxx.sql
  │     ├─ 步骤3：用户确认（L3 需 y/yes，L4 需"我确认执行"）
  │     └─ 步骤4：执行原 SQL + 验证影响行数
  │
  ├─ 4. gongshu 协议4：歧义追问（如指令有多种解读）
  │     └─ 必须追问，禁止默认选择破坏性更大的理解
  │
  └─ 5. gongshu 协议3：审计日志
        └─ 写入 /var/log/ai-data-ops.log
```

### 4.4 服务器文件操作规范

**优先级**（部署工具由 `gongkong/config.yaml` 的 `deploy` 字段配置）：
1. `remote.ps1 upload`（或等效部署脚本）— 本地写好完整文件 → 上传覆盖
2. `remote.ps1 run`（或等效）— 本地写脚本 → 服务器执行
3. `ssh <alias> "简单命令"` — 仅用于只读操作（alias 由 config.yaml 提供）
4. **项目配置的远程执行通道** — SSH 都失败时的兜底（由 gongkong 注入，如 WebSocket 代理、CI runner 等）

**禁止**：
- 在远程命令中用 heredoc 写文件
- 在远程命令中拼接含 onclick/引号/括号的 HTML 字符串
- 用 sed -i 做全局字符串替换

### 4.5 多任务并行

```
收到多个独立任务
  │
  ├─ 1. 分析任务间的依赖关系
  ├─ 2. 将无依赖的任务拆分为独立子任务
  ├─ 3. 为每组子任务分配 groupId
  ├─ 4. 通过项目配置的任务派发机制逐一派发（非阻塞，立即返回）
  ├─ 5. 派发完成后，按 groupId 汇总结果
  └─ 6. 合并结果，输出最终结论
```

### 4.6 文档处理流程

```
需要生成/转换文档
  │
  ├─ 1. 加载 gongcheng
  ├─ 2. 按目标格式选择工具
  │     ├─ .docx / Word → md2docx
  │     ├─ .html（含 Mermaid 流程图） → md2html
  │     └─ 原生 .xlsx/.pptx/.docx/.pdf → tools/excel、tools/ppt、tools/docx、tools/pdf
  ├─ 3. 执行转换
  └─ 4. 如文档描述代码变更 → git commit + push → 加载 gongyi
```

### 4.7 界面设计/前端开发流程

```
需要设计或改造页面
  │
  ├─ 1. 加载 gongcheng
  ├─ 2. 加载 gonghua → 执行 Design Read
  ├─ 3. 设置三旋钮 → 选择设计系统 → 输出设计方案
  ├─ 4. 确认后实现代码 → gongkong 处理部署 → git commit + push
  ├─ 5. 同步记忆 → 加载 gongyi → build_db --incremental
  └─ 6. 如 SSH 部署失败 → 降级到项目配置的远程执行通道
```

### 4.8 画图/渲染流程

```
需要画图或渲染图源码
  │
  ├─ 1. 加载 gongcheng
  ├─ 2. 加载 gongtu
  ├─ 3. 编写/读取图源码（.puml/.mmd/.d2）
  ├─ 4. 调用 render.sh 渲染成 SVG
  └─ 5. 在 markdown 里嵌入 SVG（源码和 SVG 都提交 git）
```

### 4.9 工作交接流程

```
AI 完成一个版本/阶段
  │
  ├─ 1. 按 Git 规范 → 确认所有代码已 commit + push
  ├─ 2. 加载 gongyi → build_db --incremental → export_md 生成 PROJECT_SPEC.md
  ├─ 3. gongyou 协议4 → 更新 memory.md 状态
  └─ 4. 总结变更摘要供人类审查
```

---

## 五、交接产物规范

gongcheng 各子 skill 之间必须按本章规范交接，确保下游 skill 能无条件读取、验证、继承上游产出。

### 5.1 通用要求

1. **产物必须落地为文件**：口头交接无效，必须写入约定路径的 markdown/yaml 文件。
2. **文件名必须带版本与时间戳**：`GX-YYYYMMDD-XXX`、`GC-YYYYMMDD-XXX` 等，便于追踪。
3. **每个产物必须包含**：来源、目标读者、核心结论、下一步动作、尚未解决的问题。
4. **下游必须显性标注覆盖情况**：gongchan 接收 gongxu 产出后，必须在设计文档中标注每个 P0 工需的覆盖位置。
5. **缺失时回退上游**：下游发现上游产物不满足本章规范，必须回退到上游 skill 补齐，不得自行猜测。

### 5.2 gongxu → gongchan 交接

| 产物 | 文件名 | 位置 | 必填 | gongchan 使用方式 |
|------|--------|------|------|------------------|
| 任务信号卡 | `00_signal.md` | `docs/gongxu/GX-YYYYMMDD-XXX/` | 推荐 | 理解原始意图 |
| 追问清单 | `01_questions.md` | `docs/gongxu/GX-YYYYMMDD-XXX/` | 完整模式必填 | 核对已澄清与未澄清 |
| 工需标准 v1.0 | `02_standard_v1.md` | `docs/gongxu/GX-YYYYMMDD-XXX/` | **必填** | 作为验收基线 |
| 工需清单 | `03_needs.md` | `docs/gongxu/GX-YYYYMMDD-XXX/` | **必填** | 阶段二/三逐项对照 |
| 自生需求补充 | `04_self_needs.md` | `docs/gongxu/GX-YYYYMMDD-XXX/` | 推荐 | 检查是否遗漏隐性需求 |
| 工需建议书 | `05_proposal.md` | `docs/gongxu/GX-YYYYMMDD-XXX/` | **必填** | 作为整体输入 |

### 5.3 gongchan → gongsheji 交接

| 产物 | 文件名/路径 | 必填 | gongsheji 使用方式 |
|------|-------------|------|-------------------|
| 模块设计文档 | `docs/newdesign/01_系统模块设计.md` | 必填 | 理解模块边界 |
| 架构总览 | `docs/newdesign/00_总览.md` | 必填 | 把握整体结构 |
| 数据结构设计 | `docs/newdesign/03_数据结构设计_*.md` | 必填 | 建表/字段实现 |
| 流程闭环设计 | `docs/newdesign/07_业务流程闭环设计.md` | 必填 | 写业务逻辑 |
| 工需覆盖对照表 | 嵌入在模块设计/闭环设计文档中 | **必填** | 验证 P0 全覆盖 |
| HTML 静态页/设计稿 | `docs/newdesign/html/` 或等价路径 | 推荐 | 前端实现参考 |
| 开发交接清单 | `docs/newdesign/99_交接清单.md` | 必填 | 确认进入开发前状态 |

### 5.4 回退触发条件

下游 skill 在以下情况必须回退上游：

- 找不到 `03_needs.md` 或 `02_standard_v1.md`
- 工需清单中 P0 项为空或无法对应到设计
- 设计文档未包含工需覆盖对照表
- 闭环检查发现的缺口根因是需求遗漏而非设计遗漏

### 5.5 记忆同步要求

所有交接产物完成后，必须触发 gongyi 增量更新：

```bash
python3 build_db.py --incremental <project.root>
```

---

## 六、与 gongkong 的协作契约

gongcheng 是通用编排层，gongkong 是项目配置层。两者通过 `config.yaml` 解耦：

```
gongcheng（通用，开源）
    │
    │  需要项目配置时
    ↓
gongkong（项目专属）
    │
    │  读取同目录 config.yaml
    ↓
返回配置：project.root / git.repositories / ssh / deploy / memory.db_path / high_risk_files（可选：远程执行通道、任务派发机制等扩展字段）
```

**gongkong 必须提供的配置字段**（见 gongkong/SKILL.md 的 schema）：
- `project.name` / `project.root` — 项目标识和根路径
- `git.gitea_url` / `git.repositories[]` — Git 服务地址和仓库列表
- `ssh.alias` / `ssh.host` / `ssh.port` / `ssh.user` / `ssh.key` — SSH 连接信息
- `deploy.remote_root` / `deploy.remote_ps1` — 部署路径和工具
- `memory.db_path` — 知识库 SQLite 路径
- `high_risk_files[]` — 高风险文件清单（gongyou 协议2 使用）
- `db.connections[]` — 数据库连接清单（gongshu 使用）
- `db.sensitive_fields[]` — 项目专属敏感字段（gongshu 使用，追加到默认清单）
- `db.backup_dir` — 数据库备份目录（gongshu 使用）
- `db.audit_log` — 数据操作审计日志路径（gongshu 使用）

**可选扩展字段**（项目按需注入）：
- `remote_execution.url` / `task_dispatch.url` — 远程执行通道、任务派发机制地址（如 WebSocket 代理、CI runner 等）

**换项目时**：复制 gongkong 目录到新项目，只改 config.yaml，gongcheng 不用动。

---

## 七、扩展指南

新增通用子 skill 时：
1. 在本包目录下创建 `<新skill名>/` 子目录
2. 命名遵循"工"字系列（gongxxx），体现工程性质
3. 在本文件的第三章索引表中追加一行
4. 在第一章的工作类型表中追加对应行（如适用）

新增工具时：
1. 在 `tools/` 下创建 `<工具名>/` 子目录
2. 在第三章索引的"工具"部分追加一行

新增项目专属子 skill 时：
1. 在 `<project.root>/.trae/skills/<新skill名>/` 创建目录
2. 在 gongkong/SKILL.md 中登记（如需配置注入）

---

## 八、快速命令（通用模板）

| 用户说 | gongcheng 执行 |
|--------|----------------|
| "修改…代码" | gongkong 注入配置 → gongyou 影响检查 → gongsheji 工作流 → git commit + push → gongyi 更新记忆 |
| "生成一个关于...的报告" | 加载 md2docx → 生成 .md → 转 .docx |
| "把 Markdown 转成 HTML" | 加载 md2html → 生成 .html |
| "设计...功能" | 加载 gongsheji → 写 spec/plan |
| "总结这一轮干了什么" | 加载 gongyi → export_md → 人类审查 |
| "提交所有代码" | gongkong 提供 git.repositories → 遍历 rsync → commit + push |
| "把这个文件传到服务器" | gongkong 提供 deploy 配置 → 用部署工具上传 |
| "SSH 写入不了文件" | 用 deploy.remote_ps1；仍失败则降级到项目配置的远程执行通道 |
| "同时做 XXX 和 YYY" | 拆分任务 → 通过项目配置的任务派发机制并行执行 → 汇总 |
| "设计/美化...页面" | 加载 gonghua → Design Read → 选设计系统 → 实现 |
| "画...架构图" | 加载 gongtu → 写 .puml → render.sh 渲染 SVG |
| "客户给了个方案文档" | 加载 gongwen → 查 gongyi 既有记忆 → 审问 → 方案底稿 → 移交 gongsheji |
| "处理这个 Excel/PPT/Word/PDF" | 按 extensions 选 tools/excel、tools/ppt、tools/docx、tools/pdf → OOXML 感知读写 |
| "生成/优化这个 SVG" | 加载 tools/svg → 检查 viewBox/无障碍/SVGO → 输出 |
| "执行...SQL" / "更新...数据" | gongshu 协议1 风险分级 → 协议2 备份+确认 → 执行 → 协议3 审计 |
| "重置...用户密码" | gongshu 协议4 歧义追问 → L4 全表备份+原值导出 → 二次确认 |
| "禁用/删除...用户" | gongshu 协议4 歧义追问 → L4 备份 → 二次确认 → 审计日志 |

---

## 九、同步 SkillHub 开源注意事项

> 本包开源发布到 SkillHub 时，**必须严格遵守以下规则**，防止账号密码泄露。

### 红线（不可违反）

1. **绝不上传带有账号密码的配置文件**
   - `gongkong/config.yaml` 含真实 SSH 密钥名、服务器 IP、Gitea 账号密码 —— **禁止上传**
   - 发布前必须确认打包目录里只有 `config.yaml.example`，没有 `config.yaml`
   - 验证命令：`find <打包目录> -name "config.yaml" | wc -l` 必须返回 `0`

2. **必须上传空的配置模板**
   - `gongkong/config.yaml.example` 是脱敏模板（所有敏感字段用占位符）—— **必须包含**
   - 用户下载后 `cp config.yaml.example config.yaml` 自行填值
   - 模板里的占位符示例：`your.server.ip` / `YOUR_PASSWORD_HERE` / `your_ssh_key_name`

### 发布前检查清单

每次发布到 SkillHub 前逐项确认：

- [ ] `gongkong/config.yaml`（真实配置）不在打包目录中
- [ ] `gongkong/config.yaml.example`（脱敏模板）在打包目录中
- [ ] `gongkong/.gitignore` 包含 `config.yaml` 排除规则
- [ ] 全目录搜索无真实 IP / 密码 / token / 密钥：
  ```bash
  # 把下面的占位符替换成你自己的真实值后执行，必须全部无输出
  grep -rn "<你的服务器IP>" <打包目录>/       # 例如 101.x.x.x
  grep -rn "<你的真实密码>" <打包目录>/       # 任意真实密码
  grep -rn "<你的SSH密钥名>" <打包目录>/      # ~/.ssh/ 下的密钥名
  grep -rn "<你的API token前缀>" <打包目录>/  # 例如以 xxx_ 开头的 token
  ```
  以上命令必须全部无输出

  > 注：模板里的占位符（`YOUR_PASSWORD_HERE` / `your.server.ip` / `your_ssh_key_name` 等）不应被匹配到，它们是脱敏示例值。
- [ ] SKILL.md frontmatter 的 slug/displayName/version 合法
- [ ] `skillhub publish <path> --dry-run` 通过

### 更新发布流程

后续版本更新发布时：

```bash
# 1. 从源目录同步（排除真实配置）
python3 sync_to_staging.py   # 或手动 cp，确保排除 config.yaml

# 2. 验证无敏感信息
grep -rn "config.yaml" <打包目录>/ | grep -v "config.yaml.example" | grep -v ".gitignore"
# 应无输出

# 3. 更新 SKILL.md 的 version 字段

# 4. dry-run
skillhub publish <打包目录> --host "https://api.skillhub.cn" --dry-run

# 5. 正式发布
skillhub publish <打包目录> --host "https://api.skillhub.cn" --changelog "本次变更说明"
```

### 泄露应急

如果不慎上传了含密码的 config.yaml：
1. 立即在 SkillHub 个人中心删除该版本
2. 修改所有泄露的密码（Gitea 密码、SSH 密钥、API token）
3. 重新发布干净版本
4. 在 changelog 中标注"修复配置泄露"

---

## License

MIT。gongtu 子目录的 LICENSE 是 Kroki 依赖的协议声明。

## 版本

v1.3.2 — 2026-07-29 移除已废弃的 git-management skill 引用，统一改为 git commit + push
v1.3.1 — 2026-07-29 统一子 skill 与根包版本号为 1.3.1，同步 GitHub 与 SkillHub 最新内容
v1.3.0 — 2026-07-28 明确 gongxu（工需）与 gongchan（工产）分工，新增第五章交接产物规范；gongxu 产出作为 gongchan 强制输入；README 增加最小示例
v1.2.3 — 2026-07-28 将 md2html（Markdown 转 HTML / ASCII 流程图自动转 Mermaid）纳入 gongcheng 工具层；重整第三章子 skill 索引，明确区分工字系列子 skill 与 tools/ 工具层（文档转换 / Office / 图形）。
v1.1.0 — 2026-07-07 新增 gongshu（工数）数据安全守护 skill，补齐数据层风控缺口；定义 L1-L4 四级风险分级、强制备份、确认门禁、歧义追问协议；源于 2026-07-07 生产事故教训
v1.0.1 — 2026-07-01 移除 aibuddys 项目专属依赖，改为通用远程执行/任务派发扩展点
v1.0.0 — 2026-07-01 首个开源版本
