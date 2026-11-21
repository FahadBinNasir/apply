$BackupDir = if ($env:BACKUP_DIR) { $env:BACKUP_DIR } else { ".\backups" }
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Dest = Join-Path $BackupDir "backup_$Timestamp"

New-Item -ItemType Directory -Force -Path $Dest | Out-Null

Write-Host "[BACKUP] Backing up SQLite database..."
docker run --rm -v apply_app_data:/data -v "${PWD}/${Dest}":/backup alpine `
  sh -c "cp -r /data/db /backup/ && cp -r /data/cvs /backup/ 2>/dev/null || true"

Write-Host "[BACKUP] Backing up WhatsApp session..."
docker run --rm -v apply_wa_session:/data -v "${PWD}/${Dest}":/backup alpine `
  sh -c "tar -czf /backup/wa_session.tar.gz -C /data ."

Write-Host "[BACKUP] Backup completed successfully at $Dest"
