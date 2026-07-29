---
slug: gongsheji
displayName: 工设计
version: 1.3.0
summary: 严格工程设计工作流，spec→plan→TDD 执行→评审，用于编码实现。
license: MIT
name: gongsheji
description: |
  工设计 — 严格工程设计工作流。当用户明确要求（如 "enable superpowers", "开启工程设计模式", "включи superpowers"）
  或任务涉及 coding/build/debug 时触发。流程：明确目标 → 写 spec → 写 plan → 小步执行（优先 TDD）→ 评审完成。
  仅用于编码工作流，不用于日常对话。
---

# 工设计 (gongsheji) — 严格工程设计工作流

> 原 superpowers-mode，"工"字系列通用 skill。
> 仅当用户明确要求启用，或任务涉及 coding/build/debug 时触发。

## 状态文件

模式状态记录在：

`memory/gongsheji-mode.md`

格式：

```md
enabled: true|false
updatedAt: <ISO>
notes: <optional>
```

## 启用/禁用命令

- 启用短语：`enable superpowers`、`开启工程设计`、`superpowers on`、`включи superpowers`
  - 写 `enabled: true` 到状态文件
  - 用 1 条短消息确认
- 禁用短语：`disable superpowers`、`关闭工程设计`、`superpowers off`、`выключи superpowers`
  - 写 `enabled: false`
  - 用 1 条短消息确认
- 状态查询：`superpowers status`、`工程设计状态`、`статус superpowers`
  - 读状态并报告 enabled/disabled

## 启用时的工作流（仅 coding 任务）

对 coding/build/debug 请求，按此顺序：

1. **快速明确目标和约束**
2. **产出简短 spec**（分块，易审查）
3. **产出实现计划**（小任务粒度）
4. **（可选，30 秒）迷你风险评审**：
   - 这个改动在生产环境可能怎么失败？
   - 最薄弱的依赖/状态假设是什么？
   - 什么信号会显示回归 + 如何快速回滚？
5. **逐任务执行**（高风险改动优先 test-first）
6. **对照验收标准验证**，然后总结结果 + 下一步

需要时使用 `references/` 下的模板。

## 红旗（快速自检）

如果注意到这些想法，放慢并应用工作流：
- "快速冲一把不用计划" — 非平凡改动
- "显然没问题，测试稍后" — 高风险编辑
- "不需要回滚" — 触碰 config/auth/cron/system 文件前
- "看起来能用" — 没有显式验证

## 边界

- 不对非 coding 对话强制此工作流
- 如果用户要求速度（`quick`、`just do it`、`快速搞一下`），跳到最小计划并执行
- 保持更新简洁，避免流程噪音

## 与其他工字 skill 的协作

- **gongcheng**：gongsheji 是 gongcheng 工作类型表第 3 行（项目设计）的执行 skill
- **gongyou**：执行阶段每改一个文件前，gongyou 协议2 做影响检查
- **gongyi**：完成后 gongyi 更新知识库
- **gongkong**：如需项目配置（如部署路径），由 gongkong/config.yaml 注入
