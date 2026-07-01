#!/usr/bin/env python3
"""
AI 项目知识库查询脚本 v2

用法：
    # 自然语言查询
    python query_db.py <db路径> "用户创建 token 的流程"

    # SQL 直传（AI 专用）
    python query_db.py <db路径> --sql "SELECT name, responsibility FROM modules WHERE layer='billing'"

    # 指定输出格式
    python query_db.py <db路径> "列出所有 API" --format json|table|md

AI 查询优先级：
    1. --sql 模式：直接执行 SQL
    2. 自然语言匹配：预定义模式 → SQL
    3. 全文搜索：多表 LIKE
"""

import sqlite3
import argparse
import json
import sys
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# =============================================================================
# 自然语言 → SQL 映射
# =============================================================================

QUERY_PATTERNS = [
    # 项目信息
    ("项目介绍|项目概述|项目简介|meta", "SELECT key, value FROM meta"),

    # 循环/变更相关（新增）
    ("(?:这次|本次|最近).*(?:循环|改了什么|变更|变化)",
     "SELECT timestamp, module, change_type, description, author FROM change_log ORDER BY id DESC LIMIT 10"),
    ("(?:哪些|所有).*(?:变更|change_log|修改记录)",
     "SELECT timestamp, module, symbol, change_type, description, author FROM change_log ORDER BY id DESC LIMIT 20"),
    ("(?:哪些|哪个).*(?:函数|符号|symbol).*(?:修改|变更|改动)",
     "SELECT DISTINCT s.name, s.signature, s.module_id FROM symbols s JOIN change_log c ON s.module_id = c.module ORDER BY s.name"),
    ("(?:审查|review|检查).*(?:约束|红线|forbidden)",
     "SELECT rule, severity, affected_modules, source_location FROM constraints WHERE severity IN ('forbidden', 'critical')"),

    # 模块
    ("所有模块|模块列表|有哪些模块",
     "SELECT name, layer, responsibility FROM modules ORDER BY layer, name"),
    ("(?:(\w+)\s+)?.*模块.*(?:详情|信息|介绍)",
     "SELECT name, layer, responsibility, entry_func, file_path, notes FROM modules WHERE name LIKE '%{keyword}%'"),
    ("(?:哪些|所有)\s*(\w+)\s*层.*模块",
     "SELECT name, responsibility FROM modules WHERE layer = '{keyword}'"),

    # 符号/函数
    ("(?:函数|符号).*列表|所有函数",
     "SELECT name, signature, role FROM symbols ORDER BY role, name"),
    ("(?:函数|符号)\s+(\w+)",
     "SELECT name, signature, role, receiver, params, returns, line_number FROM symbols WHERE name LIKE '%{keyword}%'"),

    # API 路由
    ("(?:所有|哪些|列出).*api|api.*路由|接口.*列表",
     "SELECT method, path, handler, auth, group_name FROM api_routes ORDER BY method, path"),
    ("需要认证|需要登录|auth.*api",
     "SELECT method, path, handler FROM api_routes WHERE auth != 'none'"),
    ("(?:admin|管理).*api",
     "SELECT method, path, handler, auth FROM api_routes WHERE group_name = 'admin'"),
    ("(?:proxy|代理|v1).*api",
     "SELECT method, path, handler FROM api_routes WHERE group_name = 'proxy'"),
    ("(?:用户|user).*api",
     "SELECT method, path, handler FROM api_routes WHERE group_name = 'user'"),
    ("(POST|GET|PUT|DELETE|PATCH).*(?:api|路由)",
     "SELECT method, path, handler FROM api_routes WHERE method = '{keyword}'"),
    ("(?:路径|path)\s+(/\S+)",
     "SELECT method, path, handler, auth FROM api_routes WHERE path LIKE '%{keyword}%'"),

    # 数据库表
    ("(?:哪些|所有).*(?:表|table)|(?:表|table).*(?:列表|结构)",
     "SELECT name, prefix, purpose FROM tables ORDER BY name"),
    ("(?:表|table)\s+(\w+)",
     "SELECT name, purpose, fields, relations FROM tables WHERE name LIKE '%{keyword}%'"),

    # 决策
    ("(?:所有|哪些).*(?:决策|adr|决定)|adr.*列表",
     "SELECT code, title, status, source_file FROM decisions ORDER BY code"),
    ("adr[-\s]*(\d+)",
     "SELECT code, title, context, decision, consequences, risks, mitigations, status FROM decisions WHERE code LIKE '%ADR-{keyword}%'"),
    ("(?:已采纳|accepted).*决策",
     "SELECT code, title FROM decisions WHERE status = 'accepted'"),

    # 约束
    ("(?:所有|哪些).*(?:约束|constraint)|约束.*列表",
     "SELECT category, rule, severity, affected_modules, source_location FROM constraints ORDER BY severity, category"),
    ("(?:forbidden|禁止|绝对不能).*约束",
     "SELECT rule, severity, affected_modules FROM constraints WHERE severity = 'forbidden'"),
    ("(?:critical|关键|严重).*约束",
     "SELECT rule, severity, affected_modules FROM constraints WHERE severity = 'critical'"),
    ("(\w+).*(?:约束|constraint)",
     "SELECT category, rule, severity FROM constraints WHERE affected_modules LIKE '%{keyword}%' OR rule LIKE '%{keyword}%'"),

    # 配置
    ("(?:所有|哪些).*(?:配置|config)|配置.*列表",
     "SELECT scope, key, value, type, description, source FROM config"),
    ("(\w+).*配置",
     "SELECT scope, key, value, description FROM config WHERE key LIKE '%{keyword}%' OR scope = '{keyword}'"),

    # 统计
    ("(?:统计|统计信息|summary|count|多少)",
     """
     SELECT 'modules' as item, COUNT(*) as count FROM modules
     UNION ALL SELECT 'symbols', COUNT(*) FROM symbols
     UNION ALL SELECT 'api_routes', COUNT(*) FROM api_routes
     UNION ALL SELECT 'tables', COUNT(*) FROM tables
     UNION ALL SELECT 'decisions', COUNT(*) FROM decisions
     UNION ALL SELECT 'constraints', COUNT(*) FROM constraints
     UNION ALL SELECT 'config', COUNT(*) FROM config
     """),

    # schema（数据库全貌）
    ("schema|数据库.*全貌|全部.*表结构",
     "SELECT name, purpose FROM tables ORDER BY name"),
]


# =============================================================================
# 格式化输出
# =============================================================================

def format_table(rows: List[tuple], columns: List[str]) -> str:
    """ASCII 表格输出"""
    if not rows:
        return "（无数据）"

    widths = [len(str(c)) for c in columns]
    for row in rows:
        for i, val in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(str(val) if val is not None else ""))

    header = " | ".join(str(c).ljust(widths[i]) for i, c in enumerate(columns))
    separator = "-+-".join("-" * w for w in widths)

    lines = [header, separator]
    for row in rows:
        line = " | ".join(str(row[i] if i < len(row) else "").ljust(widths[i]) for i in range(len(columns)))
        lines.append(line)

    return "\n".join(lines)


def format_json(rows: List[tuple], columns: List[str]) -> str:
    """JSON 输出"""
    result = []
    for row in rows:
        obj = {}
        for i, col in enumerate(columns):
            obj[col] = row[i] if i < len(row) else None
        result.append(obj)
    return json.dumps(result, ensure_ascii=False, indent=2)


def format_markdown(rows: List[tuple], columns: List[str]) -> str:
    """Markdown 表格输出"""
    if not rows:
        return "（无数据）"

    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"

    lines = [header, separator]
    for row in rows:
        line = "| " + " | ".join(str(v) if v is not None else "" for v in row) + " |"
        lines.append(line)

    return "\n".join(lines)


# =============================================================================
# 查询执行
# =============================================================================

def match_natural_query(query: str) -> Optional[str]:
    """自然语言匹配 → SQL"""
    query_stripped = query.strip()

    for pattern, sql in QUERY_PATTERNS:
        match = re.search(pattern, query_stripped, re.IGNORECASE)
        if match:
            # 提取关键词
            keyword = ""
            if match.lastindex and match.lastindex >= 1:
                keyword = match.group(1) or match.group(0)

            # 清理关键词
            keyword = keyword.strip().replace('"', '').replace("'", "")

            # 替换占位符
            if "{keyword}" in sql:
                return sql.replace("{keyword}", keyword)
            return sql

    return None


def execute_sql_query(conn: sqlite3.Connection, sql: str) -> Tuple[List[str], List[tuple]]:
    """执行 SQL，返回列名和数据行"""
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        columns = [d[0] for d in cursor.description]
        rows = cursor.fetchall()
        return columns, rows
    except sqlite3.Error as e:
        return ["error"], [(str(e),)]


def execute_search(conn: sqlite3.Connection, query: str) -> List[Tuple[str, List[str], List[tuple]]]:
    """多表全文搜索"""
    search_pattern = f"%{query}%"
    results = []

    searches = [
        ("modules", ["name", "layer", "responsibility"]),
        ("symbols", ["name", "signature", "role"]),
        ("api_routes", ["method", "path", "handler"]),
        ("tables", ["name", "purpose"]),
        ("decisions", ["code", "title", "decision"]),
        ("constraints", ["rule", "severity"]),
        ("config", ["key", "description"]),
    ]

    for table, cols in searches:
        col_names = ", ".join(cols)
        conditions = " OR ".join(f"{c} LIKE ?" for c in cols)
        sql = f"SELECT {col_names} FROM {table} WHERE {conditions} LIMIT 10"
        params = [search_pattern] * len(cols)

        try:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            if rows:
                results.append((table, cols, rows))
        except sqlite3.Error:
            continue

    return results


def execute_query(db_path: str, query: str = None, sql: str = None,
                  output_format: str = "table") -> str:
    """执行查询"""
    conn = sqlite3.connect(db_path)
    output_parts = []

    if sql:
        # SQL 直传模式
        columns, rows = execute_sql_query(conn, sql)
        if columns == ["error"]:
            conn.close()
            return f"SQL 错误: {rows[0][0]}"
        output_parts.append(format_output(rows, columns, output_format))

    elif query:
        query_stripped = query.strip()

        # 尝试自然语言匹配
        matched_sql = match_natural_query(query_stripped)

        if matched_sql:
            columns, rows = execute_sql_query(conn, matched_sql)
            if columns == ["error"]:
                conn.close()
                return f"SQL 错误: {rows[0][0]}"
            output_parts.append(format_output(rows, columns, output_format))
        else:
            # 全文搜索
            search_results = execute_search(conn, query_stripped)
            if not search_results:
                conn.close()
                return f"未找到与「{query_stripped}」相关的内容\n\n提示: 使用 --sql 模式直接执行 SQL 查询"

            for table_name, cols, rows in search_results:
                output_parts.append(f"\n## {table_name}\n")
                output_parts.append(format_output(rows, cols, output_format))

    conn.close()
    return "\n".join(output_parts)


def format_output(rows: List[tuple], columns: List[str], fmt: str) -> str:
    """格式化输出"""
    if fmt == "json":
        return format_json(rows, columns)
    elif fmt == "md":
        return format_markdown(rows, columns)
    else:
        return format_table(rows, columns)


# =============================================================================
# 主流程
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="查询 AI 项目知识库 v2")
    parser.add_argument("db_path", nargs="?", help="数据库路径")
    parser.add_argument("query", nargs="?", help="自然语言查询")
    parser.add_argument("--sql", "-s", help="直接执行 SQL")
    parser.add_argument("--format", "-f", choices=["table", "json", "md"],
                        default="table", help="输出格式")
    parser.add_argument("--list-tables", action="store_true", help="列出所有表")
    args = parser.parse_args()

    if not args.db_path:
        # 尝试在当前目录或 .ai/ 下查找
        for candidate in [Path("*.ai.db"), Path(".ai/*.ai.db")]:
            matches = list(Path(".").glob(candidate.name if candidate.name != "*.ai.db" else "*.ai.db"))
            # 手动查找
            pass

        # 查找 .ai 目录下的 .db 文件
        ai_dir = Path(".ai")
        if ai_dir.exists():
            db_files = list(ai_dir.glob("*.db"))
            if db_files:
                args.db_path = str(db_files[0])

        if not args.db_path:
            print("错误: 未指定数据库路径")
            print("用法: python query_db.py <db路径> [查询] [--sql 'SQL'] [--format json|table|md]")
            sys.exit(1)

    db_path = Path(args.db_path)
    if not db_path.exists():
        print(f"错误: 数据库不存在 {db_path}")
        sys.exit(1)

    if args.list_tables:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        conn.close()
        print("可用表:")
        for (name,) in tables:
            if name.startswith("sqlite_"):
                continue
            cursor2 = sqlite3.connect(str(db_path)).cursor()
            cursor2.execute(f"SELECT COUNT(*) FROM {name}")
            count = cursor2.fetchone()[0]
            print(f"  {name} ({count} 条)")
        sys.exit(0)

    if args.sql:
        result = execute_query(str(db_path), sql=args.sql, output_format=args.format)
    elif args.query:
        result = execute_query(str(db_path), query=args.query, output_format=args.format)
    else:
        print("请提供查询内容或使用 --sql 参数")
        print("示例:")
        print('  python query_db.py "所有模块"')
        print('  python query_db.py --sql "SELECT name FROM modules"')
        sys.exit(0)

    print(result)


if __name__ == "__main__":
    main()
