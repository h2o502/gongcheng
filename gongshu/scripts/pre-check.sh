#!/bin/bash
# gongshu pre-check.sh — 执行前自动检查 SQL 风险等级
# 用法: bash pre-check.sh "<SQL语句>" "<数据库连接名>"
# 输出: 风险等级 + 影响行数预估 + 是否触及敏感字段

set -euo pipefail

SQL="$1"
DB_NAME="${2:-default}"

# 默认敏感字段清单（可被 config.yaml 覆盖）
SENSITIVE_FIELDS="password_hash|password|passwd|pwd|token|api_key|apikey|secret|private_key|balance|credit|amount|deposit|email|phone|mobile|id_card|role|permission|is_admin|is_super"

# 检测 SQL 类型
sql_type=$(echo "$SQL" | awk '{print toupper($1)}')

case "$sql_type" in
  SELECT|EXPLAIN|SHOW|DESCRIBE|DESC)
    echo "RISK_LEVEL=L1"
    echo "TYPE=readonly"
    echo "REQUIREMENT=none"
    exit 0
    ;;
  INSERT)
    RISK="L2"
    ;;
  UPDATE|DELETE)
    RISK="L3"
    # 检测是否无 WHERE
    if ! echo "$SQL" | grep -qi "WHERE"; then
      RISK="L4"
      echo "WARNING: no WHERE clause, full table operation"
    fi
    # 检测敏感字段
    if echo "$SQL" | grep -qiE "SET.*($SENSITIVE_FIELDS)"; then
      RISK="L4"
      echo "WARNING: touching sensitive fields (password/token/secret/balance etc.)"
    fi
    ;;
  DROP|TRUNCATE)
    RISK="L4"
    echo "WARNING: irreversible DDL operation"
    ;;
  ALTER)
    RISK="L3"
    if echo "$SQL" | grep -qi "DROP COLUMN"; then
      RISK="L4"
      echo "WARNING: dropping column, data loss"
    fi
    ;;
  GRANT)
    RISK="L4"
    echo "WARNING: privilege escalation"
    ;;
  *)
    RISK="L4"
    echo "WARNING: unknown SQL type, defaulting to L4"
    ;;
esac

echo "RISK_LEVEL=$RISK"
echo "SQL_TYPE=$sql_type"

if [ "$RISK" = "L3" ] || [ "$RISK" = "L4" ]; then
  echo "REQUIREMENT=backup+confirm"
  if [ "$RISK" = "L4" ]; then
    echo "CONFIRM_TEXT=我确认执行"
  else
    echo "CONFIRM_TEXT=y"
  fi
fi

echo "---"
echo "下一步："
case "$RISK" in
  L1) echo "可直接执行" ;;
  L2) echo "记录操作日志后执行" ;;
  L3) echo "必须先备份受影响行，再等用户确认（y/yes）" ;;
  L4) echo "必须全表备份 + 二次确认（\"我确认执行\"）" ;;
esac
