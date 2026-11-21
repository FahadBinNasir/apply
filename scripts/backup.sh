#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DEST="${BACKUP_DIR}/backup_${TIMESTAMP}"

mkdir -p "${DEST}"

echo "[BACKUP] Backing up SQLite database..."
docker run --rm -v apply_app_data:/data -v "$(pwd)/${DEST}":/backup alpine \
  sh -c "cp -r /data/db /backup/ && cp -r /data/cvs /backup/ 2>/dev/null || true"

echo "[BACKUP] Backing up WhatsApp session..."
docker run --rm -v apply_wa_session:/data -v "$(pwd)/${DEST}":/backup alpine \
  sh -c "tar -czf /backup/wa_session.tar.gz -C /data ."

echo "[BACKUP] Backup completed successfully at ${DEST}"
