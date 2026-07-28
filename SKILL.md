---
name: "gongcheng"
slug: "gongcheng"
displayName: "工成"
description: "工成（gongcheng）— Vibecoding 全生命周期 AI 工程 Skill。首个必须加载的通用工程编排 Skill，贯穿需求澄清、架构设计、代码实现、文档沉淀与持续复盘。以 PlantUML 记录项目架构，以规则驱动工作流自我迭代。"
version: "1.3.0"
---

# 工成 (gongcheng) — Vibecoding 全生命周期 AI 工程 Skill

**首个必须加载的通用工程编排 Skill** 。沉淀自多个 AI 项目落地实战经验，贯穿需求澄清、架构设计、代码实现、文档沉淀与持续复盘。 **不含项目专属配置** ：Gitea 地址、SSH 别名、部署路径等全部由 `gongkong/config.yaml` 注入。 以 PlantUML 记录项目架构，以规则驱动工作流自我迭代。开源版仅含模板，请勿提交账号密码。

本包是 gongcheng 及其子 skill 的开源发布形态。gongcheng 既是包名也是核心编排 skill， 其余工字系列子 skill（gongxu/gongsheji/gongyi/gonghua/gongtu/gongyou/gongwen/gongshu/gongkong）和工具层（tools/ 下含 md2docx/md2html/svg/pdf/excel/ppt/docx）作为子目录包含在本包中。

## 一、强制规则（不可违反）

任何涉及以下类型的工作，**必须先加载对应子 skill** ：

| # | 工作类型 | 必须加载的通用 skill | 项目配置（由 gongkong/config.yaml 注入） | 违反后果 |
|---|---|---|---|---|
| 1 | **修改代码/提交代码/部署** | gongsheji + gongyou + git-management | `git.repositories`（项目仓库列表） | 代码无法追溯，禁止操作 |
| 2 | **文档创建/转换（.md ↔ .docx / .html）** | md2docx + md2html | - | 格式不规范，禁止操作 |
| 3 | **项目设计/架构决策/方案规划** | gongsheji | - | 缺少规范流程，禁止操作 |
| 4 | **改动代码/更新项目状态** | gongyi | `memory.db_path`（知识库路径） | 知识库不同步，禁止操作 |
| 5 | **界面设计/前端页面开发/视觉改造** | gonghua | - | 防止 AI 生成千篇一律的通用界面，确保设计质量 |
| 6 | **服务器文件上传/远程脚本执行/SSH 部署** | gongkong（部署层） | `ssh` + `deploy.remote_root` + `deploy.remote_ps1` | 禁止在远程命令中拼 heredoc 或复杂引号字符串 |
| 7 | **画图/架构图/类图/流程图渲染** | gongtu | - | 文本图源码无法可视化 |
| 8 | **改动前影响检查/踩坑标注** | gongyou | `high_risk_files`（高风险文件清单） | 修 B 破 A，破坏未知依赖 |
| 9 | **方案审问/需求澄清/商业三问** | gongwen | - | 需求未澄清就写代码，返工率极高 |
| 10 | **工程需求澄清/隐性需求挖掘/需求对齐** | gongxu | - | 人类与 AI 理解偏差，遗漏闭环与异常分支 |
| 11 | **Office 文档读写（.xlsx/.pptx/.docx/.pdf）** | tools/excel + tools/ppt + tools/docx + tools/pdf | - | 直接改 OOXML 易破坏样式/公式/布局 |
| 12 | **SVG 图形创建/优化** | tools/svg | - | 缺 viewBox/无障碍属性，可伸缩性与可访问性差 |
| 13 | **数据库读写/批量数据操作** | gongshu | `db.connections`（数据库连接清单）+ `db.sensitive_fields`（敏感字段） | 数据不可恢复，禁止操作 |

**额外红线（代码修改时必须遵守）** ：

- **禁止使用全局字符串替换** （如 `sed -i s/old/new/ file`、Python `content.replace(old,new)`、PowerShell `-replace` 等）。搜索到的匹配项可能分布在不相关的函数/模块中，修改一处却破坏多处。

- **正确做法** ：先定位到具体行/函数，用精确的行级或范围级方式修改（`sed -i 123s/old/new/` 按行号替换、在本地用工具读取-精确编辑-回写、或直接用 file edit 操作）。每次修改后必须编译/测试确认无误。

**额外红线（数据操作时必须遵守）** ：

- **禁止无备份执行 L3/L4 数据操作** （批量 UPDATE/DELETE、DROP/TRUNCATE、覆盖敏感字段）。必须先 `CREATE TABLE backup_<table>_<date> AS SELECT ...` 备份受影响行，再执行。

- **禁止覆盖敏感字段前不导出原值** （password_hash/token/secret/balance 等）。必须先 `CREATE TABLE audit_<table>_<date> AS SELECT id, <敏感字段>, NOW() FROM ...` 记录原值。

- **禁止无 WHERE 的 UPDATE/DELETE** 。如必须全表操作，按 L4 处理，需用户二次确认。

- **禁止默认选择破坏性更大的指令理解** 。遇到歧义必须追问（详见 gongshu 协议4）。

- **正确做法** ：先 EXPLAIN/COUNT 预估影响 → 备份 → 生成回滚 SQL → 用户确认 → 执行 → 验证 → 审计日志。

**检查流程** （每次开始工作前执行）：

1. **加载 gongkong** ：读取 `gongkong/config.yaml`，注入项目专属配置（git 仓库/SSH/部署路径/memory 路径/高风险文件清单）

2. **识别工作类型** （代码/文档/设计/部署/画图/需求澄清/其他）

3. **逐一对照上表** ，确认对应通用 skill 已加载，项目配置已注入

4. **评估是否能直接 SSH** ：如遇到写入失败、复杂嵌套命令、网络超时等问题 → 降级使用项目配置的远程执行通道

5. **评估是否有多个互不干涉的任务** ：设计任务拆分 → 通过项目配置的任务派发机制并行执行

6. **如有遗漏，先加载 skill 再继续**

7. **工作完成后** ，确认所有变更已 commit + push + 同步知识库

## 二、Git 代码管理规范（通用纪律）

项目专属信息（Gitea 地址、仓库列表、SSH 别名）由 `gongkong/config.yaml` 提供。 本节只包含通用 Git 纪律，适用于任何项目。

### 2.1 核心原则（不可违反）

| # | 原则 | 说明 |
|---|---|---|
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

**安全回滚（推荐，保留历史记录）** ：

```
cd <repo.local_path>
git revert HEAD
git push
```
**强制回滚（会丢失中间提交，必须用户明确确认后执行）** ：

```
cd <repo.local_path>
git reset --hard <目标版本号>
git push -f
```
### 2.5 红线规则

- 不创建 .bak 文件：任何时候都禁止创建 
*.bak *.bak.* 文件。Git 历史就是最好的备份

- 不提交大文件：.db .sqlite node_modules/ uploads/ \*.log 禁止提交

- 不强制推送：git push -f 需要用户明确说"强制推送"才能执行

- 不遗留未提交修改：session 结束前必须检查并提交所有修改

- 不直接改 Git 镜像目录下的文件：应该改源码目录，再 rsync 同步

- 敏感信息处理：自建 Gitea 时密码、token 不用脱敏；公共仓库须脱敏

### 2.6 前端资源版本管理

当修改前端静态资源（如 `chat.css`、`chat.js`）时，**必须同步更新所有引用这些资源的 HTML 文件中的版本号** 。

HTML 通过 `?v=xxx` 查询参数引用资源。只修改 CSS/JS 但不更新版本号，浏览器会使用缓存的旧文件。

**正确流程** ：

1. 修改 CSS/JS 文件内容

2. 更新文件内部的版本注释（如 `v3.1` → `v4.0`）

3. 同步更新所有 HTML 文件中的引用版本号（`?v=3.1` → `?v=4.0`）

版本号命名：语义化版本号（v1.0, v1.1, v2.0），小改小版本，大改大版本。

### 2.7 自动快照（可选）

项目可配置每天凌晨自动遍历所有仓库，有修改则自动 commit + push。 commit message: `auto-snapshot: [日期] 自动备份`

## 三、子 Skill 索引

本包目录结构：gongcheng 本身是根 skill，其余工字系列 skill 是子目录，工具类在 `tools/` 下。

### 3.1 工字系列子 skill

#### gongxu（工需）

- **位置** ：`gongxu/`

- **功能** ：工程需求自驱引擎。让人类和 AI 在协作过程中对出"需要做什么"，建立自驱标准并持续反刍

- **产出** ：《任务信号卡》《追问清单》《工需标准》《工需清单》《工需建议书》《反刍记录》

- **触发场景** ：任何工程任务启动前、发现理解偏差时、交付前验收、用户说"还缺什么""工需一下"

- **与 gongwen 区别** ：gongwen 问"这事该不该做"，gongxu 问"这事要做成什么样"

- **与 gongchan 区别** ：gongxu 决定"做什么和做到什么程度"，gongchan 决定"长什么样和怎么做"

#### gongsheji（工设计）

- **位置** ：`gongsheji/`

- **功能** ：严格工程设计工作流。先写 spec → 写 plan → 小步执行（优先 TDD）→ 评审完成

- **触发场景** ：新功能设计、架构决策、方案规划、重大重构

#### gongyi（工艺）

- **位置** ：`gongyi/`

- **功能** ：AI 协同编程的项目记忆中继站。增量更新 SQLite 知识库，支持开发/审查/交接三种模式

- **脚本** ：`build_db.py`（构建库）、`query_db.py`（查询）、`export_md.py`（导出文档）

- **知识库路径** ：由 `gongkong/config.yaml` 的 `memory.db_path` 提供

- **触发场景** ：修改代码后更新记忆、查询项目上下文、版本交接

#### gonghua（工画）

- **位置** ：`gonghua/`

- **功能** ：防止 AI 生成千篇一律的通用界面。读取需求后推断设计方向，输出有辨识度的前端页面

- **核心机制** ：先做 "Design Read" → 设置三个旋钮（DESIGN_VARIANCE / MOTION_INTENSITY / VISUAL_DENSITY）→ 选择设计系统或原生 CSS

- **触发场景** ：新建前端页面、界面视觉改造、组件 UI 设计

#### gongtu（工图）

- **位置** ：`gongtu/`

- **功能** ：把 PlantUML/Mermaid/D2/Graphviz 等 27 种图源码渲染成 SVG/PNG/PDF 图片

- **依赖** ：Kroki（MIT 协议），默认公网 API，可自部署

- **触发场景** ：画架构图/类图/时序图/流程图、转 SVG、markdown 图源码可视化

#### gongyou（工优）

- **位置** ：`gongyou/`

- **功能** ：连续性任务守护。强制改动前影响检查、渐进式记忆加载、踩坑标注

- **4 个协议** ：会话启动 / 改动前检查 / 踩坑标注 / 状态更新

- **高风险清单** ：由 `gongkong/config.yaml` 的 `high_risk_files` 提供

- **触发场景** ：会话启动时、修改任何文件前、发生修 B 破 A 时、会话结束

#### gongshu（工数）

- **位置** ：`gongshu/`

- **功能** ：数据安全守护。强制风险分级、备份、确认门禁、审计日志

- **4 个协议** ：风险分级 / 备份+确认门禁 / 审计日志 / 歧义追问

- **4 级风险** ：L1 只读 / L2 单行写 / L3 批量写 / L4 不可逆

- **敏感字段清单** ：password_hash/token/secret/balance 等，覆盖时自动升级为 L4

- **高风险 SQL 黑名单** ：10 类禁止直接执行的 SQL 模式

- **触发场景** ：任何数据库读写前、批量数据操作、覆盖敏感字段、遇到歧义指令

- **与 gongyou 互补** ：gongyou 守文件，gongshu 守数据

#### gongwen（工问）

- **位置** ：`gongwen/`

- **功能** ：方案审问与方案底稿。把客户文档/口述想法通过追问、压力测试、矛盾检测逼问成结构化方案底稿

- **产出** ：`draft.yaml` + `PROPOSAL.md` + `PENDING.md`，定稿后移交 gongsheji

- **商业三问** ：商业项目必填"卖什么/给谁/为什么买你的"，含反模式检测

- **触发场景** ：客户给方案文档要实现、想法需要追问清楚、写 spec 前先审问需求

#### gongkong（工控）

- **位置** ：`gongkong/`

- **功能** ：项目配置注入层。读取同目录 `config.yaml`，向 gongcheng 提供项目专属配置

- **配置文件** ：`config.yaml`（真实配置，含密码，**不上传** ）+ `config.yaml.example`（脱敏模板，上传）

- **触发场景** ：gongcheng 启动时自动加载

### 3.2 工具层

> 工具层只负责"具体转换/渲染"，不参与工程流程调度。工程层 skill 按工作类型按需调用。

#### 3.2.1 文档转换工具

##### md2docx（工具）

- **位置** ：`tools/md2docx/`

- **功能** ：Markdown 与 Word 双向转换，支持合并单元格、Mermaid 图表渲染、代码高亮、中文排版优化

- **调用方式** ：`python md2docx.py input.md output.docx` 或反向

- **触发场景** ：创建/编辑项目文档（.md/.docx）、导出报告

- **注意** ：属于 tools/ 工具层，不是工程 skill；不改名（有硬编码路径依赖）

##### md2html（工具）

- **位置** ：`tools/md2html/`

- **功能** ：Markdown 转 HTML，自动将 ASCII 流程图转换为 Mermaid 语法，浏览器端渲染

- **调用方式** ：`python md2html.py input.md output.md` 或 `python md2html.py --html input.md output.html`

- **触发场景** ：把设计文档/会议纪要转成可在线浏览的 HTML、将文本流程图转为可视化图表

- **注意** ：`md2docx` 的姊妹工具；范围最小化（A最小），目前只处理 ASCII → Mermaid；复杂图请继续用 `gongtu` 或 PlantUML

#### 3.2.2 Office 文档工具

##### excel（工具）

- **位置** ：`tools/excel/`

- **功能** ：Microsoft Excel 工作簿读写。公式、日期、类型、格式、合并单元格、模板保真（openpyxl/pandas）

- **触发场景** ：处理 `.xlsx/.xlsm/.xls/.csv`、需保留公式/格式/工作簿结构时

##### ppt（工具）

- **位置** ：`tools/ppt/`

- **功能** ：Microsoft PowerPoint 演示文稿读写。布局、模板、占位符、备注、图表、视觉 QA（python-pptx）

- **触发场景** ：处理 `.pptx`、需保留布局/占位符/模板保真时

##### docx（工具）

- **位置** ：`tools/docx/`

- **功能** ：Microsoft Word 文档读写。样式、编号、修订追踪、表格、节、兼容性检查（OOXML 感知编辑）

- **触发场景** ：处理 `.docx`、含修订追踪/域/表格/模板、需往返编辑不漂移时

- **与 md2docx 区别** ：md2docx 专做 Markdown↔Word 转换；docx 处理原生 .docx 的深度编辑（OOXML 级）

##### pdf（工具）

- **位置** ：`tools/pdf/`

- **功能** ：PDF 处理工具集。文本/表格抽取、生成新 PDF、合并/拆分、表单填写（pypdf 等）

- **触发场景** ：抽取 PDF 内容、合并/拆分文档、填表单、批量处理 PDF

#### 3.2.3 图形工具

##### svg（工具）

- **位置** ：`tools/svg/`

- **功能** ：创建和优化 SVG 图形，覆盖 viewBox 缩放、无障碍（role="img"+title）、SVGO 优化、内联 vs `<img>` 嵌入、currentColor 主题化

- **辅助文件** ：`viewbox.md` / `accessibility.md` / `optimization.md` / `embedding.md` / `styling.md`

- **触发场景** ：手写 SVG 图标/图形、优化现有 SVG、确保可访问性与可伸缩性

## 四、工作流规范（通用骨架）

### 4.1 代码修改完整流程

```
用户提出需求
 │
 ├─ 1. 加载 gongcheng（当前 step，通用编排）
 ├─ 2. 加载 gongkong → 读取 config.yaml 注入项目配置
 ├─ 3. 判断工作类型 → 加载对应通用子 skill
 ├─ 4. 如需商业/方案审问 → 加载 gongwen → 输出方案底稿
 ├─ 5. 加载 gongxu → 对出工程需求 → 输出工需建议书 + 工需标准
 ├─ 6. gongyou 协议2（改动前文件影响检查，高风险等用户确认）
 ├─ 6b. 如涉及数据库 → gongshu 协议1（数据风险分级）+ 协议2（备份+确认门禁）
 ├─ 7. 如需设计 → 加载 gongsheji → 写 spec/plan
 ├─ 8. 修改代码 → gongkong 处理部署（用 config.yaml 的 SSH/部署配置）
 ├─ 9. git-management 提交（用 config.yaml 的 git 仓库配置）
 ├─ 10. 同步记忆 → 加载 gongyi → build_db --incremental
 ├─ 11. 如涉及文档 → 加载 md2docx → 生成/更新文档
 └─ 12. 如涉及数据操作 → gongshu 协议3（写入审计日志）
```

### 4.1b 工程需求澄清流程

任何工程任务开始前，必须先经过 gongxu 把需求对清楚：

```
用户提出需求
 │
 ├─ 1. 接收任务信号 → 输出《任务信号卡》
 ├─ 2. 第一轮追问 → 输出《追问清单》
 ├─ 3. 建立初版标准 → 输出《工需标准 v0.1》
 ├─ 4. 用标准去对 → 输出《标准校准记录》
 ├─ 5. 沉淀工需清单 → 输出《工需清单》
 ├─ 6. 自生需求检查 → 输出《自生需求补充》
 ├─ 7. 输出《工需建议书》
 │      └─ 本产物移交 gongchan 或 gongsheji
 └─ 8. 交付后反刍 → 输出《反刍记录》→ 同步 gongyi
```

**关键原则** ：

- gongxu 不替代 gongwen。gongwen 解决"该不该做"，gongxu 解决"要做成什么样"。
- gongxu 不替代 gongchan。gongxu 产出需求边界与验收标准，gongchan 产出产品形态与设计。
- gongxu 的标准是活的，每轮交付后必须反刍升级，并回流到 gongyi。

### 4.1c 数据操作完整流程

```
需要执行 SQL / 数据库操作
 │
 ├─ 1. 加载 gongcheng → 加载 gongshu
 ├─ 2. gongshu 协议1：风险分级
 │ ├─ L1 只读 → 直接执行
 │ ├─ L2 单行写 → 记录日志后执行
 │ ├─ L3 批量写 → 进入协议2
 │ └─ L4 不可逆/敏感字段 → 进入协议2（加强）
 │
 ├─ 3. gongshu 协议2：备份 + 确认门禁
 │ ├─ 步骤1：CREATE TABLE backup_xxx AS SELECT ...（备份受影响行）
 │ ├─ 步骤2：生成回滚 SQL → /tmp/rollback_xxx.sql
 │ ├─ 步骤3：用户确认（L3 需 y/yes，L4 需"我确认执行"）
 │ └─ 步骤4：执行原 SQL + 验证影响行数
 │
 ├─ 4. gongshu 协议4：歧义追问（如指令有多种解读）
 │ └─ 必须追问，禁止默认选择破坏性更大的理解
 │
 └─ 5. gongshu 协议3：审计日志
 └─ 写入 /var/log/ai-data-ops.log
```
### 4.2 服务器文件操作规范

**优先级** （部署工具由 `gongkong/config.yaml` 的 `deploy` 字段配置）：

1. `remote.ps1 upload`（或等效部署脚本）— 本地写好完整文件 → 上传覆盖

2. `remote.ps1 run`（或等效）— 本地写脚本 → 服务器执行

3. `ssh <alias> "简单命令"` — 仅用于只读操作（alias 由 config.yaml 提供）

4. **项目配置的远程执行通道**  — SSH 都失败时的兜底（由 gongkong 注入，如 WebSocket 代理、CI runner 等）

**禁止** ：

- 在远程命令中用 heredoc 写文件

- 在远程命令中拼接含 onclick/引号/括号的 HTML 字符串

- 用 sed -i 做全局字符串替换

### 4.3 多任务并行

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
### 4.4 文档处理流程

```
需要生成/转换文档
 │
 ├─ 1. 加载 gongcheng
 ├─ 2. 按目标格式选择工具
 │     ├─ .docx / Word → md2docx
 │     ├─ .html（含 Mermaid 流程图） → md2html
 │     └─ 原生 .xlsx/.pptx/.docx/.pdf → tools/excel、tools/ppt、tools/docx、tools/pdf
 ├─ 3. 执行转换
 └─ 4. 如文档描述代码变更 → 加载 git-management + gongyi
```
### 4.5 界面设计/前端开发流程

```
需要设计或改造页面
 │
 ├─ 1. 加载 gongcheng
 ├─ 2. 加载 gonghua → 执行 Design Read
 ├─ 3. 设置三旋钮 → 选择设计系统 → 输出设计方案
 ├─ 4. 确认后实现代码 → gongkong 处理部署 → git-management 提交
 ├─ 5. 同步记忆 → 加载 gongyi → build_db --incremental
 └─ 6. 如 SSH 部署失败 → 降级到项目配置的远程执行通道
```
### 4.6 画图/渲染流程

```
需要画图或渲染图源码
 │
 ├─ 1. 加载 gongcheng
 ├─ 2. 加载 gongtu
 ├─ 3. 编写/读取图源码（.puml/.mmd/.d2）
 ├─ 4. 调用 render.sh 渲染成 SVG
 └─ 5. 在 markdown 里嵌入 SVG（源码和 SVG 都提交 git）
```
### 4.7 工作交接流程

```
AI 完成一个版本/阶段
 │
 ├─ 1. 按 Git 规范 → 确认所有代码已 commit + push
 ├─ 2. 加载 gongyi → build_db --incremental → export_md 生成 PROJECT_SPEC.md
 ├─ 3. gongyou 协议4 → 更新 memory.md 状态
 └─ 4. 总结变更摘要供人类审查
```
## 五、与 gongkong 的协作契约

gongcheng 是通用编排层，gongkong 是项目配置层。两者通过 `config.yaml` 解耦：

```
gongcheng（通用，开源）
 │
 │ 需要项目配置时
 ↓
gongkong（项目专属）
 │
 │ 读取同目录 config.yaml
 ↓
返回配置：project.root / git.repositories / ssh / deploy / memory.db_path / high_risk_files（可选：远程执行通道、任务派发机制等扩展字段）
```
**gongkong 必须提供的配置字段** （见 gongkong/SKILL.md 的 schema）：

- `project.name` / `project.root` — 项目标识和根路径

- `git.gitea_url` / `git.repositories[]` — Git 服务地址和仓库列表

- `ssh` — SSH 别名、用户名、端口等

- `deploy.remote_root` / `deploy.remote_ps1` — 远程部署根目录与部署脚本

- `memory.db_path` — gongyi SQLite 知识库路径

- `high_risk_files`（可选）— gongyou 改动前检查清单

- `remote_exec`（可选）— SSH 失败时的远程执行通道

- `task_dispatcher`（可选）— 多任务派发机制配置

## 六、版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0.0 | - | 初始版本 |
| v1.1.0 | 3周前 | 完善子 skill 索引与工作流 |
| v1.2.0 | 2026-07-28 | 新增 gongxu（工需）作为前置步骤，嵌入强制规则、子 skill 索引与代码修改流程 |
| v1.3.0 | 2026-07-28 | 将 md2html 纳入工具层；重整第三章子 skill 索引，明确区分工字系列子 skill 与 tools/ 工具层（文档转换 / Office / 图形）|
