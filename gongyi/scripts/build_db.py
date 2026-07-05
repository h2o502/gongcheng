#!/usr/bin/env python3
"""
AI 项目知识库构建脚本 v2

用法：
    python build_db.py <项目路径> [--output <db路径>] [--incremental] [--force] [--context-only]

功能：
    1. 自动检测项目语言（Go/Python/JS/TS）
    2. 扫描源码文件，提取模块、符号、API 路由
    3. 解析数据库表定义和约束注释
    4. 收集 ADR 决策记录
    5. 构建/更新 SQLite 数据库
    6. 自动生成/更新 CONTEXT.md

输出：
    <项目路径>/.ai/project.ai.db
    <项目路径>/.ai/CONTEXT.md
"""

import os
import sys
import json
import sqlite3
import re
import argparse
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

# =============================================================================
# 配置
# =============================================================================

EXCLUDE_DIRS = {
    "vendor", "node_modules", ".git", ".venv", "venv", "__pycache__",
    "testdata", "migrations", "dist", "build", ".next", ".ai", "docs",
    ".qoderwork", ".workspace", ".trash",
}

EXCLUDE_FILES_PATTERNS = {
    "*_test.go", "*_test.py", "*.test.js", "*.test.ts", "*.test.tsx",
    "*.spec.js", "*.spec.ts", "*.spec.tsx",
    "*.pb.go", "*.gen.go", "*.pb.go",
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "go.sum", "go.mod",
}

# =============================================================================
# 语言检测
# =============================================================================

def detect_language(project_path: Path) -> str:
    """自动检测项目主要语言"""
    indicators = {
        "go": [project_path / "go.mod", project_path / "go.sum"],
        "python": [project_path / "requirements.txt", project_path / "pyproject.toml", project_path / "setup.py"],
        "javascript": [project_path / "package.json"],
        "typescript": [project_path / "tsconfig.json"],
    }

    # 先检查标志性文件
    for lang, files in indicators.items():
        for f in files:
            if f.exists():
                if lang in ("javascript", "typescript"):
                    # 进一步区分：有 tsconfig 就是 TS
                    if (project_path / "tsconfig.json").exists():
                        return "typescript"
                    return "javascript"
                return lang

    # 统计文件扩展名
    ext_count = {}
    for ext in [".go", ".py", ".js", ".jsx", ".ts", ".tsx", ".vue", ".rs", ".java", ".rb"]:
        count = len(list(project_path.rglob(f"*{ext}")))
        if count > 0:
            ext_count[ext] = count

    if not ext_count:
        return "unknown"

    # 返回最多的
    max_ext = max(ext_count, key=ext_count.get)
    lang_map = {
        ".go": "go", ".py": "python",
        ".js": "javascript", ".jsx": "javascript",
        ".ts": "typescript", ".tsx": "typescript", ".vue": "typescript",
        ".rs": "rust", ".java": "java", ".rb": "ruby",
    }
    return lang_map.get(max_ext, "unknown")


def get_file_extensions(language: str) -> List[str]:
    exts = {
        "go": [".go"],
        "python": [".py"],
        "javascript": [".js", ".jsx", ".mjs", ".cjs"],
        "typescript": [".ts", ".tsx", ".mts", ".cts"],
    }
    return exts.get(language.lower(), [])


# =============================================================================
# 函数调用提取（轻量正则，非 tree-sitter 语义级）
# 说明：比现状（无）强，比视频标准（符号级语义解析）弱。
#       能识别 direct call，不能识别多态/反射/动态分发。
#       用于填 schema 已预留的 symbols.calls/called_by 字段。
# =============================================================================

GO_KEYWORDS = {
    'if', 'for', 'switch', 'return', 'func', 'var', 'const', 'type', 'go',
    'defer', 'select', 'case', 'break', 'continue', 'fallthrough', 'range',
    'make', 'new', 'len', 'cap', 'append', 'copy', 'delete', 'panic',
    'recover', 'print', 'println', 'error',
}
PY_KEYWORDS = {
    'if', 'for', 'while', 'return', 'def', 'class', 'import', 'from', 'try',
    'except', 'finally', 'with', 'yield', 'lambda', 'print', 'isinstance',
    'range', 'len', 'super', 'self', 'cls',
}
JS_KEYWORDS = {
    'if', 'for', 'while', 'return', 'function', 'const', 'let', 'var',
    'class', 'new', 'await', 'async', 'switch', 'case', 'break', 'continue',
    'console', 'require', 'import', 'export', 'typeof', 'instanceof',
}

_NEXT_FUNC_PATTERNS = {
    'go': re.compile(r'^\s*func\s'),
    'python': re.compile(r'^\s*(?:async\s+)?def\s'),
    'javascript': re.compile(
        r'^\s*(?:export\s+)?(?:async\s+)?function\s'
        r'|^\s*(?:export\s+)?(?:const|let|var)\s+\w+\s*=\s*(?:async\s+)?\('
    ),
    'typescript': re.compile(
        r'^\s*(?:export\s+)?(?:async\s+)?function\s'
        r'|^\s*(?:export\s+)?(?:const|let|var)\s+\w+\s*=\s*(?:async\s+)?\('
    ),
}

_CALL_KEYWORDS = {
    'go': GO_KEYWORDS, 'python': PY_KEYWORDS,
    'javascript': JS_KEYWORDS, 'typescript': JS_KEYWORDS,
}


def extract_calls_in_function(lines: List[str], start_line: int,
                               func_name: str, language: str) -> List[str]:
    """提取函数体内的调用（轻量正则版）

    返回去重后的被调用符号名列表。
    不能识别：多态、反射、动态分发、跨语言桥接。
    """
    keywords = _CALL_KEYWORDS.get(language, set())
    next_func = _NEXT_FUNC_PATTERNS.get(language)

    body_lines = []
    for i in range(start_line, len(lines)):
        if i > start_line and next_func and next_func.match(lines[i]):
            break
        body_lines.append(lines[i])

    body = "\n".join(body_lines)
    call_pattern = re.compile(r'\b(\w+)\s*\(')
    calls = set()
    for m in call_pattern.finditer(body):
        name = m.group(1)
        if name not in keywords and name != func_name:
            calls.add(name)
    return sorted(calls)


# =============================================================================
# Go 解析器
# =============================================================================

def parse_go_file(filepath: Path) -> Dict[str, Any]:
    """解析 Go 源文件，提取函数、结构体、接口、路由、注释"""
    result = {
        "functions": [],
        "structs": [],
        "interfaces": [],
        "routes": [],
        "comments": [],
        "constraints": [],
        "decisions": [],
    }

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    content = "".join(lines)

    # 提取函数 (包括方法)
    # func (receiver) Name(params) returns {
    func_pattern = re.compile(
        r'func\s+'                           # func keyword
        r'(?P<receiver>\([^)]+\)\s+)?'       # optional receiver
        r'(?P<name>\w+)'                     # function name
        r'\s*\((?P<params>[^)]*)\)'         # parameters
        r'\s*(?P<returns>[^{\n]*)?'         # return types
        r'\s*\{',                            # opening brace
        re.DOTALL
    )

    for match in func_pattern.finditer(content):
        # Calculate line number
        line_num = content[:match.start()].count('\n') + 1
        func_name = match.group('name')
        receiver = match.group('receiver').strip().strip('()').strip() if match.group('receiver') else None
        params = match.group('params').strip()
        returns = match.group('returns').strip() if match.group('returns') else ""

        # Build signature
        sig = "func"
        if receiver:
            sig += f" ({receiver})"
        sig += f" {func_name}({params})"
        if returns:
            sig += f" {returns}"

        calls = extract_calls_in_function(lines, line_num, func_name, 'go')

        result["functions"].append({
            "name": func_name,
            "signature": sig,
            "receiver": receiver.split()[-1] if receiver else None,
            "params": params,
            "returns": returns,
            "line": line_num,
            "calls": calls,
        })

    # 提取结构体
    struct_pattern = re.compile(r'type\s+(\w+)\s+struct\s*\{')
    for match in struct_pattern.finditer(content):
        line_num = content[:match.start()].count('\n') + 1
        result["structs"].append({
            "name": match.group(1),
            "line": line_num,
        })

    # 提取接口
    interface_pattern = re.compile(r'type\s+(\w+)\s+interface\s*\{')
    for match in interface_pattern.finditer(content):
        line_num = content[:match.start()].count('\n') + 1
        result["interfaces"].append({
            "name": match.group(1),
            "line": line_num,
        })

    # 提取 Gin 风格路由
    # r.GET("/path", handler) / r.POST(...) / mux.HandleFunc(...)
    route_patterns = [
        # Gin: r.GET("/path", handler)
        r'(?:r|router|group)\.(GET|POST|PUT|DELETE|PATCH|OPTIONS|HEAD|Any)\s*\(\s*"([^"]+)"\s*,\s*([\w.]+)',
        # Std lib: mux.HandleFunc("/path", handler)
        r'(?:mux|http\.DefaultServeMux)\.(HandleFunc|Handle)\s*\(\s*"([^"]+)"\s*,\s*([\w.]+)',
        # Generic: .GET("/path", ...)
        r'\.(GET|POST|PUT|DELETE|PATCH)\s*\(\s*"([^"]+)"',
    ]

    for pattern in route_patterns:
        for match in re.finditer(pattern, content):
            line_num = content[:match.start()].count('\n') + 1
            method = match.group(1).upper()
            path = match.group(2)
            handler = match.group(3) if match.lastindex >= 3 else ""

            if method == "ANY" or method == "HANDLEFUNC" or method == "HANDLE":
                method = "*"

            result["routes"].append({
                "method": method,
                "path": path,
                "handler": handler,
                "line": line_num,
            })

    # 提取 ADR/决策注释
    # 格式: // ADR-XXX: Title 或 // DECISION: ...
    adr_pattern = re.compile(r'//\s*(ADR-\d+)\s*[:\-]\s*(.+?)$', re.MULTILINE)
    for match in adr_pattern.finditer(content):
        line_num = content[:match.start()].count('\n') + 1
        result["decisions"].append({
            "code": match.group(1),
            "title": match.group(2).strip(),
            "line": line_num,
            "file": str(filepath.name),
        })

    # 提取约束注释
    # 格式: // CONSTRAINT: ... 或 // FORBIDDEN: ...
    constraint_patterns = [
        (r'//\s*FORBIDDEN\s*[:\-]\s*(.+?)$', 'forbidden'),
        (r'//\s*CRITICAL\s*[:\-]\s*(.+?)$', 'critical'),
        (r'//\s*CONSTRAINT\s*[:\-]\s*(.+?)$', 'warning'),
    ]
    for pattern, severity in constraint_patterns:
        for match in re.finditer(pattern, content, re.MULTILINE):
            line_num = content[:match.start()].count('\n') + 1
            result["constraints"].append({
                "rule": match.group(1).strip(),
                "severity": severity,
                "line": line_num,
                "file": str(filepath.name),
            })

    # 提取块注释中的关键决策/约束
    # /* ... */ 或 // 连续注释块
    block_comment_pattern = re.compile(r'/\*(.*?)\*/', re.DOTALL)
    for match in block_comment_pattern.finditer(content):
        comment = match.group(1).strip()
        # 检查是否包含 ADR 或约束关键字
        if any(kw in comment.lower() for kw in ['adr', 'decision', 'constraint', 'forbidden', 'must not', 'never', 'critical']):
            line_num = content[:match.start()].count('\n') + 1
            result["comments"].append({
                "content": comment[:500],
                "line": line_num,
            })

    return result


# =============================================================================
# Python 解析器
# =============================================================================

def parse_python_file(filepath: Path) -> Dict[str, Any]:
    """解析 Python 源文件"""
    result = {
        "functions": [], "structs": [], "interfaces": [],
        "routes": [], "comments": [], "constraints": [], "decisions": [],
    }

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    content = "".join(lines)

    # 提取函数
    func_pattern = re.compile(
        r'(?:@\w+[^\n]*\n\s*)*'  # optional decorators
        r'(?:async\s+)?def\s+(\w+)\s*\(([^)]*)\)'
        r'(?:\s*->\s*([^\n:]+))?'
    )
    for match in func_pattern.finditer(content):
        line_num = content[:match.start()].count('\n') + 1
        func_name = match.group(1)
        calls = extract_calls_in_function(lines, line_num, func_name, 'python')
        result["functions"].append({
            "name": func_name,
            "params": match.group(2).strip(),
            "returns": match.group(3).strip() if match.group(3) else "",
            "line": line_num,
            "calls": calls,
        })

    # 提取类
    class_pattern = re.compile(r'class\s+(\w+)(?:\s*\([^)]+\))?\s*:')
    for match in class_pattern.finditer(content):
        line_num = content[:match.start()].count('\n') + 1
        result["structs"].append({
            "name": match.group(1),
            "line": line_num,
        })

    # Flask/FastAPI 路由
    route_patterns = [
        # Flask: @app.route("/path", methods=["GET"])
        r'@app\.route\(\s*"([^"]+)"(?:\s*,\s*methods\s*=\s*\[([^\]]*)\])?',
        # FastAPI: @router.get("/path")
        r'@(?:app|router)\.(get|post|put|delete|patch)\(\s*"([^"]+)"',
    ]
    for pattern in route_patterns:
        for match in re.finditer(pattern, content, re.IGNORECASE):
            line_num = content[:match.start()].count('\n') + 1
            if len(match.groups()) >= 2 and match.group(1) in ('get', 'post', 'put', 'delete', 'patch'):
                result["routes"].append({
                    "method": match.group(1).upper(),
                    "path": match.group(2),
                    "handler": "",
                    "line": line_num,
                })
            else:
                result["routes"].append({
                    "method": "*",
                    "path": match.group(1),
                    "handler": "",
                    "line": line_num,
                })

    return result


# =============================================================================
# JavaScript/TypeScript 解析器
# =============================================================================

def parse_js_file(filepath: Path) -> Dict[str, Any]:
    """解析 JavaScript/TypeScript 源文件"""
    result = {
        "functions": [], "structs": [], "interfaces": [],
        "routes": [], "comments": [], "constraints": [], "decisions": [],
    }

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    lines = content.split('\n')

    # 提取函数
    patterns = [
        r'(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)',
        r'(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(([^)]*)\)\s*=>',
        r'(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?function\s*\(([^)]*)\)',
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, content):
            line_num = content[:match.start()].count('\n') + 1
            func_name = match.group(1)
            calls = extract_calls_in_function(lines, line_num, func_name, 'javascript')
            result["functions"].append({
                "name": func_name,
                "params": match.group(2).strip() if match.group(2) else "",
                "line": line_num,
                "calls": calls,
            })

    # 提取类/组件
    class_pattern = re.compile(r'(?:export\s+)?(?:class|function)\s+(\w+)')
    for match in class_pattern.finditer(content):
        line_num = content[:match.start()].count('\n') + 1
        result["structs"].append({
            "name": match.group(1),
            "line": line_num,
        })

    # Express/Fastify 路由
    route_patterns = [
        r'(?:app|router)\.(get|post|put|delete|patch|all)\s*\(\s*"([^"]+)"',
        r'router\.(get|post|put|delete|patch)\(\s*["\']([^"\']+)["\']',
    ]
    for pattern in route_patterns:
        for match in re.finditer(pattern, content, re.IGNORECASE):
            line_num = content[:match.start()].count('\n') + 1
            method = match.group(1).upper()
            if method == "ALL":
                method = "*"
            result["routes"].append({
                "method": method,
                "path": match.group(2),
                "handler": "",
                "line": line_num,
            })

    return result


def get_parser(language: str):
    parsers = {
        "go": parse_go_file,
        "python": parse_python_file,
        "javascript": parse_js_file,
        "typescript": parse_js_file,
    }
    return parsers.get(language.lower())


# =============================================================================
# 文件扫描
# =============================================================================

def scan_source_files(project_path: Path, language: str) -> List[Path]:
    """扫描源码文件"""
    files = []
    exts = get_file_extensions(language)

    for ext in exts:
        for filepath in project_path.rglob(f"*{ext}"):
            # 跳过排除目录
            if any(excluded in filepath.parts for excluded in EXCLUDE_DIRS):
                continue
            files.append(filepath)

    return files


# =============================================================================
# 文件变更检测（增量更新核心）
# =============================================================================

def compute_file_hash(filepath: Path) -> str:
    """计算文件 SHA256 哈希（前16位足够）"""
    h = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                h.update(chunk)
        return h.hexdigest()[:16]
    except (IOError, OSError):
        return ""


def get_file_hashes_table(conn: sqlite3.Connection) -> Dict[str, str]:
    """从 change_log 获取上次记录的文件 hash 表"""
    cursor = conn.cursor()
    # 使用 meta 表存储文件 hash 映射
    hashes = {}
    for row in cursor.execute("SELECT key, value FROM meta WHERE key LIKE 'filehash:%'"):
        file_path = row[0].replace('filehash:', '')
        hashes[file_path] = row[1]
    return hashes


def detect_changed_files(
    project_path: Path,
    files: List[Path],
    old_hashes: Dict[str, str]
) -> Tuple[List[Path], List[Path], List[Path]]:
    """检测变更的文件：新增、修改、删除"""
    added = []
    modified = []

    current_paths = set()
    for filepath in files:
        try:
            rel = str(filepath.relative_to(project_path))
        except ValueError:
            rel = str(filepath)
        current_paths.add(rel)

        file_hash = compute_file_hash(filepath)
        old_hash = old_hashes.get(rel)

        if old_hash is None:
            added.append(filepath)
        elif old_hash != file_hash:
            modified.append(filepath)

    # 检测删除的文件
    deleted_paths = set(old_hashes.keys()) - current_paths
    deleted = [project_path / p for p in deleted_paths]

    return added, modified, deleted


def record_file_hashes(conn: sqlite3.Connection, project_path: Path, files: List[Path]):
    """更新文件 hash 记录"""
    cursor = conn.cursor()
    for filepath in files:
        try:
            rel = str(filepath.relative_to(project_path))
        except ValueError:
            rel = str(filepath)
        file_hash = compute_file_hash(filepath)
        cursor.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                      (f'filehash:{rel}', file_hash))
    conn.commit()


def record_change_log(conn: sqlite3.Connection, changes: List[Dict], author: str = None):
    """记录变更日志"""
    if not changes:
        return
    cursor = conn.cursor()
    timestamp = datetime.now().isoformat()
    if not author:
        author = os.environ.get("AI_AUTHOR", "auto")

    for change in changes:
        cursor.execute("""
            INSERT INTO change_log (timestamp, module, symbol, change_type, description, author)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            timestamp,
            change.get("module", ""),
            change.get("symbol", ""),
            change.get("change_type", "modified"),
            change.get("description", ""),
            author,
        ))
    conn.commit()


def rebuild_called_by(conn: sqlite3.Connection):
    """根据 symbols.calls 反向构建 called_by 字段

    calls 是 caller → [callee_id, ...] 的正向关系
    called_by 是 callee → [caller_id, ...] 的反向关系
    每次 build 完成后调用一次，保持索引一致。
    """
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, calls FROM symbols WHERE calls IS NOT NULL AND calls != '[]'")
    rows = cursor.fetchall()

    # name -> [sym_id] 映射（同名符号可能存在多个）
    name_to_ids = {}
    for sym_id, name, _ in rows:
        name_to_ids.setdefault(name, []).append(sym_id)

    # 反向构建：callee_id -> [caller_id, ...]
    called_by_map = {}
    for sym_id, name, calls_json in rows:
        try:
            calls = json.loads(calls_json) if calls_json else []
        except json.JSONDecodeError:
            calls = []
        for callee_name in calls:
            for callee_id in name_to_ids.get(callee_name, []):
                called_by_map.setdefault(callee_id, []).append(sym_id)

    # 写回（先清空再填）
    cursor.execute("UPDATE symbols SET called_by = '[]'")
    for callee_id, caller_ids in called_by_map.items():
        cursor.execute("UPDATE symbols SET called_by = ? WHERE id = ?",
                       (json.dumps(caller_ids), callee_id))
    conn.commit()
    print(f"  反向索引: {len(called_by_map)} 个符号被调用")


# =============================================================================
# 模块提取
# =============================================================================

def determine_layer(filepath: Path, language: str) -> str:
    """根据文件路径判断模块层级"""
    path_str = str(filepath).lower()
    name = filepath.name.lower()

    layer_rules = [
        ("proxy", ["proxy", "forward", "reverse_proxy"]),
        ("billing", ["billing", "cost", "charge", "deduct", "price"]),
        ("auth", ["auth", "login", "register", "session", "jwt"]),
        ("handler", ["handler", "controller", "api"]),
        ("service", ["service"]),
        ("repository", ["repo", "dao", "repository", "store"]),
        ("model", ["model", "entity", "dto", "schema"]),
        ("middleware", ["middleware", "interceptor"]),
        ("config", ["config", "env", "setting"]),
        ("crawler", ["crawler", "scraper", "spider"]),
        ("sync", ["sync", "crawler"]),
        ("user", ["user", "account", "profile"]),
        ("admin", ["admin", "management", "manage"]),
    ]

    for layer, keywords in layer_rules:
        if any(kw in path_str or kw in name for kw in keywords):
            return layer

    # Go 特定：main.go 作为入口
    if language == "go" and name == "main.go":
        return "entry"

    return "other"


def extract_modules(files: List[Path], language: str, project_path: Path = None) -> List[Dict]:
    """提取模块信息"""
    modules = []
    parser = get_parser(language)

    for filepath in files:
        module_name = filepath.stem
        layer = determine_layer(filepath, language)

        parsed = parser(filepath) if parser else {"functions": [], "structs": []}

        entry_func = None
        if parsed.get("functions"):
            # 第一个函数通常是入口
            entry_func = parsed["functions"][0]["name"]

        # 提取文件级注释作为 responsibility
        responsibility = f"模块 {module_name}"
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            first_lines = f.read(500)
        # 提取文件头部注释
        header_comment = re.match(r'(?://.*\n)*|(/\*.*?\*/)', first_lines, re.DOTALL)
        if header_comment:
            comment = header_comment.group(0).replace('//', '').replace('/*', '').replace('*/', '').strip()
            if len(comment) < 200:
                responsibility = comment.split('\n')[0]

        # 收集约束和决策
        constraints = []
        for c in parsed.get("constraints", []):
            constraints.append(f"{c['rule']} (in {c['file']}:{c['line']})")

        decisions = []
        for d in parsed.get("decisions", []):
            decisions.append(f"{d['code']}: {d['title']}")

        # 计算相对路径
        try:
            rel_path = str(filepath.relative_to(project_path.parent))
        except ValueError:
            rel_path = str(filepath)

        modules.append({
            "name": module_name,
            "layer": layer,
            "responsibility": responsibility,
            "entry_func": entry_func,
            "file_path": rel_path,
            "line_start": 1,
            "line_end": sum(1 for _ in open(filepath, 'r', encoding='utf-8', errors='ignore')),
            "deps": "[]",
            "sideeffects": "",
            "constraints": json.dumps(constraints) if constraints else "",
            "func_count": len(parsed.get("functions", [])),
            "struct_count": len(parsed.get("structs", [])),
            "route_count": len(parsed.get("routes", [])),
            "parsed": parsed,  # 保留给后续使用
        })

    return modules


# =============================================================================
# API 路由提取
# =============================================================================

def extract_all_routes(modules: List[Dict]) -> List[Dict]:
    """从所有模块中提取路由"""
    routes = []
    seen = set()

    for module in modules:
        parsed = module.get("parsed", {})
        for route in parsed.get("routes", []):
            key = f"{route['method']}:{route['path']}"
            if key in seen:
                continue
            seen.add(key)

            # 判断认证类型
            path = route.get("path", "")
            method = route.get("method", "*")

            auth = "none"
            if "/admin/" in path.lower():
                auth = "admin"
            elif "/v1/" in path or "/api/" in path:
                auth = "bearer"
            elif "session" in path.lower() or "login" in path.lower():
                auth = "session"

            # 判断分组
            group = "other"
            if "/admin" in path:
                group = "admin"
            elif "/v1/" in path:
                group = "proxy"
            elif "/api/user" in path or "/api/mappings" in path:
                group = "user"
            elif "/api/" in path:
                group = "user"
            elif "/health" in path:
                group = "public"

            routes.append({
                "method": method,
                "path": route["path"],
                "handler": route.get("handler", module.get("entry_func", "")),
                "auth": auth,
                "group_name": group,
                "description": "",
                "file_path": module.get("file_path", ""),
                "line_number": route.get("line", 0),
            })

    return routes


# =============================================================================
# 符号提取
# =============================================================================

def extract_symbols(modules: List[Dict]) -> List[Dict]:
    """从所有模块中提取符号（函数、结构体等）"""
    symbols = []

    for module in modules:
        parsed = module.get("parsed", {})
        module_id = module.get("name", "")

        # 函数
        for func in parsed.get("functions", []):
            sig = func.get("signature", f"func {func['name']}({func.get('params', '')})")
            symbols.append({
                "module_id": module_id,
                "name": func["name"],
                "signature": sig,
                "role": "function",
                "receiver": func.get("receiver"),
                "params": func.get("params", ""),
                "returns": func.get("returns", ""),
                "line_number": func.get("line", 0),
                "calls": json.dumps(func.get("calls", [])),
            })

        # 结构体
        for struct in parsed.get("structs", []):
            symbols.append({
                "module_id": module_id,
                "name": struct["name"],
                "signature": f"type {struct['name']} struct",
                "role": "struct",
                "line_number": struct.get("line", 0),
            })

        # 接口
        for iface in parsed.get("interfaces", []):
            symbols.append({
                "module_id": module_id,
                "name": iface["name"],
                "signature": f"type {iface['name']} interface",
                "role": "interface",
                "line_number": iface.get("line", 0),
            })

    return symbols


# =============================================================================
# 数据库操作
# =============================================================================

def create_tables(conn: sqlite3.Connection):
    """创建表结构"""
    cursor = conn.cursor()

    cursor.execute("""CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS modules (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, layer TEXT,
        responsibility TEXT, entry_func TEXT, file_path TEXT,
        line_start INTEGER, line_end INTEGER, deps TEXT, sideeffects TEXT,
        constraints TEXT, notes TEXT
    )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS symbols (
        id INTEGER PRIMARY KEY AUTOINCREMENT, module_id INTEGER, name TEXT NOT NULL,
        signature TEXT, role TEXT, receiver TEXT, params TEXT, returns TEXT,
        calls TEXT, called_by TEXT, line_number INTEGER, notes TEXT
    )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS api_routes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, method TEXT, path TEXT NOT NULL,
        handler TEXT NOT NULL, auth TEXT, group_name TEXT, description TEXT,
        file_path TEXT, line_number INTEGER, notes TEXT
    )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS tables (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, prefix TEXT,
        purpose TEXT, fields TEXT, relations TEXT, primary_key TEXT,
        foreign_keys TEXT, indexes TEXT, notes TEXT
    )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS decisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL, context TEXT, decision TEXT, consequences TEXT,
        risks TEXT, mitigations TEXT, status TEXT, source_file TEXT, notes TEXT
    )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS constraints (
        id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT, rule TEXT NOT NULL,
        severity TEXT, affected_modules TEXT, affected_tables TEXT,
        enforcement TEXT, source_location TEXT, notes TEXT
    )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS config (
        id INTEGER PRIMARY KEY AUTOINCREMENT, scope TEXT, key TEXT NOT NULL,
        value TEXT, type TEXT, description TEXT, source TEXT, notes TEXT
    )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS data_flow (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
        description TEXT, steps TEXT, involved_modules TEXT,
        involved_tables TEXT, notes TEXT
    )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS change_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, module TEXT,
        symbol TEXT, change_type TEXT, description TEXT, author TEXT, notes TEXT
    )""")

    conn.commit()


def insert_data(conn: sqlite3.Connection, data: Dict[str, Any]):
    """插入数据"""
    cursor = conn.cursor()

    # meta
    for key, value in data.get("meta", {}).items():
        cursor.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (key, str(value)))

    # modules
    for module in data.get("modules", []):
        cursor.execute("""
            INSERT INTO modules (name, layer, responsibility, entry_func, file_path,
                line_start, line_end, deps, sideeffects, constraints, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            module["name"], module.get("layer", ""), module.get("responsibility", ""),
            module.get("entry_func", ""), module.get("file_path", ""),
            module.get("line_start", 1), module.get("line_end", 0),
            module.get("deps", "[]"), module.get("sideeffects", ""),
            module.get("constraints", ""),
            f"{module.get('func_count', 0)} functions, {module.get('struct_count', 0)} structs, {module.get('route_count', 0)} routes",
        ))

    # symbols
    for sym in data.get("symbols", []):
        cursor.execute("""
            INSERT INTO symbols (module_id, name, signature, role, receiver, params, returns, line_number, calls)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sym.get("module_id", ""), sym["name"], sym.get("signature", ""),
            sym.get("role", ""), sym.get("receiver"), sym.get("params", ""),
            sym.get("returns", ""), sym.get("line_number", 0),
            sym.get("calls", "[]"),
        ))

    # api_routes
    for route in data.get("api_routes", []):
        cursor.execute("""
            INSERT INTO api_routes (method, path, handler, auth, group_name, description, file_path, line_number)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            route.get("method", ""), route.get("path", ""), route.get("handler", ""),
            route.get("auth", ""), route.get("group_name", ""), route.get("description", ""),
            route.get("file_path", ""), route.get("line_number", 0),
        ))

    # decisions
    for dec in data.get("decisions", []):
        cursor.execute("""
            INSERT OR REPLACE INTO decisions (code, title, status, source_file)
            VALUES (?, ?, ?, ?)
        """, (
            dec.get("code", ""), dec.get("title", ""),
            dec.get("status", "accepted"), dec.get("source_file", ""),
        ))

    # constraints
    for c in data.get("constraints", []):
        cursor.execute("""
            INSERT INTO constraints (category, rule, severity, source_location)
            VALUES (?, ?, ?, ?)
        """, (
            c.get("category", "business"), c.get("rule", ""),
            c.get("severity", "warning"), c.get("source_location", ""),
        ))

    conn.commit()


# =============================================================================
# CONTEXT.md 生成
# =============================================================================

def generate_context_md(conn: sqlite3.Connection, output_path: Path, recent_count: int = 5):
    """生成 L1 导航文件"""
    cursor = conn.cursor()

    # 获取基本信息
    meta = {}
    for row in cursor.execute("SELECT key, value FROM meta"):
        if not row[0].startswith('filehash:'):  # Skip file hashes
            meta[row[0]] = row[1]

    # 获取最近变更
    recent_changes = cursor.execute(
        "SELECT timestamp, module, change_type, description, author FROM change_log ORDER BY id DESC LIMIT ?",
        (recent_count,)
    ).fetchall()

    # 获取模块
    modules = cursor.execute("SELECT name, layer, responsibility FROM modules ORDER BY layer, name").fetchall()

    # 获取表
    tables = cursor.execute("SELECT name, purpose FROM tables ORDER BY name").fetchall()

    # 获取约束（forbidden/critical）
    constraints = cursor.execute(
        "SELECT rule, severity FROM constraints WHERE severity IN ('forbidden', 'critical') ORDER BY severity"
    ).fetchall()

    # 获取决策
    decisions = cursor.execute("SELECT code, title, status FROM decisions ORDER BY code").fetchall()

    # 获取 API 路由（按组统计）
    route_groups = cursor.execute(
        "SELECT group_name, COUNT(*) FROM api_routes GROUP BY group_name"
    ).fetchall()

    # 统计信息
    total_funcs = cursor.execute("SELECT COUNT(*) FROM symbols WHERE role='function'").fetchone()[0]
    total_routes = cursor.execute("SELECT COUNT(*) FROM api_routes").fetchone()[0]

    # 生成内容
    lines = [
        f"# {meta.get('name', 'Project')} · AI Navigation (L1)",
        "",
        "> 本文件由脚本自动生成，人不需要阅读。",
        f"> 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "> AI 首次读取本文件后，按需从 `.ai/*.ai.db` 拉取具体信息。",
        "",
        "## 项目一句话定位",
        "",
        f"**{meta.get('name', 'Project')} = {meta.get('description', '项目描述')}**",
        "",
        f"- **语言**: {meta.get('language', '?')} | **框架**: {meta.get('framework', '?')}",
        f"- **端口**: {meta.get('port', '?')} | **版本**: {meta.get('version', '?')}",
        f"- **入口**: {meta.get('entry_point', '?')} | **函数数**: {total_funcs} | **API 数**: {total_routes}",
        "",
    ]

    # 最近变更（循环模式核心）
    if recent_changes:
        lines.append("## 最近变更\n")
        lines.append("| 时间 | 模块 | 类型 | 描述 | 操作者 |")
        lines.append("|------|------|------|------|--------|")
        for ts, module, change_type, desc, author in recent_changes:
            # 截断时间戳
            short_ts = ts[:16].replace('T', ' ') if 'T' in ts else ts[:16]
            lines.append(f"| {short_ts} | {module} | {change_type} | {desc} | {author} |")
        lines.append("")

    if constraints:
        lines.append("## 核心约束（绝对不可违背）\n")
        lines.append("| 规则 | 严重度 |")
        lines.append("|------|--------|")
        for rule, severity in constraints:
            lines.append(f"| {rule} | {severity} |")
        lines.append("")

    if modules:
        lines.append("## 模块索引\n")
        lines.append("| 模块 | 层级 | 一句话职责 |")
        lines.append("|------|------|------------|")
        for name, layer, resp in modules:
            lines.append(f"| {name} | {layer} | {resp} |")
        lines.append("")

    if tables:
        lines.append("## 数据库表索引\n")
        lines.append("| 表 | 用途 |")
        lines.append("|----|------|")
        for name, purpose in tables:
            lines.append(f"| {name} | {purpose} |")
        lines.append("")

    if decisions:
        lines.append("## 决策索引（ADR）\n")
        for code, title, status in decisions:
            lines.append(f"- {code}: {title} ({status})")
        lines.append("")

    lines.append("## 快速查询命令\n")
    lines.append("```bash")
    lines.append(f"cd .ai && python query_db.py \"这次循环改了什么\"    # 最近变更")
    lines.append(f"cd .ai && python query_db.py billing        # 计费约束")
    lines.append(f"cd .ai && python query_db.py '/v1/'         # API路由")
    lines.append(f"cd .ai && python query_db.py tf_tokens      # 表结构")
    lines.append(f"cd .ai && python query_db.py ADR-001        # 决策记录")
    lines.append(f"cd .ai && python query_db.py all constraints # 全部约束")
    lines.append(f"cd .ai && python query_db.py --sql 'SELECT ...'  # 直接 SQL")
    lines.append("```\n")

    output_path.write_text("\n".join(lines), encoding='utf-8')
    print(f"  CONTEXT.md generated: {output_path}")


# =============================================================================
# 主流程
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="构建 AI 项目知识库 v2")
    parser.add_argument("project_path", help="项目路径")
    parser.add_argument("--output", "-o", help="输出数据库路径")
    parser.add_argument("--incremental", "-i", action="store_true", help="增量更新模式")
    parser.add_argument("--force", "-f", action="store_true", help="强制覆盖")
    parser.add_argument("--context-only", action="store_true", help="只更新 CONTEXT.md")
    parser.add_argument("--author", "-a", default=None, help="操作者标识 (AI session ID / 用户名)")
    parser.add_argument("--language", "-l", default=None, help="强制指定语言 (go/python/javascript/typescript)")
    args = parser.parse_args()

    project_path = Path(args.project_path).resolve()
    if not project_path.exists():
        print(f"错误: 项目路径不存在 {project_path}")
        sys.exit(1)

    # 确定输出目录: {workspace}/{project_name}/.ai
    ai_dir = project_path / ".ai"
    ai_dir.mkdir(exist_ok=True)

    if args.output:
        db_path = Path(args.output)
    else:
        db_path = ai_dir / f"{project_path.name}.ai.db"

    # 检测语言（支持强制指定）
    if args.language:
        language = args.language
    else:
        language = detect_language(project_path)
    print(f"项目路径: {project_path}")
    print(f"检测语言: {language}")
    print(f"输出数据库: {db_path}")

    if language == "unknown":
        print("警告: 无法检测项目语言，尝试使用 Go 解析器")
        language = "go"

    # 检查是否已存在
    if db_path.exists() and not args.force and not args.incremental:
        print(f"数据库已存在: {db_path}")
        print("使用 --force 强制覆盖 或 --incremental 增量更新")
        # 仍然生成 CONTEXT.md
        conn = sqlite3.connect(str(db_path))
        generate_context_md(conn, ai_dir / "CONTEXT.md")
        conn.close()
        sys.exit(0)

    if args.context_only and db_path.exists():
        conn = sqlite3.connect(str(db_path))
        generate_context_md(conn, ai_dir / "CONTEXT.md")
        conn.close()
        print("CONTEXT.md 已更新")
        sys.exit(0)

    # 连接数据库
    if args.force and db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(str(db_path))
    create_tables(conn)

    # 增量更新模式
    if args.incremental and db_path.exists():
        print("\n=== 增量更新模式 ===")
        _do_incremental_update(conn, project_path, language, ai_dir, args.author)
        conn.close()
        return

    # 全量构建模式
    _do_full_build(conn, project_path, language, ai_dir, args.author)
    conn.close()


def _do_full_build(conn, project_path, language, ai_dir, author=None):
    """全量构建"""
    # 写入元信息
    meta = {
        "name": project_path.name,
        "language": language,
        "port": "",
        "description": "",
        "entry_point": "",
        "version": "",
        "generated_at": datetime.now().isoformat(),
    }

    # 扫描源码
    print(f"\n扫描 {language} 源码...")
    source_files = scan_source_files(project_path, language)
    print(f"  发现 {len(source_files)} 个源文件")

    # 提取模块
    print("提取模块信息...")
    modules = extract_modules(source_files, language, project_path)
    print(f"  提取 {len(modules)} 个模块")

    # 提取路由
    print("提取 API 路由...")
    routes = extract_all_routes(modules)
    print(f"  提取 {len(routes)} 条路由")

    # 提取符号
    print("提取符号表...")
    symbols = extract_symbols(modules)
    print(f"  提取 {len(symbols)} 个符号")

    # 清理 parsed 字段（不需要存入数据库）
    for m in modules:
        m.pop("parsed", None)

    # 组装数据
    data = {
        "meta": meta,
        "modules": modules,
        "api_routes": routes,
        "symbols": symbols,
        "decisions": [],
        "constraints": [],
    }

    # 插入数据
    print("\n写入数据库...")
    insert_data(conn, data)

    # 记录文件 hash
    print("记录文件指纹...")
    record_file_hashes(conn, project_path, source_files)

    # 记录变更日志
    changes = [{"module": "all", "symbol": "", "change_type": "initial_build",
                "description": f"首次构建知识库，扫描 {len(source_files)} 个文件"}]
    record_change_log(conn, changes, author)

    # 构建调用反向索引
    print("构建调用反向索引...")
    rebuild_called_by(conn)

    # 生成 CONTEXT.md
    print("\n生成 CONTEXT.md...")
    generate_context_md(conn, ai_dir / "CONTEXT.md")

    # 打印统计
    print(f"\n{'=' * 50}")
    print("知识库构建完成")
    print(f"{'=' * 50}")
    print(f"  modules: {len(modules)}")
    print(f"  api_routes: {len(routes)}")
    print(f"  symbols: {len(symbols)}")
    print(f"{'=' * 50}")
    print(f"\n知识库: {ai_dir / f'{project_path.name}.ai.db'}")
    print(f"导航文件: {ai_dir / 'CONTEXT.md'}")


def _do_incremental_update(conn, project_path, language, ai_dir, author=None):
    """增量更新：只扫描变更过的文件"""
    # 获取上次记录的文件 hash
    old_hashes = get_file_hashes_table(conn)

    # 扫描当前所有文件
    source_files = scan_source_files(project_path, language)
    print(f"  当前 {len(source_files)} 个源文件，上次记录 {len(old_hashes)} 个")

    # 检测变更
    added, modified, deleted = detect_changed_files(project_path, source_files, old_hashes)
    print(f"  新增: {len(added)} | 修改: {len(modified)} | 删除: {len(deleted)}")

    if not added and not modified and not deleted:
        print("\n  无变更，跳过构建")
        # 仍然更新 CONTEXT.md
        generate_context_md(conn, ai_dir / "CONTEXT.md")
        return

    # 记录变更
    changes = []
    for f in added:
        changes.append({
            "module": f.stem,
            "symbol": "",
            "change_type": "added",
            "description": f"新增文件: {f.name}",
        })
    for f in modified:
        changes.append({
            "module": f.stem,
            "symbol": "",
            "change_type": "modified",
            "description": f"修改文件: {f.name}",
        })
    for f in deleted:
        changes.append({
            "module": f.stem,
            "symbol": "",
            "change_type": "deleted",
            "description": f"删除文件: {f.name}",
        })

    # 解析变更文件
    parser = get_parser(language)
    changed_modules = []
    all_changed_symbols = []

    # 处理新增和修改的文件
    for filepath in added + modified:
        parsed = parser(filepath) if parser else {"functions": [], "structs": []}
        layer = determine_layer(filepath, language)

        entry_func = parsed["functions"][0]["name"] if parsed.get("functions") else None
        line_count = sum(1 for _ in open(filepath, 'r', encoding='utf-8', errors='ignore'))

        try:
            rel_path = str(filepath.relative_to(project_path.parent))
        except ValueError:
            rel_path = str(filepath)

        responsibility = f"模块 {filepath.stem}"
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            first_lines = f.read(500)
        header_comment = re.match(r'(?://.*\n)*|(/\*.*?\*/)', first_lines, re.DOTALL)
        if header_comment:
            comment = header_comment.group(0).replace('//', '').replace('/*', '').replace('*/', '').strip()
            if len(comment) < 200:
                responsibility = comment.split('\n')[0]

        # 收集约束
        constraints = []
        for c in parsed.get("constraints", []):
            constraints.append(f"{c['rule']} (in {c['file']}:{c['line']})")

        changed_modules.append({
            "name": filepath.stem,
            "layer": layer,
            "responsibility": responsibility,
            "entry_func": entry_func,
            "file_path": rel_path,
            "line_start": 1,
            "line_end": line_count,
            "deps": "[]",
            "sideeffects": "",
            "constraints": json.dumps(constraints) if constraints else "",
            "func_count": len(parsed.get("functions", [])),
            "struct_count": len(parsed.get("structs", [])),
            "route_count": len(parsed.get("routes", [])),
            "parsed": parsed,
        })

        # 提取符号
        for func in parsed.get("functions", []):
            all_changed_symbols.append({
                "module_id": filepath.stem,
                "name": func["name"],
                "signature": func.get("signature", f"func {func['name']}({func.get('params', '')})"),
                "role": "function",
                "receiver": func.get("receiver"),
                "params": func.get("params", ""),
                "returns": func.get("returns", ""),
                "line_number": func.get("line", 0),
                "calls": json.dumps(func.get("calls", [])),
                "change_type": "added" if filepath in added else "modified",
            })

        # 记录约束
        for c in parsed.get("constraints", []):
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO constraints (category, rule, severity, source_location)
                VALUES (?, ?, ?, ?)
            """, ("business", c["rule"], c["severity"], f"{c['file']}:{c['line']}"))

        # 记录决策
        for d in parsed.get("decisions", []):
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO decisions (code, title, status, source_file)
                VALUES (?, ?, ?, ?)
            """, (d["code"], d["title"], "accepted", d["file"]))

    # 更新 modules 表（删除旧记录，插入新记录）
    for m in changed_modules:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM modules WHERE name = ?", (m["name"],))
        cursor.execute("""
            INSERT INTO modules (name, layer, responsibility, entry_func, file_path,
                line_start, line_end, deps, sideeffects, constraints, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            m["name"], m.get("layer", ""), m.get("responsibility", ""),
            m.get("entry_func", ""), m.get("file_path", ""),
            m.get("line_start", 1), m.get("line_end", 0),
            m.get("deps", "[]"), m.get("sideeffects", ""),
            m.get("constraints", ""),
            f"{m.get('func_count', 0)} functions, {m.get('struct_count', 0)} structs, {m.get('route_count', 0)} routes",
        ))

    # 更新符号表（先删除旧符号，再插入新符号）
    for m in changed_modules:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM symbols WHERE module_id = ?", (m["name"],))

    for sym in all_changed_symbols:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO symbols (module_id, name, signature, role, receiver, params, returns, line_number, calls)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sym.get("module_id", ""), sym["name"], sym.get("signature", ""),
            sym.get("role", ""), sym.get("receiver"), sym.get("params", ""),
            sym.get("returns", ""), sym.get("line_number", 0),
            sym.get("calls", "[]"),
        ))

    # 重新提取路由（基于变更后的模块）
    new_routes = extract_all_routes(changed_modules)
    # 删除旧路由中来自变更模块的
    for m in changed_modules:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM api_routes WHERE file_path LIKE ?", (f"%{m['name']}%",))

    for route in new_routes:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO api_routes (method, path, handler, auth, group_name, description, file_path, line_number)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            route.get("method", ""), route.get("path", ""), route.get("handler", ""),
            route.get("auth", ""), route.get("group_name", ""), route.get("description", ""),
            route.get("file_path", ""), route.get("line_number", 0),
        ))

    # 更新文件 hash
    record_file_hashes(conn, project_path, source_files)

    # 记录变更日志
    record_change_log(conn, changes, author)

    # 重建调用反向索引（全量重建：变更模块的符号关系会扩散影响其他模块的 called_by）
    print("构建调用反向索引...")
    rebuild_called_by(conn)

    # 更新 CONTEXT.md
    print("\n生成 CONTEXT.md...")
    generate_context_md(conn, ai_dir / "CONTEXT.md")

    # 打印统计
    print(f"\n{'=' * 50}")
    print("增量更新完成")
    print(f"{'=' * 50}")
    print(f"  新增文件: {len(added)}")
    print(f"  修改文件: {len(modified)}")
    print(f"  删除文件: {len(deleted)}")
    print(f"  变更符号: {len(all_changed_symbols)}")
    print(f"  新增路由: {len(new_routes)}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
