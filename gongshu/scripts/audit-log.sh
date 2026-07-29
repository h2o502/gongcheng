#!/bin/bash
# gongshu audit-log.sh — 写入审计日志
# 用法: bash audit-log.sh "<级别>" "<表>" "<操作类型>" "<影响行数>" "<备份位置>" "<回滚SQL路径>" "[项目日志路径]"

set -euo pipefail

LEVEL="$1"
TABLE="$2"
OP_TYPE="$3"
ROWS="$4"
BACKUP_LOC="${5:-none}"
ROLLBACK_LOC="${6:-none}"
PROJECT_LOG="${7:-}"  # 可选：项目级日志路径

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# 日志路径：优先 /var/log，fallback 到 /tmp
LOG_FILE="/var/log/ai-data-ops.log"
if [ ! -w "/var/log" ]; then
  LOG_FILE="/tmp/ai-data-ops.log"
fi

LOG_LINE="[${TIMESTAMP}] ${LEVEL} | ai-assistant | ${TABLE} | ${OP_TYPE} | ${ROWS} rows | backup=${BACKUP_LOC} | rollback=${ROLLBACK_LOC}"

echo "$LOG_LINE" >> "$LOG_FILE"

# 如提供了项目级日志路径，同时写入
if [ -n "$PROJECT_LOG" ]; then
  mkdir -p "$(dirname "$PROJECT_LOG")" 2>/dev/null || true
  echo "$LOG_LINE" >> "$PROJECT_LOG"
  echo "审计日志已写入:"
  echo "  - $LOG_FILE"
  echo "  - $PROJECT_LOG"
else
  echo "审计日志已写入:"
  echo "  - $LOG_FILE"
fi

echo ""
echo "日志内容: $LOG_LINE"
