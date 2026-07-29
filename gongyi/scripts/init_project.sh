#!/bin/bash
# AI 项目知识库 — 快速初始化脚本 v2
#
# 用法: bash init_project.sh <项目路径>
#
# 功能:
#   1. 在项目下创建 .ai/ 目录
#   2. 复制所有脚本到 .ai/
#   3. 注入初始约束模板
#   4. 自动运行首次构建

set -e

SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_PATH="${1:-.}"

if [ ! -d "$PROJECT_PATH" ]; then
    echo "错误: 项目路径不存在: $PROJECT_PATH"
    exit 1
fi

PROJECT_NAME=$(basename "$(cd "$PROJECT_PATH" && pwd)")
AI_DIR="$PROJECT_PATH/.ai"

echo "=== AI 项目知识库 v2 — 初始化 ==="
echo "项目: $PROJECT_NAME"
echo "路径: $PROJECT_PATH"

# 创建 .ai 目录
mkdir -p "$AI_DIR"

# 复制脚本
echo ""
echo "复制脚本到 $AI_DIR..."
cp "$SKILL_DIR/scripts/build_db.py" "$AI_DIR/"
cp "$SKILL_DIR/scripts/query_db.py" "$AI_DIR/"
cp "$SKILL_DIR/scripts/export_md.py" "$AI_DIR/"
chmod +x "$AI_DIR/"*.py

# 复制 schema 参考
mkdir -p "$AI_DIR/references"
cp "$SKILL_DIR/references/schema.md" "$AI_DIR/references/" 2>/dev/null || true

echo "  build_db.py   ✓"
echo "  query_db.py   ✓"
echo "  export_md.py  ✓"
echo "  references/schema.md  ✓"

# 注入初始约束模板
echo ""
echo "注入初始约束模板..."
CONSTRAINTS_SQL="$AI_DIR/init_constraints.sql"
cat > "$CONSTRAINTS_SQL" << 'EOF'
-- 通用约束模板（可根据项目实际情况修改）
-- 这些是开发循环中的红线，AI 在开发时必须遵守

INSERT OR IGNORE INTO constraints (category, rule, severity, notes) VALUES
    ('transactional', '涉及金额变动的操作必须使用事务', 'forbidden', '防止金额不一致'),
    ('business', '扣费金额不能为负数', 'forbidden', '防止反向扣费'),
    ('security', '用户密码不能明文存储', 'forbidden', '必须使用哈希'),
    ('business', '用户不能查看其他用户的数据', 'forbidden', '数据隔离'),
    ('integrity', '外键关联的记录删除前检查依赖', 'warning', '防止孤立记录');
EOF

echo "  init_constraints.sql  ✓"

# 运行首次构建
echo ""
echo "运行首次构建..."
cd "$PROJECT_PATH"
python3 "$AI_DIR/build_db.py" "$PROJECT_PATH" --force

# 注入约束模板到数据库
if [ -f "$CONSTRAINTS_SQL" ]; then
    DB_FILE=$(find "$AI_DIR" -name "*.ai.db" | head -1)
    if [ -n "$DB_FILE" ]; then
        echo ""
        echo "注入约束模板到数据库..."
        sqlite3 "$DB_FILE" < "$CONSTRAINTS_SQL"
        echo "  约束已注入 ✓"
    fi
fi

# 重新生成 CONTEXT.md
python3 "$AI_DIR/build_db.py" "$PROJECT_PATH" --context-only

echo ""
echo "=== 初始化完成 ==="
echo ""
echo "开发循环使用方法:"
echo ""
echo "  1. AI 首次接触: 读 $AI_DIR/CONTEXT.md"
echo "  2. AI 开发完成后:"
echo "     python3 $AI_DIR/build_db.py $PROJECT_PATH --incremental --author 'AI-session-xxx'"
echo "  3. 交接给人类查看:"
echo "     python3 $AI_DIR/export_md.py $AI_DIR/${PROJECT_NAME}.ai.db --review -o REVIEW.md"
echo "     python3 $AI_DIR/export_md.py $AI_DIR/${PROJECT_NAME}.ai.db --diff -o CHANGELOG.md"
echo "  4. 人类审查后交还给 AI: 继续第 2 步"
echo "  5. 版本迭代完成时:"
echo "     python3 $AI_DIR/export_md.py $AI_DIR/${PROJECT_NAME}.ai.db -o docs/PROJECT_SPEC.md"
echo ""
echo "快捷查询:"
echo "  cd $AI_DIR && python3 query_db.py \"这次循环改了什么\""
echo "  cd $AI_DIR && python3 query_db.py billing  # 查 billing 模块约束"
echo "  cd $AI_DIR && python3 query_db.py --sql \"SELECT * FROM constraints WHERE severity='forbidden'\""
