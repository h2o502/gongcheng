---
slug: gongshu
displayName: 工数
version: 1.3.1
summary: 数据库操作风险分级、强制备份、确认门禁、审计日志，防止 AI 误操作导致数据不可恢复。
license: MIT
name: gongshu
description: |
  数据安全守护 Skill，与 gongyou（文件守护）平级，专门守护数据层。
  定义 L1-L4 四级风险分级，强制备份、确认门禁、歧义追问、审计日志。
  任何涉及数据库读写的操作前必须触发。
  数据库连接清单由 gongkong/config.yaml 注入。
tags:
  - data-safety
  - database
  - risk-control
  - backup
  - audit
  - chinese
---

# 工数 (gongshu) — 数据安全守护

> "工"字系列通用 skill，与 gongyou（文件守护）平级，专门守护数据层。
> **本质**：让每一次数据操作都可回滚、可审计、可追责。
> 数据库连接清单由 `gongkong/config.yaml` 的 `db.connections` 注入。

## 设计动机

AI 执行数据库操作时，容易犯三类致命错误：
1. **歧义指令未追问**——把"设置唯一用户密码"理解为"禁用其他所有用户"
2. **覆盖性操作无备份**——直接 UPDATE 覆盖原值，没有先备份
3. **无回滚预案**——执行后才发现 binlog 无法回放，没有数据库备份

本 skill 通过四级风险分级 + 强制备份 + 确认门禁 + 审计日志，确保数据操作可回滚、可审计。

## 何时触发

- **任何数据库读写操作前**：自动执行协议1（风险分级）
- **L3/L4 级操作**：自动执行协议2（备份 + 确认门禁）
- **操作完成后**：自动执行协议3（审计日志）
- **用户指令含歧义**：自动执行协议4（歧义追问）

---

## 协议1：风险分级

任何 SQL/数据操作前，必须先判定风险等级。

### 四级风险分级表

| 等级 | 操作示例 | 强制要求 |
|------|---------|---------|
| **L1 只读** | SELECT / EXPLAIN / SHOW | 无 |
| **L2 单行写** | 单行 INSERT / 单行 UPDATE（主键限定）/ 单行 DELETE（主键限定） | 记录操作日志 |
| **L3 批量写** | 批量 UPDATE（>1行）/ 批量 DELETE（>1行）/ DDL（ALTER TABLE ADD COLUMN） | ① 先备份受影响行 ② 用户确认 ③ 记录回滚 SQL |
| **L4 不可逆** | DROP TABLE / DROP DATABASE / TRUNCATE / 无 WHERE 的 UPDATE·DELETE / 覆盖 password·token·secret·balance 等敏感字段 / GRANT ALL | ① 全表备份 ② 用户明确二次确认 ③ 记录原值 ④ 评估回滚可行性 |

### 风险判定流程

```
准备执行 SQL/数据操作
  │
  ├─ 1. 是 SELECT/EXPLAIN/SHOW 吗？
  │     ├─ 是 → L1，直接执行
  │     └─ 否 → 继续
  │
  ├─ 2. 影响行数预估（先 EXPLAIN 或 COUNT）
  │     ├─ 1 行 → L2，记录日志后执行
  │     ├─ >1 行 → L3，进入协议2
  │     └─ 无法预估 → 默认按 L4 处理
  │
  ├─ 3. 是否触及敏感字段？
  │     ├─ password_hash / token / secret / api_key / balance / email / phone
  │     └─ 是 → 直接升级为 L4，进入协议2
  │
  ├─ 4. 是否 DDL 或不可逆操作？
  │     ├─ DROP / TRUNCATE / ALTER DROP COLUMN → L4
  │     └─ 无 WHERE 的 UPDATE/DELETE → L4
  │
  └─ 输出风险报告
```

### 输出格式

```
=== 工数 · 风险分级报告 ===
操作类型：<SELECT / INSERT / UPDATE / DELETE / DDL / DROP>
目标表：<table_name>
影响行数预估：<N 行 / 全表 / 未知>
敏感字段：<是/否>（<字段名>）
风险等级：<L1 / L2 / L3 / L4>
强制要求：<对应等级的要求>
状态：<✅ 可执行 / ⚠️ 等待用户确认 / 🔴 必须备份+二次确认>
```

---

## 协议2：备份 + 确认门禁

L3/L4 操作必须按顺序完成以下步骤，**缺任何一步禁止执行**。

### 步骤1：备份受影响数据

**L3 级备份**（批量 UPDATE/DELETE）：
```sql
-- 创建备份表，表名带日期后缀
CREATE TABLE IF NOT EXISTS backup_<table>_<YYYYMMDD> AS
SELECT * FROM <table> WHERE <操作将影响的 WHERE 条件>;
```

**L4 级备份**（DROP/TRUNCATE/敏感字段覆盖/无 WHERE）：
```sql
-- 全表备份
CREATE TABLE IF NOT EXISTS backup_<table>_<YYYYMMDD> AS
SELECT * FROM <table>;

-- 敏感字段覆盖时，额外记录原值
CREATE TABLE IF NOT EXISTS audit_<table>_<YYYYMMDD> AS
SELECT id, <敏感字段>, NOW() AS snapshot_time FROM <table> WHERE <操作条件>;
```

**文件类数据备份**（配置文件、JSON 等）：
```bash
cp <file> <file>.before-<操作描述>-<YYYYMMDD>
```

### 步骤2：生成回滚 SQL

```sql
-- L3 批量 UPDATE 回滚
UPDATE <table> SET <字段>=<旧值> WHERE <条件>;

-- L4 敏感字段覆盖回滚（从备份表恢复）
UPDATE <table> t
JOIN audit_<table>_<YYYYMMDD> a ON t.id = a.id
SET t.<敏感字段> = a.<敏感字段>;

-- L4 DROP TABLE 回滚（需从备份表恢复）
CREATE TABLE <table> AS SELECT * FROM backup_<table>_<YYYYMMDD>;
```

将回滚 SQL 写入 `/tmp/rollback_<table>_<YYYYMMDDHHMM>.sql`，告知用户路径。

### 步骤3：用户确认门禁

**L3 确认格式**：
```
⚠️ L3 级数据操作待确认

操作：UPDATE tf_users SET status=1 WHERE created_at < '2024-01-01'
影响：约 234 行
备份：backup_tf_users_20260707（234 行已备份）
回滚：/tmp/rollback_tf_users_202607071430.sql

确认执行吗？[y/n]
```

**L4 确认格式**：
```
🔴 L4 级不可逆数据操作待确认

操作：UPDATE tf_users SET password_hash='DISABLED_xxx' WHERE id != 1
影响：116 行，敏感字段 password_hash
备份：audit_tf_users_20260707（116 行原哈希已保存）
回滚：/tmp/rollback_tf_users_202607071430.sql

⚠️ 警告：此操作将覆盖密码哈希，用户将无法用原密码登录。
   回滚需从 audit 表恢复，请确认已保存回滚 SQL。

二次确认：请输入"我确认执行"以继续。
```

**必须用户明确回复**才能执行：
- L3：`y` 或 `yes` 或 `确认`
- L4：`我确认执行`（强制完整句）

### 步骤4：执行并验证

```sql
-- 执行操作
<原 SQL>;

-- 验证影响行数
SELECT ROW_COUNT();  -- MySQL
-- 或 SELECT changes();  -- SQLite

-- 与预估对比，如偏差 >10% 立即告警
```

---

## 协议3：审计日志

所有 L2+ 操作完成后，写入审计日志。

### 日志格式

```
[<ISO 时间>] <操作级别> | <操作人> | <表> | <操作类型> | <影响行数> | <备份位置> | <回滚SQL路径>
```

### 日志位置

- **统一日志**：`/var/log/ai-data-ops.log`（如目录不存在则 fallback 到 `/tmp/ai-data-ops.log`）
- **项目级日志**：`<project.root>/.trae/data-ops.log`

### 日志内容

```
[2026-07-07T14:30:00Z] L4 | ai-assistant | tf_users | UPDATE password_hash | 116 rows | audit_tf_users_20260707 | /tmp/rollback_tf_users_202607071430.sql
```

---

## 协议4：歧义追问

当用户指令涉及数据操作但存在歧义时，**必须先追问，禁止自行选择破坏性更大的理解**。

### 触发条件

1. 指令有多种合理解读（如"唯一用户"可指"只保留一个"或"只设置一个的密码"）
2. 指令涉及批量操作但未明确范围（如"禁用其他用户"未说明禁用登录 vs 删除账号）
3. 指令涉及不可逆操作但未提及备份（如"重置密码"未说明是否保留原密码）
4. 指令的影响范围超过 10 个对象但未明确确认（如"所有用户""全部配置""清空"）

### 追问格式

```
您的指令「<原话>」我理解为以下 N 种可能，请确认是哪种：

A. <解读1>（影响范围：<...>，可逆/不可逆）
B. <解读2>（影响范围：<...>，可逆/不可逆）
C. <解读3>（影响范围：<...>，可逆/不可逆）

我的建议：<选破坏性最小的，或最符合常规理解的>
```

### 红线

- **禁止默认选择破坏性更大的理解**
- **禁止在未确认时直接执行 L3/L4 操作**
- **禁止用"我猜你应该是 XXX"代替追问**

---

## 高风险 SQL 黑名单

以下 SQL **必须拆分为「备份 → 确认 → 执行 → 验证」四步**，禁止直接执行：

| # | SQL 模式 | 风险 | 强制流程 |
|---|---------|------|---------|
| 1 | `UPDATE ... WHERE <非主键条件>` | 影响行数不可控 | 先 COUNT → 备份 → 确认 |
| 2 | `UPDATE ... SET password_hash/token/secret/balance = ...` | 敏感字段覆盖 | 先导出原值 → 二次确认 |
| 3 | `DELETE ...` 无 WHERE 或非主键 WHERE | 批量删除 | 先备份 → 二次确认 |
| 4 | `DROP TABLE / DROP DATABASE` | 不可逆 | 全表备份 → 二次确认 |
| 5 | `TRUNCATE TABLE` | 不可逆 | 全表备份 → 二次确认 |
| 6 | `ALTER TABLE ... DROP COLUMN` | 数据丢失 | mysqldump → 二次确认 |
| 7 | `UPDATE/DELETE` 涉及 >10 行 | 批量操作 | 先 COUNT → 备份 → 确认 |
| 8 | `GRANT ALL PRIVILEGES` | 权限提升 | 记录原权限 → 二次确认 |
| 9 | `UPDATE ... SET <字段> = <常量>` 无 WHERE | 全表覆盖 | 全表备份 → 二次确认 |
| 10 | 任何涉及 `DISABLED` / `deleted` / `inactive` 状态的批量更新 | 批量禁用 | 先备份 → 确认 → 记录原状态 |

---

## 敏感字段清单

以下字段被覆盖时**自动升级为 L4**：

| 类别 | 字段名模式 |
|------|-----------|
| 认证 | `password_hash` / `password` / `passwd` / `pwd` |
| 凭证 | `token` / `api_key` / `apikey` / `secret` / `private_key` |
| 金融 | `balance` / `credit` / `amount` / `deposit` |
| 身份 | `email` / `phone` / `mobile` / `id_card` |
| 状态 | `status` / `disabled` / `deleted` / `active`（批量修改时） |
| 权限 | `role` / `permission` / `is_admin` / `is_super` |

项目可通过 `gongkong/config.yaml` 的 `db.sensitive_fields` 扩展。

---

## 与 gongkong 的协作契约

gongshu 需要以下配置字段（由 gongkong/config.yaml 提供）：

```yaml
db:
  connections:
    - name: primary
      type: mysql          # mysql / postgresql / sqlite
      host: 127.0.0.1
      port: 3306
      database: your_db
      user: your_user
      password: YOUR_PASSWORD_HERE
  sensitive_fields:        # 项目专属敏感字段（追加到默认清单）
    - "custom_secret_field"
  backup_dir: "/backup/mysql"      # 备份目录
  audit_log: "/var/log/ai-data-ops.log"  # 审计日志路径
```

换项目时只需改 config.yaml，本 SKILL.md 不用动。

---

## 与其他 skill 的协作

| 协作对象 | 协作方式 |
|---------|---------|
| **gongcheng** | 被其调度，遇到数据操作时加载 |
| **gongyou** | 互补关系：gongyou 守文件，gongshu 守数据 |
| **gongsheji** | 数据层设计决策时，gongshu 提供风险约束 |
| **gongyi** | 操作完成后同步审计日志到记忆库 |

### 触发优先级

当操作同时涉及代码和数据时：
```
gongcheng 调度
  ├─ gongyou 协议2（文件影响检查）
  ├─ gongshu 协议1（数据风险分级）  ← 并行执行
  ├─ 两者都通过后 → 执行
  └─ 任意一方告警 → 暂停，等用户确认
```

---

## 脚本

### `scripts/pre-check.sh`
执行前自动检查 SQL 风险等级、预估影响行数、识别敏感字段。

### `scripts/auto-backup.sh`
自动创建备份表、生成回滚 SQL、写入审计日志。

### `scripts/audit-log.sh`
统一写入审计日志（兼容 /var/log 和 /tmp fallback）。

---

## 检查清单（AI 自检）

每次执行数据操作前，AI 必须回答以下 6 个问题：

- [ ] 1. 这条 SQL 的影响行数预估是多少？（>10 行必须 L3，>100 行必须 L4）
- [ ] 2. 是否触及敏感字段？（是 → 直接 L4）
- [ ] 3. 是否已备份受影响数据？（L3/L4 必须备份）
- [ ] 4. 回滚 SQL 是否已生成并告知用户路径？
- [ ] 5. 用户是否已明确确认？（L3 需 y/yes，L4 需"我确认执行"）
- [ ] 6. 操作完成后是否写入审计日志？

**任何一个问题为否，禁止执行。**

---

## 事故教训记录

### 2026-07-07 · tf_users 密码哈希覆盖事故

**事故**：AI 执行 `UPDATE tf_users SET password_hash='DISABLED_xxx' WHERE id != 1` 覆盖 116 个用户密码哈希。

**根因**：
1. 指令歧义未追问（"唯一用户"理解为"只保留一个"）
2. 覆盖性操作无备份（直接 UPDATE，未先备份原哈希）
3. 无回滚预案（binlog MIXED 模式无法回放，无数据库备份）

**教训**：
1. 歧义指令必须追问，禁止默认选择破坏性更大的理解
2. 覆盖密码等敏感字段前，必须先导出原值到备份表
3. 任何 L3/L4 操作必须有回滚 SQL 并告知用户路径

**本 skill 的协议2/协议4 直接源于此事故。**
