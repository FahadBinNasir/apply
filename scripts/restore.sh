#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <path_to_backup_folder>"
    exit 1
fi

SRC="$1"
if [ ! -d "${SRC}" ]; then
    echo "Error: Directory ${SRC} does not exist"
    exit 1
fi

echo "[RESTORE] Restoring SQLite database and files..."
docker run --rm -v apply_app_data:/data -v "$(pwd)/${SRC}":/backup alpine \
  sh -c "cp -r /backup/db/* /data/db/ && cp -r /backup/cvs/* /data/cvs/ 2>/dev/null || true"

if [ -f "${SRC}/wa_session.tar.gz" ]; then
    echo "[RESTORE] Restoring WhatsApp session..."
    docker run --rm -v apply_wa_session:/data -v "$(pwd)/${SRC}":/backup alpine \
      sh -c "tar -xzf /backup/wa_session.tar.gz -C /data"
fi

echo "[RESTORE] Restore completed successfully."
