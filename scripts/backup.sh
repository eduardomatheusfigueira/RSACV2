#!/usr/bin/env bash
# ==============================================================================
# Revsist — Script de Backup Diário Criptografado (doc 40 §40.7.6, doc 41 Tarefa 4.11)
# ==============================================================================
# Executa dump binário do PostgreSQL, empacota PDFs, cifra com age e expurga
# backups com mais de 30 dias (LGPD Art. 16, L-34).
# ==============================================================================

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/backups}"
DATA_DIR="${DATA_DIR:-/data}"
POSTGRES_HOST="${POSTGRES_HOST:-db}"
POSTGRES_USER="${POSTGRES_USER:-rsac}"
POSTGRES_DB="${POSTGRES_DB:-rsac}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
AGE_KEY="${AGE_RECIPIENT_KEY:-}"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
TEMP_WORK_DIR=$(mktemp -d)
trap 'rm -rf "${TEMP_WORK_DIR}"' EXIT

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Iniciando rotina de backup do Revsist..."
mkdir -p "${BACKUP_DIR}"

# 1. Dump do banco de dados PostgreSQL
DB_DUMP="${TEMP_WORK_DIR}/db_${POSTGRES_DB}_${TIMESTAMP}.dump"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Exportando banco PostgreSQL..."
export PGPASSWORD="${POSTGRES_PASSWORD}"
pg_dump -h "${POSTGRES_HOST}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -Fc -f "${DB_DUMP}"

# 2. Compactação dos arquivos PDF
PDF_ARCHIVE="${TEMP_WORK_DIR}/pdfs_${TIMESTAMP}.tar.gz"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Empacotando arquivos PDFs..."
if [ -d "${DATA_DIR}/pdfs" ]; then
    tar -czf "${PDF_ARCHIVE}" -C "${DATA_DIR}" pdfs
else
    tar -czf "${PDF_ARCHIVE}" --files-from /dev/null
fi

# 3. Pacote combinado
BUNDLE="${TEMP_WORK_DIR}/revsist_backup_${TIMESTAMP}.tar"
tar -cf "${BUNDLE}" -C "${TEMP_WORK_DIR}" "$(basename "${DB_DUMP}")" "$(basename "${PDF_ARCHIVE}")"

# 4. Criptografia com age (se chave pública configurada)
FINAL_FILE="${BACKUP_DIR}/revsist_backup_${TIMESTAMP}.tar"
if [ -n "${AGE_KEY}" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Cifrando backup com age..."
    age -r "${AGE_KEY}" -o "${FINAL_FILE}.age" "${BUNDLE}"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backup cifrado gerado: ${FINAL_FILE}.age"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] AVISO: AGE_RECIPIENT_KEY não configurada. Armazenando em claro."
    mv "${BUNDLE}" "${FINAL_FILE}"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backup gerado: ${FINAL_FILE}"
fi

# 5. Expurgo de backups antigos (> RETENTION_DAYS)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Aplicando política de retenção (${RETENTION_DAYS} dias)..."
find "${BACKUP_DIR}" -type f -name "revsist_backup_*" -mtime +"${RETENTION_DAYS}" -exec rm -f {} +

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Rotina de backup concluída com sucesso."
