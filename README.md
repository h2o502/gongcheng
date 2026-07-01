# 工字系列 Skill 包 — AI 项目工程能力开源版

一套面向 AI 协同编程的工程项目能力包，按"工程"语义拆分为 8 个工字 skill + 1 个配置层 + 6 个工具，
通过 `gongcheng` 统一编排。配置与逻辑分离：通用逻辑在本包，项目专属配置由 `gongkong` 注入。

## 设计哲学

| 问题 | 解法 |
|------|------|
| AI 改代码修 B 破 A | gongyou 强制改动前影响检查 + 踩坑标注 |
| AI 不读历史直接动手 | gongyi 提供 SQLite 知识库，500 token 内定位上下文 |
| AI 需求没问清就写代码 | gongwen 审问 + 方案底稿，把模糊需求逼问成结构化方案 |
| AI 写出来的界面千篇一律 | gonghua 反 AI slop，三旋钮控制设计差异度 |
| AI 画的图全是文本源码 | gongtu 把 PlantUML/Mermaid/D2 渲染成 SVG |
| AI 改完代码不提交 | gongcheng 强制 Git 纪律，session 结束前必 commit+push |
| AI 跨 session 信息丢失 | gongyi 三模式（开发/审查/交接）+ 导出 PROJECT_SPEC.md |
| AI 做设计没有规范流程 | gongsheji spec→plan→execute（TDD）工作流 |

## 包含的 Skills

### 工程层（7 个工字 skill + 1 个配置层）

| Skill | 中文名 | 职责 |
|-------|--------|------|
| **gongcheng** | 工程师 | 通用编排层，规则检查 + 工作流调度 + 子 skill 索引。**必须最先加载** |
| **gongsheji** | 工设计 | 工程设计工作流：spec → plan → 小步执行（TDD）→ 评审 |
| **gongyi** | 工艺 | 项目记忆中继站：SQLite 知识库 + 开发/审查/交接三模式 |
| **gonghua** | 工画 | 前端实现，反 AI slop，三旋钮（DESIGN_VARIANCE/MOTION_INTENSITY/VISUAL_DENSITY）|
| **gongtu** | 工图 | 图渲染，PlantUML/Mermaid/D2/Graphviz 等 27 种 → SVG/PNG/PDF |
| **gongyou** | 工优 | 连续性任务守护：改动前影响检查 + 渐进式记忆加载 + 踩坑标注 |
| **gongwen** | 工问 | 方案审问与方案底稿：把模糊需求逼问成结构化方案，含商业三问 |
| **gongkong** | 工控 | 项目配置注入层。`SKILL.md` 管逻辑（通用），`config.yaml` 管配置（专属）|

### 工具层（tools/ 子目录，可扩展）

| 工具 | 职责 |
|------|------|
| **tools/md2docx** | Markdown ↔ Word 双向转换（合并单元格、Mermaid、代码高亮、中文排版）|
| **tools/svg** | SVG 图形创建与优化（viewBox、无障碍、SVGO、currentColor 主题化）|
| **tools/pdf** | PDF 文本/表格抽取、生成、合并/拆分、表单填写 |
| **tools/excel** | Excel 工作簿读写（公式、日期、格式、合并单元格、模板保真）|
| **tools/ppt** | PowerPoint 演示文稿读写（布局、占位符、备注、图表、模板保真）|
| **tools/docx** | Word 文档深度读写（样式、编号、修订追踪、表格、OOXML 感知编辑）|

> 工程层管"流程和规则"，工具层管"具体转换/渲染"。工具独立于工程层，增减不影响编排。
> md2docx 专做 Markdown↔Word 转换；docx 处理原生 .docx 的 OOXML 级深度编辑，两者互补。

## 目录结构

```
gongcheng/                ← 根 skill（SkillHub 发布入口）
├── SKILL.md              ← 根 skill 文件（编排层 + 工作类型表 + 子 skill 索引）
├── README.md
├── gongsheji/            ← 工设计
├── gongyi/               ← 工艺（知识库）
├── gonghua/              ← 工画（前端）
├── gongtu/               ← 工图（图渲染）
├── gongyou/              ← 工优（守护）
├── gongwen/              ← 工问（审问）
├── gongkong/             ← 工控（项目配置，含 config.yaml.example）
└── tools/
    ├── md2docx/          ← Markdown ↔ Word 转换
    ├── svg/              ← SVG 创建与优化
    ├── pdf/              ← PDF 处理
    ├── excel/            ← Excel 工作簿读写
    ├── ppt/              ← PowerPoint 演示文稿读写
    └── docx/             ← Word 文档深度读写
```

## 快速上手

### 1. 安装

整个 `gongcheng/` 作为一个整体复制到 AI agent 的 skill 加载路径：

```bash
# 方式 A：整包安装（推荐，保持子文件夹结构）
cp -r gongcheng ~/.trae-cn/skills/   # 或你的 agent 对应的 skills 目录

# 方式 B：只装工程层，不装工具
cp -r gongcheng/gongsheji gongcheng/gongyi gongcheng/gonghua \
      gongcheng/gongtu gongcheng/gongyou gongcheng/gongwen \
      ~/.trae-cn/skills/
# 注意：gongcheng 本身是根 skill，整包安装时它的 SKILL.md 就是编排入口

# gongkong 放到项目目录下（不放通用 skills 目录）
mkdir -p <你的项目>/.trae/skills/
cp -r gongcheng/gongkong <你的项目>/.trae/skills/
```

### 2. 配置 gongkong

```bash
cd <你的项目>/.trae/skills/gongkong/
cp config.yaml.example config.yaml
# 编辑 config.yaml，填入你项目的真实值：
#   - project.name / project.root
#   - git.gitea_url / git.repositories
#   - ssh.alias / ssh.host / ssh.key
#   - deploy.remote_root
#   - memory.db_path
#   - high_risk_files
#   - git_admin.username / git_admin.password
```

**重要**：`config.yaml` 含账号密码，**不要提交到公共 git 仓库**。
gongkong 目录下已有 `.gitignore` 排除它。

### 3. 设置用户规则

在你的 AI agent 用户规则里加一条：

```
必须使用gongcheng
```

这会强制 agent 每次执行项目任务时先加载 gongcheng，按工作类型表调度对应子 skill。

### 4. gongyi 初始化（可选，但推荐）

如果你的项目已有代码，初始化知识库：

```bash
cd <你的项目>/.ai/
python3 build_db.py <项目路径>
# 自动生成 .ai/project.ai.db + .ai/CONTEXT.md
```

### 5. gongtu 依赖（如需画图）

gongtu 依赖 Kroki 渲染服务。两种方式：

- **公网 API（默认）**：无需安装，直接用 `https://kroki.io`
- **自部署**：`bash install.sh` 用 Docker 启动本地 Kroki

## 工作流示例

### 场景 A：客户给了一份方案文档想让你实现

```
1. gongcheng 识别 → 需求审问场景 → 加载 gongwen
2. gongwen Pre-step：查 gongyi 既有记忆预填底稿
3. gongwen 抽取文档 → 商业判定 → 追问（含商业三问）
4. gongwen 压力测试 → 定稿 → 输出 draft.yaml + PROPOSAL.md
5. gongcheng 调度 → 加载 gongsheji → 读 draft.yaml → 写 spec/plan
6. gongsheji 执行 → gongyou 影响检查 → 改代码
7. git-management 提交 → gongyi 增量更新知识库
8. gongtu 渲染架构图附入文档
```

### 场景 B：改一个已有功能的 bug

```
1. gongcheng 识别 → 代码修改场景 → 加载 gongyou + gongsheji
2. gongyou 协议2：改动前影响检查（高风险文件等用户确认）
3. gongyi 查询：拉取相关模块/约束/ADR
4. gongsheji：写 spec → 写 plan → TDD 执行
5. git-management 提交 → gongyi 增量更新
```

## 架构原则

1. **配置与逻辑分离**：通用逻辑在 skill 的 SKILL.md，项目配置在 gongkong/config.yaml
2. **换项目只改 config.yaml**：复制 gongkong 目录到新项目，改 config.yaml，其他 skill 不动
3. **每个 skill 单一职责**：gongwen 管需求，gongsheji 管设计，gongyi 管记忆，gongyou 管守护
4. **gongcheng 是唯一入口**：所有任务先过 gongcheng，按工作类型表调度

## 各 Skill 详细文档

详见各 skill 目录下的 `SKILL.md`。

## License

本包采用 MIT 协议。gongtu 子目录下的 LICENSE 是 Kroki 依赖的协议声明。

## 版本

v1.0.1 — 2026-07-01 移除 aibuddys 项目专属依赖，改为通用远程执行/任务派发扩展点
v1.0 — 2026-07-01 首个开源版本
