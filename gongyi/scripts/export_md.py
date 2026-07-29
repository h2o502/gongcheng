#!/usr/bin/env python3
"""
AI 项目知识库 — Markdown 导出脚本

用法：
    python export_md.py <db路径> [--output <输出路径>] [--include-diagrams] [--toc]

功能：
    从 SQLite 知识库导出完整的 Markdown 交接文档。
    适合人类阅读、新人上手、跨 session/agent/团队交接。
"""

import sqlite3
import json
import argparse
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple

# =============================================================================
# Markdown 生成器
# =============================================================================

class MarkdownExporter:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.meta = {}
        self._load_meta()

    def _load_meta(self):
        cursor = self.conn.cursor()
        for row in cursor.execute("SELECT key, value FROM meta"):
            self.meta[row[0]] = row[1]

    def close(self):
        self.conn.close()

    def export(self, include_diagrams: bool = True, include_toc: bool = True) -> str:
        """导出完整 Markdown"""
        sections = []

        # Header
        sections.append(self._header())

        if include_toc:
            sections.append(self._toc())

        sections.append(self._section_overview())
        if include_diagrams:
            sections.append(self._section_architecture())
        sections.append(self._section_api_routes())
        if include_diagrams:
            sections.append(self._section_database())
        else:
            sections.append(self._section_database_simple())
        sections.append(self._section_modules())
        sections.append(self._section_symbols())
        sections.append(self._section_decisions())
        sections.append(self._section_constraints())
        sections.append(self._section_config())
        sections.append(self._section_change_log())

        sections.append(self._footer())

        return "\n\n".join(sections)

    # --- Sections ---

    def _header(self) -> str:
        name = self.meta.get("name", "Project")
        version = self.meta.get("version", "?")
        generated = datetime.now().strftime("%Y-%m-%d %H:%M")
        language = self.meta.get("language", "?")
        framework = self.meta.get("framework", "?")

        return f"""# {name} 项目说明书

> 文档版本: {version} | 生成时间: {generated}
> 由 AI 项目知识库 v2 自动导出
> 语言: {language} | 框架: {framework}
>
> 本文档适合人类阅读、新人上手、跨 session/agent/团队交接。
> 如需查询精确信息，建议使用 `.ai/` 目录下的 SQLite 知识库。"""

    def _toc(self) -> str:
        toc_items = [
            "1. 项目概述",
            "2. 架构分层",
            "3. API 完整清单",
            "4. 数据库设计",
            "5. 核心模块",
            "6. 符号表（函数/结构体）",
            "7. 设计决策（ADR）",
            "8. 约束清单",
            "9. 配置项",
            "10. 变更日志",
        ]
        return "## 目录\n\n" + "\n".join(toc_items)

    def _section_overview(self) -> str:
        lines = ["## 01. 项目概述\n"]

        desc = self.meta.get("description", "")
        if desc:
            lines.append(f"> **{self.meta.get('name', 'Project')} = {desc}**\n")

        # 核心指标
        cursor = self.conn.cursor()
        total_modules = cursor.execute("SELECT COUNT(*) FROM modules").fetchone()[0]
        total_symbols = cursor.execute("SELECT COUNT(*) FROM symbols").fetchone()[0]
        total_routes = cursor.execute("SELECT COUNT(*) FROM api_routes").fetchone()[0]
        total_tables = cursor.execute("SELECT COUNT(*) FROM tables").fetchone()[0]
        total_decisions = cursor.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
        total_constraints = cursor.execute("SELECT COUNT(*) FROM constraints").fetchone()[0]

        lines.append("### 核心指标\n")
        lines.append("| 指标 | 值 |")
        lines.append("|------|-----|")
        lines.append(f"| 模块数 | {total_modules} |")
        lines.append(f"| 符号数（函数/结构体） | {total_symbols} |")
        lines.append(f"| API 路由数 | {total_routes} |")
        lines.append(f"| 数据库表数 | {total_tables} |")
        lines.append(f"| ADR 决策数 | {total_decisions} |")
        lines.append(f"| 约束数 | {total_constraints} |")

        # 元信息表
        lines.append("\n### 项目信息\n")
        lines.append("| 配置项 | 值 |")
        lines.append("|--------|-----|")
        for key in ["name", "language", "framework", "database", "port", "version", "entry_point", "description"]:
            if key in self.meta:
                lines.append(f"| {key} | {self.meta[key]} |")

        return "\n".join(lines)

    def _section_architecture(self) -> str:
        cursor = self.conn.cursor()
        modules = cursor.execute("SELECT name, layer, responsibility FROM modules ORDER BY layer, name").fetchall()

        if not modules:
            return "## 02. 架构分层\n\n（暂无模块数据）"

        lines = ["## 02. 架构分层\n"]

        # 按层分组
        layers = {}
        for name, layer, resp in modules:
            if layer not in layers:
                layers[layer] = []
            layers[layer].append((name, resp))

        # Mermaid 架构图
        lines.append("```mermaid")
        lines.append("flowchart TB")

        for layer, mods in sorted(layers.items()):
            lines.append(f"    subgraph {layer.upper()}[\"{layer.upper()} Layer\"]")
            for name, resp in mods:
                safe_name = name.replace("-", "_").replace(".", "_")
                lines.append(f"        {safe_name}[\"{name}\\n{resp[:40]}\"]")
            lines.append("    end")

        lines.append("```")

        # 模块说明
        lines.append("\n### 模块清单\n")
        lines.append("| 模块 | 层级 | 职责 |")
        lines.append("|------|------|------|")
        for name, layer, resp in modules:
            lines.append(f"| {name} | {layer} | {resp} |")

        return "\n".join(lines)

    def _section_api_routes(self) -> str:
        cursor = self.conn.cursor()
        routes = cursor.execute(
            "SELECT method, path, handler, auth, group_name FROM api_routes ORDER BY group_name, method, path"
        ).fetchall()

        if not routes:
            return "## 03. API 完整清单\n\n（暂无 API 数据）"

        lines = ["## 03. API 完整清单\n"]

        # 按分组输出
        current_group = None
        for method, path, handler, auth, group in routes:
            if group != current_group:
                current_group = group
                group_label = group.upper() if group else "OTHER"
                lines.append(f"\n### {group_label}\n")
                lines.append("| 方法 | 路径 | 处理器 | 认证 |")
                lines.append("|------|------|--------|------|")

            auth_label = auth if auth else "none"
            lines.append(f"| {method} | `{path}` | {handler} | {auth_label} |")

        return "\n".join(lines)

    def _section_database(self) -> str:
        cursor = self.conn.cursor()
        tables = cursor.execute("SELECT name, prefix, purpose, fields, relations, primary_key FROM tables ORDER BY name").fetchall()

        if not tables:
            return "## 04. 数据库设计\n\n（暂无数据库数据）"

        lines = ["## 04. 数据库设计\n"]

        # ER Diagram
        lines.append("### ER 图\n")
        lines.append("```mermaid")
        lines.append("erDiagram")
        for table in tables:
            safe_name = table[0].replace("-", "_")
            lines.append(f"    {safe_name} {{")
            try:
                fields = json.loads(table[3]) if table[3] else []
                for f in fields[:5]:  # 最多显示5个字段
                    ftype = f.get("type", "text")
                    fpk = "PK" if f.get("pk") else ""
                    lines.append(f"        {ftype} {f['name']} {fpk}")
            except (json.JSONDecodeError, TypeError):
                pass
            lines.append("    }")
        lines.append("```\n")

        # 每张表的详细字段
        for table in tables:
            name, prefix, purpose, fields_json, relations, pk = table
            lines.append(f"\n### {name}\n")
            if purpose:
                lines.append(f"**用途**: {purpose}\n")

            try:
                fields = json.loads(fields_json) if fields_json else []
            except (json.JSONDecodeError, TypeError):
                fields = []

            if fields:
                lines.append("| 字段 | 类型 | 说明 |")
                lines.append("|------|------|------|")
                for f in fields:
                    ftype = f.get("type", "text")
                    comment = f.get("comment", "")
                    pk_mark = " (PK)" if f.get("pk") else ""
                    null_mark = " (NOT NULL)" if not f.get("null", True) else ""
                    lines.append(f"| {f['name']}{pk_mark} | {ftype} | {comment}{null_mark} |")

            if relations:
                lines.append(f"\n**关系**: {relations}\n")

        return "\n".join(lines)

    def _section_database_simple(self) -> str:
        """不包含 Mermaid ER 图的简化版数据库章节"""
        cursor = self.conn.cursor()
        tables = cursor.execute("SELECT name, prefix, purpose, fields FROM tables ORDER BY name").fetchall()

        if not tables:
            return "## 04. 数据库设计\n\n（暂无数据库数据）"

        lines = ["## 04. 数据库设计\n"]
        lines.append("| 表名 | 用途 | 主要字段 |")
        lines.append("|------|------|---------|")

        for name, prefix, purpose, fields_json in tables:
            try:
                fields = json.loads(fields_json) if fields_json else []
                field_names = ", ".join(f['name'] for f in fields[:6])
            except (json.JSONDecodeError, TypeError):
                field_names = ""

            prefix_str = f"({prefix}_)" if prefix else ""
            lines.append(f"| {name} {prefix_str}| {purpose} | {field_names} |")

        return "\n".join(lines)

    def _section_modules(self) -> str:
        cursor = self.conn.cursor()
        modules = cursor.execute(
            "SELECT name, layer, responsibility, entry_func, notes FROM modules ORDER BY layer, name"
        ).fetchall()

        if not modules:
            return "## 05. 核心模块\n\n（暂无模块数据）"

        lines = ["## 05. 核心模块\n"]

        current_layer = None
        for name, layer, resp, entry_func, notes in modules:
            if layer != current_layer:
                current_layer = layer
                lines.append(f"\n### {layer.upper()} 层\n")

            lines.append(f"#### {name}\n")
            lines.append(f"- **职责**: {resp}")
            if entry_func:
                lines.append(f"- **入口函数**: `{entry_func}()`")
            if notes:
                lines.append(f"- **备注**: {notes}")
            lines.append("")

        return "\n".join(lines)

    def _section_symbols(self) -> str:
        cursor = self.conn.cursor()

        # 按角色分组统计
        role_counts = cursor.execute(
            "SELECT role, COUNT(*) as cnt FROM symbols GROUP BY role ORDER BY cnt DESC"
        ).fetchall()

        if not role_counts:
            return "## 06. 符号表\n\n（暂无符号数据）"

        lines = ["## 06. 符号表（函数/结构体）\n"]

        lines.append("### 统计\n")
        lines.append("| 类型 | 数量 |")
        lines.append("|------|------|")
        for role, count in role_counts:
            lines.append(f"| {role} | {count} |")

        # 列出核心函数（有 receiver 的方法优先）
        methods = cursor.execute(
            "SELECT name, signature, receiver FROM symbols WHERE role='function' AND receiver IS NOT NULL ORDER BY receiver, name LIMIT 50"
        ).fetchall()

        if methods:
            lines.append("\n### 核心方法\n")
            lines.append("| 方法 | 签名 | 接收者 |")
            lines.append("|------|------|--------|")
            for name, sig, receiver in methods:
                lines.append(f"| `{name}` | `{sig}` | `{receiver}` |")

        return "\n".join(lines)

    def _section_decisions(self) -> str:
        cursor = self.conn.cursor()
        decisions = cursor.execute(
            "SELECT code, title, context, decision, consequences, risks, mitigations, status FROM decisions ORDER BY code"
        ).fetchall()

        if not decisions:
            return "## 07. 设计决策（ADR）\n\n（暂无决策数据）"

        lines = ["## 07. 设计决策（ADR）\n"]

        for code, title, context, decision, consequences, risks, mitigations, status in decisions:
            lines.append(f"\n### {code}: {title}\n")
            lines.append(f"**状态**: {status}\n")
            if context:
                lines.append(f"**背景**: {context}\n")
            if decision:
                lines.append(f"**决策**: {decision}\n")
            if consequences:
                lines.append(f"**后果**: {consequences}\n")
            if risks:
                lines.append(f"**风险**: {risks}\n")
            if mitigations:
                lines.append(f"**缓解措施**: {mitigations}\n")

        return "\n".join(lines)

    def _section_constraints(self) -> str:
        cursor = self.conn.cursor()
        constraints = cursor.execute(
            "SELECT category, rule, severity, affected_modules, source_location FROM constraints ORDER BY severity, category"
        ).fetchall()

        if not constraints:
            return "## 08. 约束清单\n\n（暂无约束数据）"

        lines = ["## 08. 约束清单\n"]

        # 按严重度分组
        severity_order = {"forbidden": 0, "critical": 1, "warning": 2, "info": 3}

        # forbidden
        forbidden = [c for c in constraints if c[2] == "forbidden"]
        if forbidden:
            lines.append("\n### 禁止操作（FORBIDDEN）\n")
            lines.append("以下规则不可违反，否则会导致数据损坏或安全漏洞。\n")
            lines.append("| 规则 | 类别 | 影响模块 |")
            lines.append("|------|------|---------|")
            for cat, rule, sev, affected, loc in forbidden:
                lines.append(f"| {rule} | {cat} | {affected} |")

        # critical
        critical = [c for c in constraints if c[2] == "critical"]
        if critical:
            lines.append("\n### 关键规则（CRITICAL）\n")
            lines.append("以下规则必须遵循，否则会导致行为不正确。\n")
            lines.append("| 规则 | 类别 | 影响模块 |")
            lines.append("|------|------|---------|")
            for cat, rule, sev, affected, loc in critical:
                lines.append(f"| {rule} | {cat} | {affected} |")

        # warning
        warning = [c for c in constraints if c[2] == "warning"]
        if warning:
            lines.append("\n### 警告（WARNING）\n")
            lines.append("| 规则 | 类别 |")
            lines.append("|------|------|")
            for cat, rule, sev, affected, loc in warning:
                lines.append(f"| {rule} | {cat} |")

        # info
        info = [c for c in constraints if c[2] == "info"]
        if info:
            lines.append("\n### 参考信息（INFO）\n")
            lines.append("| 规则 | 类别 |")
            lines.append("|------|------|")
            for cat, rule, sev, affected, loc in info:
                lines.append(f"| {rule} | {cat} |")

        return "\n".join(lines)

    def _section_config(self) -> str:
        cursor = self.conn.cursor()
        configs = cursor.execute(
            "SELECT scope, key, value, type, description, source FROM config ORDER BY scope, key"
        ).fetchall()

        if not configs:
            return "## 09. 配置项\n\n（暂无配置数据）"

        lines = ["## 09. 配置项\n"]

        current_scope = None
        for scope, key, value, type_, desc, source in configs:
            if scope != current_scope:
                current_scope = scope
                lines.append(f"\n### {scope}\n")
                lines.append("| 键 | 值 | 类型 | 说明 | 来源 |")
                lines.append("|-----|-----|------|------|------|")

            value_display = value if value else "（空）"
            if type_ == "secret":
                value_display = "***"
            lines.append(f"| `{key}` | {value_display} | {type_} | {desc} | {source} |")

        return "\n".join(lines)

    def _section_change_log(self) -> str:
        cursor = self.conn.cursor()
        changes = cursor.execute(
            "SELECT timestamp, module, symbol, change_type, description, author FROM change_log ORDER BY timestamp DESC LIMIT 50"
        ).fetchall()

        if not changes:
            return "## 10. 变更日志\n\n（暂无变更记录）"

        lines = ["## 10. 变更日志\n"]
        lines.append("| 时间 | 模块 | 符号 | 变更类型 | 描述 | 操作者 |")
        lines.append("|------|------|------|---------|------|--------|")
        for ts, module, symbol, change_type, desc, author in changes:
            lines.append(f"| {ts} | {module} | {symbol} | {change_type} | {desc} | {author} |")

        return "\n".join(lines)

    def _footer(self) -> str:
        generated = datetime.now().strftime("%Y-%m-%d %H:%M")
        return f"""\n---\n\n> 本文档由 AI 项目知识库 v2 自动导出\n> 导出时间: {generated}\n> 如需更新，请运行: `python build_db.py <项目路径> --incremental`\n> 然后运行: `python export_md.py .ai/*.ai.db --output docs/PROJECT_SPEC.md`"""


# =============================================================================
# 主流程
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="导出 AI 项目知识库为 Markdown")
    parser.add_argument("db_path", help="数据库路径")
    parser.add_argument("--output", "-o", help="输出文件路径")
    parser.add_argument("--no-diagrams", action="store_true", help="不包含 Mermaid 图表")
    parser.add_argument("--no-toc", action="store_true", help="不包含目录")
    parser.add_argument("--diff", action="store_true", help="只导出最近变更摘要（diff 模式）")
    parser.add_argument("--review", action="store_true", help="导出人类审查清单（handoff 模式）")
    parser.add_argument("--limit", type=int, default=20, help="变更条数限制（diff 模式）")
    args = parser.parse_args()

    db_path = Path(args.db_path)
    if not db_path.exists():
        print(f"错误: 数据库不存在 {db_path}")
        sys.exit(1)

    # 自动确定输出路径
    if args.output:
        output_path = Path(args.output)
    elif args.diff:
        output_path = Path("CHANGELOG.md")
    elif args.review:
        output_path = Path("REVIEW.md")
    else:
        output_path = Path("PROJECT_SPEC.md")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    if args.diff:
        content = export_diff(conn, limit=args.limit)
    elif args.review:
        content = export_review_checklist(conn)
    else:
        exporter = MarkdownExporter(str(db_path))
        content = exporter.export(
            include_diagrams=not args.no_diagrams,
            include_toc=not args.no_toc,
        )
        exporter.close()

    conn.close()

    output_path.write_text(content, encoding="utf-8")
    print(f"导出完成: {output_path}")
    print(f"文件大小: {output_path.stat().st_size / 1024:.1f} KB")


def export_diff(conn: sqlite3.Connection, limit: int = 20) -> str:
    """导出最近变更摘要（diff 模式）"""
    cursor = conn.cursor()

    # 获取项目名
    meta = {}
    for row in cursor.execute("SELECT key, value FROM meta WHERE key NOT LIKE 'filehash:%'"):
        meta[row[0]] = row[1]

    # 获取最近变更
    changes = cursor.execute(
        "SELECT timestamp, module, symbol, change_type, description, author FROM change_log ORDER BY id DESC LIMIT ?",
        (limit,)
    ).fetchall()

    # 统计
    stats = cursor.execute("""
        SELECT change_type, COUNT(*) as cnt
        FROM change_log
        GROUP BY change_type
        ORDER BY cnt DESC
    """).fetchall()

    lines = [
        f"# {meta.get('name', 'Project')} — 变更摘要",
        "",
        f"> 导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"> 显示最近 {len(changes)} 条变更",
        "",
        "## 变更统计\n",
        "| 类型 | 数量 |",
        "|------|------|",
    ]
    for change_type, count in stats:
        lines.append(f"| {change_type} | {count} |")

    lines.append("\n## 详细变更\n")
    lines.append("| 时间 | 模块 | 符号 | 类型 | 描述 | 操作者 |")
    lines.append("|------|------|------|------|------|--------|")

    for ts, module, symbol, change_type, desc, author in changes:
        short_ts = ts[:16].replace('T', ' ') if 'T' in ts else ts[:16]
        lines.append(f"| {short_ts} | {module} | {symbol} | {change_type} | {desc} | {author} |")

    # 检查是否有违反约束的变更
    forbidden_changes = cursor.execute("""
        SELECT cl.timestamp, cl.module, cl.description
        FROM change_log cl
        JOIN constraints c ON cl.module = c.affected_modules OR cl.description LIKE '%' || c.rule || '%'
        WHERE c.severity = 'forbidden'
        ORDER BY cl.id DESC LIMIT 5
    """).fetchall()

    if forbidden_changes:
        lines.append("\n## 警告：可能违反约束\n")
        lines.append("以下变更可能触及了 forbidden 级别的约束，请人工审查。\n")
        for ts, module, desc in forbidden_changes:
            lines.append(f"- [{ts[:16]}] {module}: {desc}")

    lines.append(f"\n---\n> 完整文档请运行: `python export_md.py {db_path.name}`")

    return "\n".join(lines)


def export_review_checklist(conn: sqlite3.Connection) -> str:
    """导出人类审查清单（handoff 模式）"""
    cursor = conn.cursor()

    meta = {}
    for row in cursor.execute("SELECT key, value FROM meta WHERE key NOT LIKE 'filehash:%'"):
        meta[row[0]] = row[1]

    # 获取最近变更
    recent_changes = cursor.execute(
        "SELECT timestamp, module, symbol, change_type, description, author FROM change_log ORDER BY id DESC LIMIT 10"
    ).fetchall()

    # 获取受影响的模块
    affected_modules = set()
    for _, module, _, _, _, _ in recent_changes:
        if module:
            affected_modules.add(module)

    # 获取这些模块的约束
    constraints_query = "SELECT rule, severity, category FROM constraints WHERE severity IN ('forbidden', 'critical')"
    if affected_modules:
        # 简化：显示所有关键约束
        pass
    constraints = cursor.execute(constraints_query).fetchall()

    # 获取变更涉及的函数
    changed_symbols = []
    for _, module, symbol, _, _, _ in recent_changes:
        if symbol:
            rows = cursor.execute(
                "SELECT name, signature, role FROM symbols WHERE name = ?", (symbol,)
            ).fetchall()
            changed_symbols.extend(rows)

    lines = [
        f"# {meta.get('name', 'Project')} — 人类审查清单",
        "",
        f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"> 此清单由 AI 开发循环自动生成，供人类程序员快速审查。",
        "",
        "## 1. 本次循环概览\n",
        f"- **变更次数**: {len(recent_changes)}",
        f"- **涉及模块**: {', '.join(affected_modules) if affected_modules else '无'}",
        f"- **涉及函数**: {len(changed_symbols)}",
        "",
    ]

    if recent_changes:
        lines.append("### 变更列表\n")
        lines.append("| 时间 | 模块 | 类型 | 描述 | 操作者 |")
        lines.append("|------|------|------|------|--------|")
        for ts, module, symbol, change_type, desc, author in recent_changes:
            short_ts = ts[:16].replace('T', ' ') if 'T' in ts else ts[:16]
            lines.append(f"| {short_ts} | {module} | {change_type} | {desc} | {author} |")

    lines.append("\n## 2. 约束审查\n")
    lines.append("请确认以下关键约束未被违反：\n")
    for rule, severity, category in constraints:
        marker = "!" if severity == "forbidden" else "?"
        lines.append(f"- [{marker}] [{severity}] {rule}")

    lines.append("\n## 3. 变更影响面\n")
    if changed_symbols:
        lines.append("以下函数/符号被修改，请确认行为正确：\n")
        for name, sig, role in changed_symbols:
            lines.append(f"- `{sig}` ({role})")
    else:
        lines.append("（未检测到具体符号变更，请检查涉及的模块）")
        for m in affected_modules:
            lines.append(f"- 模块: {m}")

    lines.append("\n## 4. 审查确认\n")
    lines.append("- [ ] 所有 forbidden 约束未被违反")
    lines.append("- [ ] 变更的函数行为正确")
    lines.append("- [ ] 没有意外的副作用")
    lines.append("- [ ] 计费/安全相关链路未受影响（如适用）")
    lines.append("- [ ] 可以交还给 AI 继续开发")

    lines.append(f"\n---\n> 审查确认后，AI 可继续下一轮开发循环。")

    return "\n".join(lines)


if __name__ == "__main__":
    main()
