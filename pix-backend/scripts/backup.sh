#!/bin/sh
# Automated PostgreSQL backup script for πX RC1.
# Runs inside the backup container every day at 03:00 UTC.

set -e

BACKUP_DIR="/backups"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="${POSTGRES_DB:-pix}"
DB_USER="${POSTGRES_USER:-pix}"
DB_HOST="${POSTGRES_HOST:-postgres}"

mkdir -p "$BACKUP_DIR"

FILE="$BACKUP_DIR/pix_${DB_NAME}_${DATE}.sql.gz"

echo "Starting backup: $FILE"
pg_dump -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" | gzip > "$FILE"

# Remove old backups
find "$BACKUP_DIR" -type f -name "pix_*.sql.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: $FILE"
