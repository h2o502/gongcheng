---
name: gongwen
description: |
  工问 (gongwen) — 方案审问与方案底稿。

  它解决的核心问题：客户带着"半成品方案"（文档或口述想法）来找 AI，
  AI 不应该直接动手实现，而应该先把方案"问清楚"——
  通过追问、压力测试、矛盾检测，把模糊的需求逼问成精确的方案底稿，
  再交给 gongsheji 进入 spec→plan→execute 流程。

  核心数据结构：**方案底稿 (Proposal Draft)** —— 一个结构化的中间载体，
  记录目标/干系人/实体/决策/约束/假设/待澄清问题/场景/矛盾点/商业维度。
  三个上游收敛到同一个底稿：gongyi 既有记忆（Pre-step）+ agent 层文档识别 + 客户口述。
  商业项目必填"卖什么/给谁/为什么买你的"三问，附反模式检测（卖什么/给谁/为什么/凭什么不被抄）。

  与 grill-with-docs 的关键区别：
  - grill 用 CONTEXT.md（术语表）+ ADR（决策）两个分离载体
  - gongwen 用统一的"方案底稿"作为单一载体
  - grill 只走"已有文档"单路径
  - gongwen 明确双路径（文档/想法）且都收敛到底稿
  - gongwen 不处理文档识别（PDF/Word 解析是 agent 层职责）

  触发场景：
  "客户给了一份方案文档想让我实现"、"我有个想法你帮我问问清楚"、
  "需求模糊需要追问"、"方案有矛盾需要压力测试"、
  "在写 spec 之前先把需求审问清楚"
---

# 工问 (gongwen) — 方案审问与方案底稿

> **定位**：在"客户原始材料"和"gongsheji 工程设计"之间，加一道**审问工序**。
> gongsheji 假设需求已经清楚，gongwen 的工作是**让需求变清楚**。

---

## 一、为什么需要 gongwen（与其他 skill 的边界）

```
客户原始材料（文档/想法）
        │
        ↓
   ┌─────────┐
   │ gongwen │  ← 审问、追问、压力测试、矛盾检测
   │ 工问    │     产出：方案底稿（结构化）
   └─────────┘
        │
        ↓ 方案底稿定稿
   ┌──────────┐
   │ gongsheji│  ← spec → plan → execute（TDD）
   │ 工设计   │     假设需求已清楚，专注工程设计
   └──────────┘
        │
        ↓ 代码完成
   ┌────────┐
   │ gongyi │  ← 沉淀到 SQLite 知识库
   │ 工艺   │     记录代码结构/符号/ADR/约束
   └────────┘
```

**与 gongyi 的边界**：
- gongwen 底稿记录的是**方案层**信息（目标/干系人/场景/决策）
- gongyi 知识库记录的是**代码层**信息（模块/符号/API/表结构）
- gongwen 的 decisions 在方案定稿后**导入** gongyi 的 decisions 表（不重复维护）

**与 gongsheji 的边界**：
- gongwen 不写 spec.md / plan.md，只产出"方案底稿"
- gongsheji 不做追问，假设输入的方案底稿已经够清楚
- 移交点：gongwen 判定"方案底稿已收敛"→ 交给 gongsheji

**与 agent 层的边界**（重要）：
- 文档识别（PDF/Word/图片解析）**不是 gongwen 的职责**
- agent 层负责把客户的 .docx/.pdf/截图变成文本/结构化片段
- gongwen 只接收"已经识别成文本的材料"，从中抽取并构建底稿
- 这意味着 gongwen 可以独立于识别引擎工作，识别能力升级不影响 gongwen

---

## 二、核心概念：方案底稿 (Proposal Draft)

### 2.1 它是什么

方案底稿是一个**结构化的中间载体**，记录"客户想要什么"的全部已知信息。
它不是最终文档，而是**追问过程中的活体数据**——每次对话都可能修改它。

**为什么用"底稿"这个词**（明确与 context/cache 切割）：
- 客户的原始材料是"源头"，但源头可能模糊/矛盾/缺失
- gongwen 的工作是把源头"提炼"成可用的结构化信息
- 这个结构化信息就是"底稿"——它可能不完整，但比源头可用，且会持续修订
- **不用"缓存"**：cache 暗示"临时存储/可丢弃"，底稿暗示"工作文档/持续打磨"
- **不用"context"**：gongyi 已用 `.ai/CONTEXT.md`（L1 导航），grill-with-docs 也用 CONTEXT.md（术语表），蹭这个名字会混淆
- **"底稿"的语义**：出版/印刷行业的"工作底稿"——非定稿、持续修改、是最终印刷品的源头
- 后续的 gongsheji/gongyi 只读底稿，不重新审问客户

### 2.2 底稿的 Schema（9 个字段）

```yaml
proposal_cache:
  meta:
    project_name: ""           # 项目名
    one_liner: ""              # 一句话定位
    created_at: ""
    last_updated: ""
    status: building|interrogating|stress_testing|finalized
    source_path: document|dialogue   # 入口路径标记

  goal:                        # 目标（最重要）
    primary: ""                # 主目标
    secondary: []              # 次要目标
    success_criteria: []       # 成功标准（可验证）
    anti_goals: []             # 反目标（明确不做什么）

  stakeholders:                # 干系人
    - name: ""
      role: ""                 # 用户/管理员/第三方/系统
      needs: []
      constraints: []

  entities:                    # 核心实体/概念（带定义）
    - name: ""
      definition: ""
      attributes: []
      relationships: []        # 与其他实体的关系

  glossary:                    # 术语表（领域语言）
    - term: ""
      definition: ""
      source: client|inferred  # 客户原话 vs AI 推断（推断的需确认）

  decisions:                   # 决策记录（ADR 风格）
    - id: ADR-001
      title: ""
      context: ""              # 为什么需要这个决策
      options: []              # 备选方案
      chosen: ""
      rationale: ""            # 为什么选这个
      status: proposed|confirmed|superseded
      confidence: high|medium|low

  constraints:                 # 约束条件
    - type: hard|soft          # hard=不可违反，soft=偏好
      description: ""
      source: client|regulatory|technical

  assumptions:                 # 假设（未经证实的）
    - description: ""
      needs_validation: true   # true=待验证，需列入 open_questions
      validated: false

  open_questions:              # 待澄清问题（追问的来源！）
    - id: Q-001
      question: ""
      priority: blocker|high|medium|low
      related_to: entity:User|decision:ADR-002|assumption:A-003
      status: open|answered|deferred
      answer: ""
      answered_at: ""

  business:                    # 商业维度（商业项目必填，非商业项目可空）
    is_commercial: true|false  # 是否商业项目（不明则列入 open_questions 先问）
    sell_what:                 # 卖什么 —— "你卖的是什么"
      offering: ""             # 产品/服务（一句话能说清吗？说不清就是没想清楚）
      form: ""                 # 形态：订阅/一次性买断/SaaS/咨询/分成/广告
      pricing: ""              # 定价 + 定价逻辑（为什么是这个价）
    sell_to_whom:              # 给谁 —— "你的客户是谁"
      target_segment: ""       # 目标客群（越具体越好，"所有人"=没想清楚）
      persona: ""              # 典型用户画像
      channel: ""              # 怎么触达他们（销售/渠道/自然流量/转介绍）
    why_buy_yours:             # 为什么买你的 —— 99.999% 的人死在这
      alternatives: []         # 客户现在用什么替代方案（包括"不用"）
      differentiation: ""      # 你的差异化（比替代方案好在哪）
      moat: ""                 # 护城河：网络效应/规模/品牌/专利/转换成本/数据
      proof: ""                # 凭什么证明你做得到（资源/经验/数据/已签客户）
      why_not_competitor: ""   # 凭什么你做了别人抄不走

  scenarios:                   # 场景用例
    - name: ""
      trigger: ""              # 触发条件
      steps: []                # 步骤
      expected: ""             # 预期结果
      edge_cases: []           # 边界情况

  contradictions:              # 检测到的矛盾点
    - id: C-001
      description: ""
      items: []                # 冲突的条目引用
      resolution: ""           # 解决方案（追问后填）
      status: open|resolved
```

### 2.3 为什么是这 9 个字段（设计逻辑）

| 字段 | 为什么必须有 | 如果缺失会怎样 |
|------|-------------|---------------|
| `goal` | 没有目标就无法判断决策对错 | AI 会按自己的理解做，偏离客户意图 |
| `stakeholders` | 不同干系人需求可能冲突 | 决策时遗漏某方利益，后期返工 |
| `entities` | 实体定义不清=数据模型瞎猜 | gongsheji 写出来的 schema 全错 |
| `glossary` | 领域术语歧义是需求模糊的头号原因 | "客户说的 user 和我们理解的 user 不是一回事" |
| `decisions` | 决策没记录=下次又问一遍 | 跨 session 无法交接 |
| `constraints` | 硬约束违反=项目失败 | "哦原来必须支持 IE8" → 推倒重来 |
| `assumptions` | 隐藏假设是 bug 的温床 | 上线才发现假设错了 |
| `open_questions` | **这是追问的引擎** | 没有它，gongwen 不知道问什么 |
| `business` | 商业项目不答三问=死路一条 | 投入做完发现没人买，浪费 months of work |
| `scenarios` | 场景缺失=无法压力测试 | 边界情况全靠线上事故发现 |
| `contradictions` | 矛盾不解决=方案自带 bug | 客户自己都没发现的需求冲突 |

> **关于 business 字段**：不是所有项目都需要（内部工具/开源项目/学习项目可空）。
> 但只要涉及"挣钱"，三问就是 **blocker 级**——答不上来不进 gongsheji。
> 经验法则：客户答"卖给所有人"="不知道卖给谁"；答"比竞品好"=没护城河；
> 答"我们有技术优势"=没证据。这些回答要继续追问到具体证据。

---

## 三、运作逻辑（4 阶段）

### 阶段 1：建立底稿 (Build)

#### Pre-step：查询 gongyi 现有记忆（必做，无论哪条路径）

> **核心洞察**：客户带来的"新方案"很可能是在**已有项目**上的演进。
> 不查 gongyi 就开始审问，等于让客户重新讲一遍已经记录过的东西，
> 还可能让新方案违反既有的硬约束或推翻已确认的 ADR。

```
gongwen 启动
    │
    ↓
调用 gongyi query_db（如果项目已有 .ai/project.ai.db）
    │
    ├─ 查 entities/tables   → 预填 entities 字段（标记 source: gongyi）
    ├─ 查 constraints       → 预填 constraints 字段（标记 source: gongyi，硬约束）
    ├─ 查 decisions         → 预填 decisions 字段（标记 status: confirmed, source: gongyi）
    │                          新方案不能违反这些已确认决策
    ├─ 查 modules           → 帮助理解现有代码结构（不进底稿，作为审问背景）
    └─ 查 api_routes        → 现有能力清单（帮助判断"能不能复用"）
    │
    ↓
初版底稿已含 gongyi 预填内容
    │
    ↓ 进入 Path 1 或 Path 2
```

**与 gongyi 的边界**：
- gongwen 只**读** gongyi，不写
- gongyi 预填的字段标记 `source: gongyi`，审问中如果客户要推翻，必须显式标记为新 decision 并 supersede 旧的
- 如果项目没有 gongyi 知识库（全新项目），跳过本步，底稿从零开始

#### 两条入口路径，都在 Pre-step 之后执行

#### Path 1：客户有文档

```
客户上传 .docx/.pdf/.md
        │
        ↓ (agent 层负责识别成文本)
   ┌──────────────────┐
   │ gongwen 接收文本 │
   └──────────────────┘
        │
        ↓
   扫描提取：
   ├─ 标题/摘要 → goal.primary
   ├─ 提到的角色 → stakeholders
   ├─ 名词概念 → entities + glossary
   ├─ "必须/应该/不得" → constraints
   ├─ "我们决定/选择" → decisions
   ├─ "假设/默认" → assumptions
   ├─ "如果/当...时" → scenarios
   └─ 模糊点/缺失点 → open_questions
        │
        ↓
   生成初版底稿（status: building → interrogating）
```

**关键**：gongwen 不做 OCR/解析，只做"文本 → 结构化抽取"。
识别质量差时，gongwen 应该在 open_questions 里标记"材料识别可能不准，请客户确认"。

#### Path 2：客户有想法

```
客户口述想法（"我想做个 XX"）
        │
        ↓
   gongwen 启动空底稿（status: building, source_path: dialogue）
        │
        ↓
   先问 3 个锚定问题（一次性问，建立骨架）：
   Q1: 你想解决什么问题？（→ goal.primary）
   Q2: 谁会用这个？（→ stakeholders）
   Q3: 成功长什么样？（→ goal.success_criteria）
        │
        ↓ 客户回答后填入底稿
   底稿有了骨架（status: interrogating）
        │
        ↓ 与 Path 1 汇合，进入阶段 2
```

**Path 1 + Path 2 汇合点**：两条路径在"阶段 2 追问"处统一。
区别只在"底稿初始内容从哪来"——Path 1 来自文档抽取，Path 2 来自 3 个锚定问题。
之后的所有流程完全相同。

#### 商业判定（汇合后立即执行，决定是否触发商业三问）

```
底稿已有骨架（goal + stakeholders 至少有内容）
    │
    ↓
gongwen 判定 is_commercial：
   ├─ 客户明确说"赚钱/盈利/收费/卖" → true
   ├─ 方案文档含定价/付费/订阅/商业模式章节 → true
   ├─ 客户明确说"内部工具/开源/学习" → false
   └─ 不明 → 列入 open_questions 先问"这个项目要挣钱吗？"
    │
    ↓
如果是商业项目 (is_commercial: true)：
   自动注入 3 个 blocker 级 open_questions：
   ├─ Q-biz-1: "你卖的是什么？"（→ business.sell_what）
   ├─ Q-biz-2: "你的客户是谁？怎么触达？"（→ business.sell_to_whom）
   └─ Q-biz-3: "客户为什么买你的而不是替代方案？"
              （→ business.why_buy_yours，含 alternatives/moat/proof）
    │
    ↓
进入阶段 2，商业三问因 blocker 优先级会最先被问
```

**判定不清时不要猜**：把"是否商业项目"作为第一个 open_question，
等客户明确后再决定是否注入商业三问。猜错会让内部工具被强行审问商业逻辑，浪费客户时间。

### 阶段 2：追问 (Interrogate) —— gongwen 的核心引擎

**铁律：一次只问一个问题**（借鉴 grill-with-docs，不可违反）。

#### 2.1 追问的优先级队列

gongwen 不是随机问，而是按优先级从 `open_questions` + `contradictions` + `assumptions.needs_validation` 里选下一个问题：

```
优先级排序：
1. contradictions (status: open)          ← 矛盾最致命，必须先解决
2. open_questions (priority: blocker)     ← 阻塞性问题，含商业三问
3. assumptions (needs_validation: true)   ← 隐藏假设，先验证
4. open_questions (priority: high)        ← 高优先级问题
5. open_questions (priority: medium)      ← 中优先级
6. glossary (source: inferred)            ← AI 推断的术语，需客户确认
7. open_questions (priority: low)         ← 低优先级（可 defer）
```

**同优先级内的子排序规则**：
- **blocker 内**：商业三问 (Q-biz-1 → Q-biz-2 → Q-biz-3) 优先于其他 blocker。
  理由：商业三问的答案会决定后续技术决策的边界（卖什么决定做什么，
  给谁决定 UX，为什么决定护城河投入），先问完避免白做。
  商业三问内部必须按 1→2→3 顺序，因为"给谁"依赖"卖什么"，
  "为什么买"依赖前两者。
- **其他同优先级**：按 `related_to` 引用的字段优先级决定（goal 相关 > scenarios 相关 > 其他）。

#### 2.2 单轮追问流程

```
gongwen 选出最高优先级问题 Q
        │
        ↓
   向客户提问（只问 Q，不附带其他问题）
        │
        ↓ 客户回答
   解析回答：
   ├─ 直接答案 → 更新 Q.answer, Q.status=answered
   ├─ 暴露新矛盾 → 新增 contradiction
   ├─ 暴露新假设 → 新增 assumption
   ├─ 暴露新术语 → 新增 glossary
   ├─ 触发新问题 → 新增 open_question
   └─ 修改既有决策 → 更新 decision（status: superseded 如果推翻）
        │
        ↓
   检查底稿是否还需追问（见 2.3 收敛判定）
        │
   ├─ 是 → 回到"选出最高优先级问题"，继续
   └─ 否 → 进入阶段 3（压力测试）
```

#### 2.3 收敛判定（什么时候停止追问）

满足**全部**条件才算"追问收敛"，可进入压力测试：
- `contradictions` 中无 `status: open`
- `open_questions` 中无 `priority: blocker` 或 `high` 且 `status: open`
- `assumptions` 中所有 `needs_validation: true` 的都已 `validated: true`
- `glossary` 中所有 `source: inferred` 的都已转 `source: client`（客户确认过）
- `decisions` 中无 `status: proposed` 且 `confidence: low`（低信心决策需确认）
- **商业项目特有**（`business.is_commercial: true` 时）：
  - `business.sell_what.offering` 不为空且非"所有人都能用"类套话
  - `business.sell_to_whom.target_segment` 具体到可识别的客群（不接受"所有人"/"中小企业"等模糊表述）
  - `business.why_buy_yours` 至少有 `differentiation` + `proof` 两个字段非空
  - 三问的答案不触发"反模式检测"（见下）

**商业三问的反模式检测**（命中即视为未答，重新追问）：

| 问题 | 反模式（不算答出来） | 应继续追问到什么程度 |
|------|---------------------|---------------------|
| 卖什么 | "一个平台"/"一个工具"/"一个 App" | 说清解决什么具体场景的具体问题 |
| 给谁 | "所有人"/"中小企业"/"年轻人" | 具体到行业+规模+角色（如"50-200人的律所合伙人"） |
| 为什么买 | "比竞品好"/"功能更多"/"价格便宜" | 说清比**哪个具体竞品**好在**哪个具体点** |
| 凭什么你做 | "我们有技术优势"/"我们团队强" | 拿出资源/数据/已签客户/独家渠道等可验证证据 |
| 凭什么不被抄 | "我们先发优势"/"我们更懂用户" | 说清网络效应/转换成本/数据壁垒/独家资源等结构性护城河 |

**注意**：收敛≠完美。中/低优先级的 open_questions 可以 `status: deferred` 推迟。
gongwen 应告知客户"还有 N 个低优先级问题被推迟，是否继续？"

### 阶段 3：压力测试 (Stress Test)

追问收敛后，底稿"自洽"了，但未必"扛得住现实"。压力测试主动找麻烦：

#### 3.1 三类压力测试

```
A. 边界场景挑战
   - 从 scenarios.edge_cases 里挑未覆盖的
   - 主动构造极端场景："如果同时有 1000 个用户..."、"如果网络断开..."
   - 客户答不上来 → 新增 open_question（回到阶段 2）

B. 矛盾交叉检测
   - 跨字段比对：goal.anti_goals 是否与 scenarios 冲突？
   - constraints.hard 是否与 decisions.chosen 冲突？
   - stakeholders 的 needs 是否互相冲突？
   - 发现矛盾 → 新增 contradiction（回到阶段 2）

C. 假设挑战
   - 对每个 assumption 提"凭什么这么假设？"
   - 客户给不出依据 → 降级为 open_question（回到阶段 2）
```

#### 3.2 压力测试的退出

压力测试可能反复触发回阶段 2（发现新问题就重新追问）。
当**一轮完整压力测试没产生任何新 contradiction / open_question** 时，进入阶段 4。

### 阶段 4：定稿 (Finalize)

```
底稿 status: stress_testing → finalized
        │
        ↓
   输出 3 份产物：
   ├─ PROPOSAL.md        ← 人类可读的方案文档（从底稿渲染）
   ├─ draft.yaml      ← 底稿的原始结构化数据（给 gongsheji 读）
   └─ PENDING.md          ← 给客户的审查清单（待确认的 deferred 问题 + 关键决策）
        │
        ↓
   移交决策：
   ├─ 客户确认 PENDING.md → 加载 gongsheji，喂 draft.yaml
   ├─ gongsheji 完成后 → decisions 导入 gongyi 的 decisions 表
   └─ gongyi 沉淀代码层知识
```

---

## 四、方案底稿的物理形态

### 候选方案曾评估

| 方案 | 优点 | 缺点 |
|------|------|------|
| **A. 单个 YAML 文件** | 人可读、git 友好、schema 清晰 | 大方案时文件很长，查询不便 |
| **B. SQLite（仿 gongyi）** | 可查询、可版本化、结构化强 | 人不可读，需工具查看 |
| **C. YAML + 衍生 Markdown** | YAML 存数据，MD 给人看 | 双写一致性需维护 |
| **D. 多个 YAML 分片** | 每个字段一个文件，模块化 | 文件多，管理复杂 |

### 决策：方案 C（YAML 是源，PROPOSAL.md 是渲染产物）

- `draft.yaml` 是 source of truth，AI 维护这个文件
- `PROPOSAL.md` 是从 draft.yaml 渲染出的人类可读文档（定稿时生成）
- `PENDING.md` 是从 draft.yaml 的 `open_questions` (status: deferred) 渲染出的待确认清单
- 渲染是单向的：draft.yaml → PROPOSAL.md/PENDING.md，反向不回流
- 理由：与 gongyi 的"SQLite 是源 + PROJECT_SPEC.md 是渲染"模式一致，团队心智模型统一

---

## 五、与其他 skill 的协作契约

### 5.1 上游：接收材料 + 既有记忆

```
agent 层（文档识别）→ 文本片段 → gongwen
客户口述 → gongwen 直接接收
gongyi 知识库 → 既有实体/约束/决策 → gongwen 预填底稿（Pre-step）
```

gongwen 不关心材料怎么来的，只接收文本。
但 gongyi 是**结构化上游**——直接预填底稿字段，不是文本材料。
三种上游的关系：
- **gongyi**：提供"已知事实"（既有约束不能违反、既有决策不能推翻）
- **agent 层文档识别**：提供"客户已写下来的想法"
- **客户口述**：提供"客户脑子里的想法"
后两者进 Path 1/2，前者进 Pre-step，三者共同构成初版底稿。

### 5.2 下游：移交给 gongsheji

gongwen 产出 `draft.yaml`，gongsheji 读取后：
- `goal` → 写入 spec.md 的"目标"章节
- `entities` → 数据模型设计的基础
- `constraints` → spec.md 的"非功能需求"
- `decisions` → spec.md 的"架构决策"章节
- `scenarios` → 测试用例的来源

gongsheji **不重新审问客户**，只基于底稿做工程设计。如果发现底稿不够，**回到 gongwen** 而不是自己问。

### 5.3 与 gongyi 的 ADR 同步

```
gongwen 阶段 4 定稿
        │
        ↓
   decisions（方案层决策）→ 导入 gongyi.decisions 表
        │
        ↓
   gongsheji 执行过程中产生的新决策 → gongyi.decisions 表（实现层决策）
```

**分工**：
- gongwen 的 decisions = "为什么这么做"（产品/方案决策）
- gongyi 的 decisions = "怎么实现的"（技术决策）
- 两类决策都进 gongyi.decisions 表，用 `type` 字段区分（`product` vs `technical`）

### 5.4 与 gongyi 的 CONTEXT.md 命名冲突（已解决）

- gongyi 的 `.ai/CONTEXT.md` = L1 导航（项目概述/架构/模块索引）
- grill-with-docs 的 CONTEXT.md = 术语表
- gongwen **不使用 CONTEXT.md 这个名字**，改用 `glossary` 字段存在底稿里
- 渲染时 glossary 输出为 `PROPOSAL.md` 的"术语表"章节，不单独成文件
- 三者物理隔离：gongyi 用 `.ai/CONTEXT.md`，gongwen 用 `.draft/draft.yaml` 的 glossary 字段，无撞名

---

## 六、触发与加载

### 6.1 何时触发 gongwen

| 客户说 | gongcheng 应加载 gongwen |
|--------|--------------------------|
| "我有一份方案文档，帮我看看" | 是（Path 1） |
| "我有个想法，你帮我捋一捋" | 是（Path 2） |
| "这个需求有点模糊" | 是 |
| "在写代码前先把需求问清楚" | 是 |
| "直接实现这个功能" | 否（直接 gongsheji） |
| "改一下这段代码" | 否（直接 gongyou + 代码修改流程） |

### 6.2 gongcheng 的工作类型表需追加

完成后在 gongcheng/SKILL.md 第一章工作类型表追加：

```
| 11 | 需求审问/方案澄清/矛盾检测 | gongwen | - | 需求模糊直接进 gongsheji 导致返工 |
```

并在第三章子 skill 索引追加 gongwen 条目。

---

## 七、设计决策（已敲定）

> 以下 12 项决策在 v1 落地时遵循。后续版本如需调整，在本节追加 supersede 记录。

1. **底稿的版本管理** —— 重大变更才 commit
   - 解决一个 contradiction、supersede 一个 decision、回答一个 blocker 问题 → git commit 一次
   - 不在每轮对话后 commit（避免 git 历史噪声）
   - commit message 格式：`draft: <变更类型> <简述>`，如 `draft: resolve contradiction C-003 客群定义`

2. **底稿的存储位置** —— `.draft/` 目录
   - 路径：`<project.root>/.draft/draft.yaml`（源）+ `<project.root>/.draft/PROPOSAL.md`（渲染）+ `<project.root>/.draft/PENDING.md`（待确认）
   - 与 gongyi 的 `.ai/` 物理隔离，体现"方案层 vs 代码层"

3. **多方案并存** —— v1 只支持单方案
   - 一个项目一个 `.draft/` 目录
   - 多方案场景（v2）：`.draft/<name>/` 子目录，每个独立一份底稿

4. **追问语气** —— 默认"专业但直接"
   - 不绕弯子、不寒暄、不输出"好的让我来帮你"等套话
   - 不冒犯：用"你"不用"您"，但不用反问/嘲讽句式
   - 可在底稿 meta 里覆盖：`tone: gentle|direct|grill`（默认 direct）

5. **压力测试的深度** —— "一轮无新发现即停"
   - 一轮 = 覆盖所有 scenarios.edge_cases + 跨字段矛盾检测（7 类组合）+ 假设挑战各一遍
   - 一轮内产生任何新 contradiction / open_question → 回阶段 2，下一轮重算
   - 连续一轮零新发现 → 进入阶段 4
   - 最多 3 轮压力测试，仍未收敛 → 强制定稿并在 PENDING.md 标记未解项

6. **与 gongsheji 的回退机制** —— 只补缺、不重审
   - gongsheji 执行中发现底稿缺字段 → 在底稿 `open_questions` 追加标记 `source: gongsheji-rollback`
   - gongcheng 重新加载 gongwen，gongwen 只处理带 rollback 标记的问题
   - 已答过的部分不重新问客户

7. **底稿 schema 不脚本化** —— 纯 YAML 手写 + AI 维护
   - gongwen 不提供 build_db 类脚本
   - gongyi 查询直接调用 gongyi 的 `query_db.py`（Pre-step）
   - schema 演化靠 AI 按本文件第二章的 yaml 结构维护

8. **gongtu 配合** —— 阶段 4 定稿时调用
   - 用 gongtu 渲染：实体关系图（从 entities 字段）+ 场景流程图（从 scenarios 字段）
   - 输出 SVG 附在 PROPOSAL.md 对应章节
   - gongtu 不可用时降级为 Mermaid 代码块（不渲染）

9. **商业判定** —— gongwen 自动判定，不明才问
   - 材料含定价/付费/订阅/商业模式章节 → `is_commercial: true`
   - 材料含"内部工具/开源/学习/练手" → `is_commercial: false`
   - 不明 → 注入一个 open_question（priority: blocker）问客户
   - 误判代价：内部工具被问商业三问，浪费 3 轮对话；宁可问一句也不猜

10. **反模式检测** —— 规则表 + LLM 兜底（两层）
    - 第一层：规则表（本文件 2.3 节的反模式表），命中即视为未答
    - 第二层：规则表未命中但回答模糊（如"主要面向成长型企业"）→ LLM 判断是否具体
    - 两层都通过才算答出来

11. **gongyi 查询时机** —— 只在 Pre-step 查一次
    - 审问过程中 gongyi 不会变（没人写代码），重查浪费
    - 客户主动要求"看一下现有代码" → 手动触发重查（标记 `source: customer-request`）

12. **business 答案回流 gongyi** —— 拆成 ADR 导入 decisions 表
    - 定稿时把 business 三问的答案各拆成一条 ADR
    - 导入 `gongyi.decisions` 表，`type: business`（区别于 `type: product` / `type: technical`）
    - 不为 business 单独建表，避免 gongyi schema 膨胀
    - 示例：ADR-BIZ-01 "目标客群=50-200人律所合伙人"，ADR-BIZ-02 "护城河=独家渠道协议"

---

## 八、与 grill-with-docs 的对照表

| 维度 | grill-with-docs | gongwen |
|------|----------------|---------|
| 载体 | CONTEXT.md + ADR 文件（分离） | 方案底稿（统一 YAML） |
| 上游 | 单一（客户文档） | 三上游：gongyi 既有记忆 + agent 文档识别 + 客户口述 |
| 文档识别 | skill 自己处理 | agent 层处理（明确边界） |
| 商业维度 | 无 | 商业三问（卖什么/给谁/为什么买你的）+ 反模式检测 |
| 追问节奏 | 一次一个问题 | 一次一个问题（继承） |
| 追问优先级 | 隐式 | 显式优先级队列（7 级，商业三问 blocker 优先） |
| 矛盾检测 | 术语冲突挑战 | 跨字段矛盾 + 术语冲突 |
| 压力测试 | 具体场景讨论 | 独立阶段（边界/矛盾/假设三类） |
| 决策记录 | ADR markdown 文件 | 底稿的 decisions 字段（含 confidence） |
| 收敛判定 | 隐式 | 显式 5 条 + 商业项目特有 4 条 + 反模式检测 |
| 产出 | CONTEXT.md + ADR/ | PROPOSAL.md + draft.yaml + PENDING.md |
| 下游 | 不明确 | 明确移交 gongsheji，决策回流 gongyi |

---

## 九、实现范围

**v1 包含**：
- ✅ 单一 YAML 底稿文件（schema 见第二章，含 business 字段）
- ✅ Pre-step 查询 gongyi 预填底稿（如有 .ai/project.ai.db）
- ✅ 双路径入口（Path 1 文档抽取 / Path 2 锚定三问）
- ✅ 商业判定 + 商业三问注入（blocker 优先级）
- ✅ 优先级驱动的单问题追问（含商业三问两层反模式检测）
- ✅ 三类压力测试（边界/矛盾/假设，最多 3 轮）
- ✅ 定稿输出 PROPOSAL.md + draft.yaml + PENDING.md
- ✅ gongtu 集成（定稿时渲染 ER 图 + 场景流程图）

**v1 不含**（后续版本再议）：
- ❌ 脚本化（无 build_db 类工具，gongyi 查询直接调 gongyi 的 query_db.py）
- ❌ 多方案并存（v2 用 `.draft/<name>/` 子目录支持）
- ❌ 底稿版本化（靠 git 历史回溯，重大变更才 commit）

---

## 十、快速开始

### 触发条件

当 gongcheng 识别到以下场景时加载 gongwen：
- 客户带来方案文档（.docx/.pdf/.md）想"实现"或"评估"
- 客户口述想法但需求模糊
- 在进入 gongsheji 之前需要把需求审问清楚

### 最小操作流程

```
1. 加载 gongwen（由 gongcheng 调度）
2. Pre-step：如有 .ai/project.ai.db → 调 gongyi query_db 预填底稿
3. 识别入口路径（Path 1 文档 / Path 2 想法）
4. 构建初版底稿 → 商业判定 → 注入商业三问（如适用）
5. 进入追问循环（一次一问，按优先级队列）
6. 收敛判定通过 → 压力测试（最多 3 轮）
7. 定稿 → 输出 PROPOSAL.md + draft.yaml + PENDING.md
8. 调 gongtu 渲染 ER 图 + 场景流程图附入 PROPOSAL.md
9. 移交 gongsheji（喂 draft.yaml），business 答案回流 gongyi.decisions
```

### 在 gongcheng 注册

本 skill 上线后，在 gongcheng/SKILL.md 第一章工作类型表追加：

```
| 11 | 需求审问/方案澄清/矛盾检测/商业三问 | gongwen | - | 需求模糊直接进 gongsheji 导致返工 |
```

并在第三章子 skill 索引追加 gongwen 条目。
