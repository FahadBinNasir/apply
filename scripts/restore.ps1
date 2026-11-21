param (
    [Parameter(Mandatory=$true)]
    [string]$BackupPath
)

if (-not (Test-Path $BackupPath)) {
    Write-Error "Directory $BackupPath does not exist"
    exit 1
}

Write-Host "[RESTORE] Restoring SQLite database and files..."
docker run --rm -v apply_app_data:/data -v "${PWD}/${BackupPath}":/backup alpine `
  sh -c "cp -r /backup/db/* /data/db/ && cp -r /backup/cvs/* /data/cvs/ 2>/dev/null || true"

$WaArchive = Join-Path $BackupPath "wa_session.tar.gz"
if (Test-Path $WaArchive) {
    Write-Host "[RESTORE] Restoring WhatsApp session..."
    docker run --rm -v apply_wa_session:/data -v "${PWD}/${BackupPath}":/backup alpine `
      sh -c "tar -xzf /backup/wa_session.tar.gz -C /data"
}

Write-Host "[RESTORE] Restore completed successfully."
