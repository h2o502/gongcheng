---
name: gongkong
description: 项目配置注入层 — 读取同目录 config.yaml，向 gongcheng 提供项目专属配置（Git 仓库/SSH/部署路径/memory/高风险文件，及可选扩展字段）。换项目时只需改 config.yaml，SKILL.md 不动。
---

# 工控 (gongkong) — 项目配置注入层

> **配置与逻辑分离**：本 SKILL.md 只管"如何读取和应用配置"（逻辑层，通用）。
> 所有项目专属数据在同目录的 `config.yaml`（数据层，专属）。
> **换项目时**：复制整个 gongkong 目录到新项目，只改 config.yaml，SKILL.md 一字不动。

---

## 一、职责边界

gongkong 是 gongcheng（通用编排层）的项目专属补充：

| 层 | 目录 | 内容 | 换项目时 |
|----|------|------|----------|
| gongcheng（通用） | `/root/.trae-cn/skills/gongcheng/` | 规则框架、工作流骨架、子 skill 索引 | 不动 |
| **gongkong（专属）** | `<project>/.trae/skills/gongkong/` | **项目配置：Git/SSH/部署路径等** | **只改 config.yaml** |

gongkong 不做任何业务编排，只负责：读取 config.yaml → 向 gongcheng 提供配置注入。

---

## 二、config.yaml 位置与加载

**位置**：与本 SKILL.md 同目录，文件名固定为 `config.yaml`

**加载时机**：
1. gongcheng 触发后，第一时间加载 gongkong
2. gongkong 读取同目录 config.yaml
3. 解析失败（语法错误/字段缺失）时，**立即报错并指出哪一行**，不继续执行
4. 解析成功后，向 gongcheng 返回配置对象

**加载原则**：
- 所有项目配置必须从 config.yaml 读，**禁止在 SKILL.md 里硬编码**
- gongcheng 引用项目配置时，必须先经 gongkong 注入，不直接读 config.yaml

---

## 三、config.yaml Schema

```yaml
# gongkong/config.yaml — 项目专属配置
# 换项目时只需改这个文件，SKILL.md 不用动

project:
  name: <项目中文名>              # 必填，项目显示名
  root: <项目根路径>              # 必填，项目源码绝对路径

git:
  gitea_url: <Gitea 地址>         # 必填，Git 服务 URL
  repositories:                   # 必填，仓库列表（至少 1 个）
    - name: <仓库名>              #   仓库名
      local_path: <本地镜像路径>  #   rsync 同步目标路径
      description: <描述>         #   仓库内容描述

ssh:
  alias: <SSH 别名>               # 必填，~/.ssh/config 中配置的别名
  host: <服务器 IP>               # 必填，服务器地址
  port: <端口>                    # 必填，通常 22
  user: <用户名>                  # 必填，通常 root
  key: <密钥名>                   # 必填，~/.ssh/ 下的密钥文件名

deploy:
  remote_root: <远程部署根路径>   # 必填，服务器上项目部署目录
  remote_ps1: <部署脚本名>        # 必填，部署工具脚本（如 remote.ps1）
  # 部署优先级: remote_ps1 upload > remote_ps1 run > ssh > 项目配置的远程执行通道

memory:
  db_path: <SQLite 路径>          # 必填，gongyi 知识库相对路径（相对 project.root）

# 可选扩展字段（项目按需配置）
# remote_execution:
#   url: <WebSocket 地址>          # 远程执行通道（SSH 失败时的兜底）
# task_dispatch:
#   url: <WebSocket 地址>          # 任务派发机制（多任务并行时使用）

high_risk_files:                  # 必填，高风险文件清单（gongyou 协议2 使用）
  - "<glob 模式>"                 #   改动前必须用户确认的文件
```

---

## 四、字段详解

### project
- `name`：项目显示名，用于日志和报告标识
- `root`：项目源码根路径，所有相对路径基于此

### git
- `gitea_url`：Git 服务地址（自建 Gitea / GitHub / GitLab 均可）
- `repositories[]`：仓库列表，按内容性质划分（如代码/配置/前端）
  - `local_path`：rsync 同步的本地镜像目录（源码在 project.root，镜像在 local_path）

### ssh
- `alias`：`~/.ssh/config` 中预配置的别名，`ssh <alias>` 即可连接
- 其他字段用于文档记录和远程执行通道调用

### deploy
- `remote_root`：服务器上项目部署的根目录
- `remote_ps1`：部署工具脚本名（解决远程命令 heredoc/引号问题的传输方案）
- 部署优先级：`remote_ps1 upload` > `remote_ps1 run` > `ssh` > 项目配置的远程执行通道

### memory
- `db_path`：gongyi 知识库 SQLite 文件路径，相对 project.root

### high_risk_files
- glob 模式列表，匹配的文件改动前必须经 gongyou 协议2 影响检查并等用户确认
- 示例：`src/auth/**`、`**/config.{ts,json}`、`**/*.sql`

### 可选扩展字段
- `remote_execution.url`：远程执行通道地址（SSH 失败时的兜底，如 WebSocket 代理、CI runner）
- `task_dispatch.url`：任务派发机制地址（多任务并行时使用）

---

## 五、配置注入接口

gongkong 向 gongcheng 提供以下配置注入点（对应第一章工作类型表的"项目配置"列）：

| gongcheng 工作类型 | 注入的 config.yaml 字段 |
|---------------------|-------------------------|
| 代码修改/提交/部署 | `git.repositories` + `ssh` + `deploy` |
| 记忆/交接 | `memory.db_path` |
| SSH/部署 | `ssh` + `deploy.remote_root` + `deploy.remote_ps1` |
| 改动前影响检查 | `high_risk_files` |
| 远程执行兜底（可选） | `remote_execution.url` |
| 任务派发（可选） | `task_dispatch.url` |

---

## 六、错误处理

### config.yaml 不存在
- 报错：`config.yaml 不存在，请创建（参考 SKILL.md 的 schema）`
- 不继续执行任何项目操作

### config.yaml 语法错误
- 报错：`config.yaml 语法错误：<行号>: <错误详情>`
- 不继续执行

### 必填字段缺失
- 报错：`config.yaml 缺少必填字段：<字段名>`
- 列出所有缺失字段后停止

### 字段值非法
- 报错：`config.yaml 字段 <字段名> 值非法：<原因>`
- 如 `ssh.port` 不是数字、`git.repositories` 为空数组等

---

## 七、初始化新项目

新项目接入 gongkong 的步骤：

1. 复制本目录（gongkong/）到新项目的 `.trae/skills/gongkong/`
2. 编辑 `config.yaml`，按 schema 填写项目专属配置
3. 确保 `~/.ssh/config` 已配置 `ssh.alias`
4. 确保 `git.repositories[].local_path` 目录存在并可写
5. 如需远程执行兜底/任务派发，配置可选扩展字段 `remote_execution.url` / `task_dispatch.url`
6. 测试：加载 gongcheng → gongkong，确认配置注入成功

---

## 八、与原 projectmanagement 的关系

gongkong 是原 projectmanagement 拆分出的项目专属层：

| 原 projectmanagement 内容 | 去向 |
|----------------------------|------|
| 强制规则框架、8 种工作类型表 | → gongcheng（通用） |
| Git 核心原则、commit 规范、回滚 | → gongcheng（通用） |
| 工作流骨架、扩展指南 | → gongcheng（通用） |
| 服务器地址 your.server.ip | → gongkong/config.yaml 的 `ssh.host` |
| Gitea 地址 https://your-gitea.example.com | → gongkong/config.yaml 的 `git.gitea_url` |
| 三仓库结构（server-code/config/web） | → gongkong/config.yaml 的 `git.repositories` |
| remote.ps1 配置 | → gongkong/config.yaml 的 `deploy` |
| 项目关键词映射（你的项目名→server-code 等） | → gongkong/config.yaml（可选扩展字段） |
| 前端部署架构（Nginx alias 软链） | → gongkong/config.yaml（可选扩展字段） |
| aibuddys URL 等远程执行/任务派发通道 | → gongkong/config.yaml 的可选扩展字段 `remote_execution.url` / `task_dispatch.url` |
| MemBridge 知识库路径 | → gongkong/config.yaml 的 `memory.db_path` |
