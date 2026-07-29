#!/bin/bash
# gongshu auto-backup.sh — 自动创建备份表 + 生成回滚 SQL
# 用法: bash auto-backup.sh "<表名>" "<WHERE条件>" "<数据库连接名>" "<敏感字段>"
# 会创建: backup_<table>_<YYYYMMDD> 和 audit_<table>_<YYYYMMDD>（如有敏感字段）

set -euo pipefail

TABLE="$1"
WHERE_CLAUSE="$2"
DB_NAME="${3:-default}"
SENSITIVE_FIELD="${4:-}"

DATE=$(date +%Y%m%d)
TIMESTAMP=$(date +%Y%m%d%H%M)

BACKUP_TABLE="backup_${TABLE}_${DATE}"
AUDIT_TABLE="audit_${TABLE}_${DATE}"
ROLLBACK_FILE="/tmp/rollback_${TABLE}_${TIMESTAMP}.sql"

echo "=== gongshu 自动备份 ==="
echo "目标表: $TABLE"
echo "WHERE 条件: ${WHERE_CLAUSE:-（无，全表）}"
echo "备份表: $BACKUP_TABLE"
echo "回滚文件: $ROLLBACK_FILE"
echo ""

# 生成备份 SQL
if [ -z "$WHERE_CLAUSE" ]; then
  BACKUP_SQL="CREATE TABLE IF NOT EXISTS ${BACKUP_TABLE} AS SELECT * FROM ${TABLE};"
else
  BACKUP_SQL="CREATE TABLE IF NOT EXISTS ${BACKUP_TABLE} AS SELECT * FROM ${TABLE} WHERE ${WHERE_CLAUSE};"
fi

echo "-- 备份 SQL --"
echo "$BACKUP_SQL"
echo ""

# 如有敏感字段，额外创建审计表
if [ -n "$SENSITIVE_FIELD" ]; then
  if [ -z "$WHERE_CLAUSE" ]; then
    AUDIT_SQL="CREATE TABLE IF NOT EXISTS ${AUDIT_TABLE} AS SELECT id, ${SENSITIVE_FIELD}, NOW() AS snapshot_time FROM ${TABLE};"
    ROLLBACK_SQL="UPDATE ${TABLE} t JOIN ${AUDIT_TABLE} a ON t.id = a.id SET t.${SENSITIVE_FIELD} = a.${SENSITIVE_FIELD};"
  else
    AUDIT_SQL="CREATE TABLE IF NOT EXISTS ${AUDIT_TABLE} AS SELECT id, ${SENSITIVE_FIELD}, NOW() AS snapshot_time FROM ${TABLE} WHERE ${WHERE_CLAUSE};"
    ROLLBACK_SQL="UPDATE ${TABLE} t JOIN ${AUDIT_TABLE} a ON t.id = a.id SET t.${SENSITIVE_FIELD} = a.${SENSITIVE_FIELD} WHERE ${WHERE_CLAUSE};"
  fi

  echo "-- 敏感字段审计 SQL --"
  echo "$AUDIT_SQL"
  echo ""
  echo "-- 回滚 SQL --"
  echo "$ROLLBACK_SQL"
  echo "$ROLLBACK_SQL" > "$ROLLBACK_FILE"
  echo ""
  echo "回滚 SQL 已写入: $ROLLBACK_FILE"
else
  # 通用回滚（从备份表恢复）
  if [ -z "$WHERE_CLAUSE" ]; then
    ROLLBACK_SQL="INSERT INTO ${TABLE} SELECT * FROM ${BACKUP_TABLE};"
  else
    ROLLBACK_SQL="INSERT INTO ${TABLE} SELECT * FROM ${BACKUP_TABLE} WHERE ${WHERE_CLAUSE};"
  fi
  echo "-- 回滚 SQL（从备份表恢复）--"
  echo "$ROLLBACK_SQL"
  echo "$ROLLBACK_SQL" > "$ROLLBACK_FILE"
  echo ""
  echo "回滚 SQL 已写入: $ROLLBACK_FILE"
fi

echo ""
echo "=== 备份脚本生成完成 ==="
echo "请在执行原 SQL 前，先执行上述备份 SQL。"
