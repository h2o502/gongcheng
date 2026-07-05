# gongyi 改动明细 — 符号级调用关系 + 知识库 git 资产化

> 日期：2026-07-05
> 主题：借鉴 Codebase-Memory-MCP 视频理念（"上下文质量 > 模型参数"），补两个能力 gap
> 性质：填 schema 已预留字段 + 资产化配置，不引入新依赖，不改表结构

---

## 一、改动动机

视频《Token消耗减少120倍？Codebase-Memory-MCP的性能突破原理解析》核心主张：
- 符号级调用路径（精确到 file:line），替代 grep 翻文件
- 知识图谱作为团队 git 资产，新人 clone 即用

gongyi 现状两个 gap：
1. [schema.md](references/schema.md) 已定义 `symbols.calls` / `symbols.called_by` 字段，但 build_db.py 从未填充
2. 知识库 .ai.db 默认不进 git，新人要重新索引

---

## 二、改动文件清单（5 个文件）

| # | 文件 | 改动类型 | 行数 |
|---|---|---|---|
| 1 | `gongyi/scripts/build_db.py` | 加函数 + 改 3 个 parser + 改 2 处 insert + 接入 2 个 build 流程 | ~110 行 |
| 2 | `gongyi/scripts/query_db.py` | 加 2 个自然语言查询模式 | ~12 行 |
| 3 | `gongyi/scripts/init_project.sh` | 加 .gitignore 资产化注入 + 末尾提示 | ~35 行 |
| 4 | `gongyi/SKILL.md` | 最佳实践加 2 条 + 示例命令加 2 行 | ~6 行 |
| 5 | `gongkong/.gitignore` | 无改动（资产化策略在项目 .gitignore，不在 skill 自身） | 0 |

---

## 三、逐文件改动详情

### 文件 1：`gongyi/scripts/build_db.py`

#### 1.1 新增工具函数 `extract_calls_in_function`（在 `get_file_extensions` 之后）

```python
GO_KEYWORDS = { ... }  # 关键字过滤表
PY_KEYWORDS = { ... }
JS_KEYWORDS = { ... }

_NEXT_FUNC_PATTERNS = {  # 各语言"下一个函数定义"的正则，用于界定函数体边界
    'go': re.compile(r'^\s*func\s'),
    'python': re.compile(r'^\s*(?:async\s+)?def\s'),
    'javascript': re.compile(...),
    'typescript': re.compile(...),
}

_CALL_KEYWORDS = {'go': GO_KEYWORDS, 'python': PY_KEYWORDS, ...}

def extract_calls_in_function(lines, start_line, func_name, language) -> List[str]:
    """提取函数体内的调用（轻量正则版）
    返回去重后的被调用符号名列表。
    不能识别：多态、反射、动态分发、跨语言桥接。
    """
```

**原理**：从函数定义行扫描到下一个函数定义，用 `\b(\w+)\s*\(` 匹配调用，过滤关键字。

#### 1.2 三个 parser 加 calls 字段

- `parse_go_file`：functions.append 加 `"calls": calls`
- `parse_python_file`：同上
- `parse_js_file`：同上（顺带补了 `lines = content.split('\n')`，原来只有 content）

#### 1.3 `extract_symbols` 加 calls 字段

functions 循环里 symbols.append 加 `"calls": json.dumps(func.get("calls", []))`

#### 1.4 `insert_data` symbols INSERT 加 calls 列

```sql
-- 改前
INSERT INTO symbols (module_id, name, signature, role, receiver, params, returns, line_number)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)

-- 改后
INSERT INTO symbols (module_id, name, signature, role, receiver, params, returns, line_number, calls)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
```

#### 1.5 新增 `rebuild_called_by` 函数（在 `record_change_log` 之后）

```python
def rebuild_called_by(conn):
    """根据 symbols.calls 反向构建 called_by 字段
    calls 是 caller → [callee_name, ...]（字符串数组）
    called_by 是 callee → [caller_id, ...]（id 数组）
    """
    # 1. 读所有有 calls 的符号
    # 2. 建 name -> [sym_id] 映射（同名符号可能多个）
    # 3. 遍历每个 caller 的 calls，把 caller_id 加到 callee 的 called_by
    # 4. 先 UPDATE called_by = '[]' 清空，再逐条写入
```

**设计决策**：called_by 存 id 而非 name，因为 id 唯一，反向查询 JOIN 更直接。
calls 存 name 而非 id，因为提取时不知道 callee 的 id（callee 可能在别的文件，还没解析到）。

#### 1.6 接入两个 build 流程

- `_do_full_build`：在 `record_change_log` 之后、`generate_context_md` 之前加 `rebuild_called_by(conn)`
- `_do_incremental_update`：同位置加。**注意增量也必须全量重建 called_by**——因为变更模块的符号变了，其他模块对它的 called_by 关系也变了

#### 1.7 增量分支 `all_changed_symbols` 加 calls 字段

```python
all_changed_symbols.append({
    ...
    "calls": json.dumps(func.get("calls", [])),  # 新增
})
```

增量 INSERT 也改成 9 列（同 1.4）。

---

### 文件 2：`gongyi/scripts/query_db.py`

在 `QUERY_PATTERNS` 的"符号/函数"段之后加 2 个模式：

```python
# 调用关系（符号级，依赖 calls/called_by 字段）
# called_by 存的是 caller 的 symbol id（rebuild_called_by 写入）
# calls 存的是 callee 的符号名（字符串数组，extract_calls_in_function 写入）
("(?:谁调用|谁用了|被谁调用|called_by|调用方|调用者)\s+(\w+)",
 "SELECT s2.name AS caller, s2.signature, m.file_path, s2.line_number "
 "FROM symbols s JOIN symbols s2 ON s2.id IN (SELECT value FROM json_each(s.called_by)) "
 "JOIN modules m ON s2.module_id = m.name WHERE s.name = '{keyword}'"),
("(?:调用谁|调用了什么|calls|调用关系)\s+(\w+)",
 "SELECT s2.name AS callee, s2.signature, m.file_path, s2.line_number "
 "FROM symbols s JOIN symbols s2 ON s2.name IN (SELECT value FROM json_each(s.calls)) "
 "JOIN modules m ON s2.module_id = m.name WHERE s.name = '{keyword}'"),
```

**注意 JOIN 条件差异**：
- 反向（谁调用 X）：`s2.id IN (json_each(s.called_by))` —— called_by 存 id
- 正向（X 调用谁）：`s2.name IN (json_each(s.calls))` —— calls 存 name

**依赖**：SQLite JSON1 扩展（Python 3.9+ 自带 sqlite3 默认编译，需 SQLite ≥ 3.38）

---

### 文件 3：`gongyi/scripts/init_project.sh`

#### 3.1 加 `inject_gitignore` 函数（在复制脚本之后）

```bash
inject_gitignore() {
  local gitignore="$1"
  local marker="# gongyi — 知识库资产化策略"
  if [ -f "$gitignore" ] && grep -qF "$marker" "$gitignore"; then
    return 0  # 已注入过，跳过
  fi
  cat >> "$gitignore" << 'EOF'

# gongyi — 知识库资产化策略
# SQLite 知识库作为团队 git 资产提交，新人 clone 即拥有项目记忆
# 运行时产物（wal/shm）忽略
!.ai/
!.ai/*.ai.db
!.ai/CONTEXT.md
!.ai/build_db.py
!.ai/query_db.py
!.ai/export_md.py
!.ai/references/
.ai/*.db-wal
.ai/*.db-shm
EOF
}
```

调用：项目根 `.gitignore` 存在则追加，不存在则创建。

#### 3.2 末尾提示加一行

```
6. 知识库 .ai/*.ai.db 作为 git 资产提交，新人 clone 即拥有项目记忆
```

---

### 文件 4：`gongyi/SKILL.md`

#### 4.1 "日常开发循环"示例加 2 行

```bash
cd <project.root>/.ai && python3 query_db.py "谁调用 validateToken"   # 查调用方（符号级，精确到行号）
cd <project.root>/.ai && python3 query_db.py "调用关系 validateToken" # 查被调用方
```

#### 4.2 "给 AI 的建议" 加第 4 条

```
4. **修改函数前** — 查调用关系：`query_db.py "谁调用 validateToken"`，拿到所有调用方 file:line，不用 grep 整个代码库
```

原第 4、5 条顺延为 5、6，第 5 条补注 "（calls/called_by 会自动重建）"。

#### 4.3 "给人类的建议" 加第 5 条

```
5. **知识库是 git 资产** — `.ai/*.ai.db` 随代码提交，新同事 clone 即拥有项目记忆，不用重新索引
```

---

## 四、验证结果

用 gongyi/scripts 自身（Python 项目，3 个文件）做目标验证：

```
全量 build：
  modules: 3
  api_routes: 2
  symbols: 55
  反向索引: 49 个符号被调用

增量 build（修改 1 文件触发）：
  修改文件: 1
  变更符号: 24
  反向索引: 49 个符号被调用  ← 增量分支也正确重建

查询验证：
  query_db.py "谁调用 extract_calls_in_function"
  → 返回 3 个 caller：parse_go_file / parse_python_file / parse_js_file，精确到行号 ✓

  query_db.py "调用关系 main"
  → 返回 main 调用的所有项目内符号（_do_full_build / detect_language / ...）✓

字段验证：
  symbols.calls：JSON 字符串数组，如 ["exists","get","max","rglob"]
  symbols.called_by：JSON id 数组，如 [4,5,6]
```

---

## 五、不做什么（及原因）

| 项 | 不做原因 |
|---|---|
| MCP 化 | 架构改造，工作量大。当前 gongyi 在 gongcheng 编排下被 AI 调用，非 MCP 不影响能力 |
| tree-sitter / 轻量语义解析 | 重依赖，与 skill 无重依赖原则冲突。本次正则覆盖 direct call 80% 场景 |
| zstd 压缩快照 | SQLite 通常 <1MB，git 直接提交即可 |
| pre-commit hook | 治本是 gongcheng 编排层强制 build，hook 是兜底 |
| token 预算参数 | 符号级索引才是真正的 token 杠杆 |
| 实时文件 watcher | 常驻进程成本高，手动 `--incremental` 已够用 |
| call_graph 新表 | schema 里 symbols.calls/called_by 已预留，加新表是重复造轮子 |
| query_db.py 的 SyntaxWarning 修复 | 原有代码的非 raw 字符串问题，非本次引入，避免范围蔓延 |

---

## 六、skillhub 同步检查清单

- [ ] gongyi/scripts/build_db.py — 同步（核心改动）
- [ ] gongyi/scripts/query_db.py — 同步（2 个查询模式）
- [ ] gongyi/scripts/init_project.sh — 同步（.gitignore 注入）
- [ ] gongyi/SKILL.md — 同步（最佳实践 + 示例）
- [ ] gongyi/references/schema.md — **无需改**（calls/called_by 字段早已定义，本次只是开始填充）
- [ ] gongkong/ — **无需改**（资产化策略在项目 .gitignore，不在 skill 自身）
- [ ] gongyou/ — **无需改**（不涉及调用关系）
- [ ] gongcheng/ — **无需改**（编排层不感知实现细节）

---

## 七、回滚方法

如需回滚，按文件 reverse 操作：

1. build_db.py：删除 `extract_calls_in_function`、`rebuild_called_by` 函数；3 个 parser 删 `"calls": calls`；2 处 INSERT 删 calls 列；2 个 build 流程删 `rebuild_called_by(conn)` 调用
2. query_db.py：删 2 个 QUERY_PATTERNS
3. init_project.sh：删 `inject_gitignore` 函数及其调用、末尾提示第 6 条
4. SKILL.md：删"给 AI 的建议"第 4 条、"给人类的建议"第 5 条、示例 2 行

**数据库兼容性**：旧 db 的 symbols 表 calls/called_by 字段为 NULL，新代码读 NULL 会当 `[]` 处理，不影响。新 db 给旧代码读也 OK（旧代码忽略这两列）。**完全向后兼容**。
