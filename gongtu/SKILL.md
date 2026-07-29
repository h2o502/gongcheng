---
slug: gongtu
displayName: 工图
version: 1.3.0
summary: 把 PlantUML/Mermaid/D2/Graphviz 等 27 种图源码渲染成 SVG/PNG/PDF 图片。
license: MIT
name: gongtu
description: |
  工图 (gongtu) — 把 PlantUML/Mermaid/D2/Graphviz 等 27 种图源码渲染成 SVG/PNG/PDF 图片。
  当用户要求"画图/渲染架构图/生成流程图/转 SVG/画类图/画时序图"时触发。
---

# 工图 (gongtu) — Diagram Renderer Skill

> 原 diagram skill，"工"字系列通用 skill。
> 把文本图描述语言(PlantUML/Mermaid/D2 等 27 种)渲染成 SVG/PNG/PDF 图片。

## 何时触发

- 用户说"画一张 X 架构图"
- 用户说"把这段 PlantUML 渲染成 SVG"
- 用户说"生成流程图/类图/时序图/部署图"
- 用户说"转 SVG / 转 PNG"
- 用户在 markdown 里写了 PlantUML/Mermaid 代码块,想要看图

## 依赖

- **Kroki**(MIT 协议,https://kroki.io)
- 默认用公网 Kroki,**无需任何安装**,开箱即用
- 生产环境建议自部署:运行 `bash install.sh` 一键启动 Docker Kroki

## 配置

环境变量 `KROKI_ENDPOINT`,默认 `https://kroki.io`。
自部署后改成 `http://localhost:8000`:

```bash
export KROKI_ENDPOINT=http://localhost:8000
```

## 工作流

1. Claude 产出图源码(PlantUML/Mermaid/D2/Graphviz...)
2. 写入源文件,路径建议 `docs/diagrams/<name>.puml`(或 `.mmd` / `.d2`)
3. 调用 `render.sh` 渲染:
   ```bash
   bash skills/gongtu/render.sh plantuml docs/diagrams/arch.puml docs/diagrams/arch.svg
   ```
4. 在 markdown 里嵌入:
   ```markdown
   ![架构图](./docs/diagrams/arch.svg)
   ```
5. **源码和 SVG 都提交 git**:
   - `.puml` 源码是主,AI 可读可改,git diff 友好
   - `.svg` 是渲染产物,可一并提交方便他人查看

## 支持的图类型(27 种)

| 常用 | PlantUML / Mermaid / D2 / Graphviz / C4-PlantUML / Excalidraw |
|---|---|
| UML | PlantUML(类图/组件图/时序图/部署图/用例图) |
| 架构 | D2 / Structurizr / C4-PlantUML |
| 流程 | Mermaid / Graphviz / BlockDiag |
| 其他 | BPMN / DBML / TikZ / Vega / Vega-Lite / WireViz ... |

完整列表见 https://kroki.io

## 输出格式

`svg`(默认,矢量,推荐)/ `png` / `jpeg` / `pdf`

## render.sh 用法

```bash
# 标准用法
bash render.sh <type> <input> <output> [format]

# 示例
bash render.sh plantuml arch.puml arch.svg
bash render.sh mermaid flow.mmd flow.png
bash render.sh d2 system.d2 system.svg
bash render.sh graphviz deps.dot deps.pdf
```

## 关键设计原则

1. **源码优先**:`.puml`/`.mmd` 文件是 source of truth,SVG 是产物。改图改源码,不直接改 SVG。
2. **git 友好**:源码是文本,`git diff` 直观。SVG 也可提交,方便不装渲染器的人看图。
3. **AI 可读**:AI 读源码理解结构,不需要看渲染后的图。
4. **后端可换**:默认公网 Kroki,可自部署,可降级到本地 plantuml.jar。
5. **不锁定**:Kroki 是 MIT 协议,永不消失,自部署完全可控。

## 自部署 Kroki(可选,推荐生产)

```bash
bash skills/gongtu/install.sh
export KROKI_ENDPOINT=http://localhost:8000
```

自部署后:
- 完全离线可用
- 无 rate limit
- 0 延迟(< 0.5 秒渲染)
- 数据不外传

## 与其他工字 skill 的协作

- **gongcheng**：gongtu 是 gongcheng 工作类型表第 9 行（画图/渲染）的执行 skill
- **gongsheji**：设计阶段产出的架构图源码可由 gongtu 渲染成 SVG
- **gongyi**：知识库中的架构文档可嵌入 gongtu 渲染的 SVG

## 故障排查

- **渲染失败**:检查源码语法,PlantUML 必须 `@startuml` 开头 `@enduml` 结尾
- **网络错误**:公网 Kroki 不通时,自部署或检查网络
- **中文乱码**:PlantUML 默认支持中文,无需特殊处理
- **图太大**:复杂图渲染慢,可自部署提升速度
