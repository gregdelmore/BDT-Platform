#!/bin/bash

# BDT Platform - Automated Backup Script
# Performs complete backup of databases, files, and configurations
# Run via cron: 0 2 * * * /opt/bdt/scripts/backup.sh

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/backups/bdt}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="bdt_backup_${TIMESTAMP}"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"
LOG_FILE="${BACKUP_DIR}/backup.log"

# Database credentials
DB_HOST="${DB_HOST:-postgres}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-bdt}"
DB_PASSWORD="${DB_PASSWORD:-bdt123}"
DB_NAMES="bdt_poc bdt_security bdt_monitoring"

# S3 configuration (optional)
S3_BUCKET="${S3_BUCKET:-}"
S3_PREFIX="${S3_PREFIX:-backups}"
AWS_REGION="${AWS_REGION:-us-east-1}"

# Notification settings
SLACK_WEBHOOK="${SLACK_WEBHOOK:-}"
EMAIL_TO="${EMAIL_TO:-}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "${LOG_FILE}"
}

# Error handling
error_exit() {
    log "ERROR: $1"
    send_notification "error" "Backup failed: $1"
    exit 1
}

# Send notifications
send_notification() {
    local status=$1
    local message=$2
    
    # Slack notification
    if [ -n "${SLACK_WEBHOOK}" ]; then
        local color="danger"
        local emoji=":x:"
        if [ "${status}" = "success" ]; then
            color="good"
            emoji=":white_check_mark:"
        fi
        
        curl -X POST "${SLACK_WEBHOOK}" \
            -H 'Content-Type: application/json' \
            -d "{
                \"attachments\": [{
                    \"color\": \"${color}\",
                    \"title\": \"BDT Backup ${status^}\",
                    \"text\": \"${message}\",
                    \"footer\": \"Timestamp: ${TIMESTAMP}\"
                }]
            }" 2>/dev/null || true
    fi
    
    # Email notification
    if [ -n "${EMAIL_TO}" ]; then
        echo "${message}" | mail -s "BDT Backup ${status^} - ${TIMESTAMP}" "${EMAIL_TO}" || true
    fi
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check required commands
    for cmd in pg_dump mongodump redis-cli tar gzip; do
        if ! command -v ${cmd} &> /dev/null; then
            error_exit "Required command '${cmd}' not found"
        fi
    done
    
    # Check disk space
    available_space=$(df "${BACKUP_DIR}" | awk 'NR==2 {print $4}')
    required_space=5242880  # 5GB in KB
    if [ "${available_space}" -lt "${required_space}" ]; then
        error_exit "Insufficient disk space. Available: ${available_space}KB, Required: ${required_space}KB"
    fi
    
    # Create backup directory
    mkdir -p "${BACKUP_PATH}"
    
    log "Prerequisites check passed"
}

# Backup PostgreSQL databases
backup_postgres() {
    log "Starting PostgreSQL backup..."
    
    local pg_backup_dir="${BACKUP_PATH}/postgres"
    mkdir -p "${pg_backup_dir}"
    
    export PGPASSWORD="${DB_PASSWORD}"
    
    for db in ${DB_NAMES}; do
        log "Backing up database: ${db}"
        
        # Full database dump
        pg_dump \
            -h "${DB_HOST}" \
            -p "${DB_PORT}" \
            -U "${DB_USER}" \
            -d "${db}" \
            --format=custom \
            --verbose \
            --no-owner \
            --no-privileges \
            --compress=9 \
            --file="${pg_backup_dir}/${db}.dump" \
            2>&1 | tee -a "${LOG_FILE}" || error_exit "Failed to backup database ${db}"
        
        # Also create SQL format for easy inspection
        pg_dump \
            -h "${DB_HOST}" \
            -p "${DB_PORT}" \
            -U "${DB_USER}" \
            -d "${db}" \
            --format=plain \
            --no-owner \
            --no-privileges \
            --file="${pg_backup_dir}/${db}.sql" \
            2>&1 | tee -a "${LOG_FILE}" || true
        
        # Compress SQL file
        gzip "${pg_backup_dir}/${db}.sql"
    done
    
    # Backup global objects (roles, tablespaces)
    pg_dumpall \
        -h "${DB_HOST}" \
        -p "${DB_PORT}" \
        -U "${DB_USER}" \
        --globals-only \
        --file="${pg_backup_dir}/globals.sql" \
        2>&1 | tee -a "${LOG_FILE}" || true
    
    gzip "${pg_backup_dir}/globals.sql"
    
    unset PGPASSWORD
    log "PostgreSQL backup completed"
}

# Backup Redis
backup_redis() {
    log "Starting Redis backup..."
    
    local redis_backup_dir="${BACKUP_PATH}/redis"
    mkdir -p "${redis_backup_dir}"
    
    # Trigger Redis backup
    redis-cli -h redis -p 6379 BGSAVE
    
    # Wait for backup to complete
    while [ "$(redis-cli -h redis -p 6379 LASTSAVE)" = "$(redis-cli -h redis -p 6379 LASTSAVE)" ]; do
        sleep 1
    done
    
    # Copy dump file
    if [ -f "/data/dump.rdb" ]; then
        cp /data/dump.rdb "${redis_backup_dir}/dump.rdb"
        log "Redis backup completed"
    else
        log "WARNING: Redis dump file not found"
    fi
}

# Backup Qdrant vector database
backup_qdrant() {
    log "Starting Qdrant backup..."
    
    local qdrant_backup_dir="${BACKUP_PATH}/qdrant"
    mkdir -p "${qdrant_backup_dir}"
    
    # Create snapshot via API
    curl -X POST "http://qdrant:6333/snapshots" \
        -H "Content-Type: application/json" \
        -o "${qdrant_backup_dir}/snapshot.json" \
        2>/dev/null || log "WARNING: Failed to create Qdrant snapshot"
    
    log "Qdrant backup attempted"
}

# Backup configuration files
backup_configs() {
    log "Starting configuration backup..."
    
    local config_backup_dir="${BACKUP_PATH}/configs"
    mkdir -p "${config_backup_dir}"
    
    # List of configuration files to backup
    local config_files=(
        "/app/.env"
        "/app/docker-compose.yml"
        "/app/nginx/nginx.conf"
        "/app/monitoring/prometheus.yml"
        "/app/api-gateway/kong.yml"
    )
    
    for file in "${config_files[@]}"; do
        if [ -f "${file}" ]; then
            cp "${file}" "${config_backup_dir}/" || true
        fi
    done
    
    # Backup Kubernetes manifests if available
    if command -v kubectl &> /dev/null; then
        kubectl get all --all-namespaces -o yaml > "${config_backup_dir}/k8s-all.yaml" 2>/dev/null || true
        kubectl get configmaps --all-namespaces -o yaml > "${config_backup_dir}/k8s-configmaps.yaml" 2>/dev/null || true
        kubectl get secrets --all-namespaces -o yaml > "${config_backup_dir}/k8s-secrets.yaml" 2>/dev/null || true
    fi
    
    log "Configuration backup completed"
}

# Backup uploaded files and documents
backup_files() {
    log "Starting file backup..."
    
    local files_backup_dir="${BACKUP_PATH}/files"
    mkdir -p "${files_backup_dir}"
    
    # Backup uploaded documents
    if [ -d "/data/uploads" ]; then
        tar -czf "${files_backup_dir}/uploads.tar.gz" -C /data uploads/ 2>/dev/null || true
    fi
    
    # Backup processed files
    if [ -d "/data/processed" ]; then
        tar -czf "${files_backup_dir}/processed.tar.gz" -C /data processed/ 2>/dev/null || true
    fi
    
    # Backup logs
    if [ -d "/var/log/bdt" ]; then
        tar -czf "${files_backup_dir}/logs.tar.gz" -C /var/log bdt/ 2>/dev/null || true
    fi
    
    log "File backup completed"
}

# Create metadata file
create_metadata() {
    log "Creating backup metadata..."
    
    cat > "${BACKUP_PATH}/metadata.json" <<EOF
{
    "timestamp": "${TIMESTAMP}",
    "version": "$(git describe --tags 2>/dev/null || echo 'unknown')",
    "hostname": "$(hostname)",
    "databases": ${DB_NAMES},
    "size": "$(du -sh ${BACKUP_PATH} | cut -f1)",
    "retention_days": ${RETENTION_DAYS}
}
EOF
    
    log "Metadata created"
}

# Compress backup
compress_backup() {
    log "Compressing backup..."
    
    cd "${BACKUP_DIR}"
    tar -czf "${BACKUP_NAME}.tar.gz" "${BACKUP_NAME}/"
    
    # Calculate checksum
    sha256sum "${BACKUP_NAME}.tar.gz" > "${BACKUP_NAME}.tar.gz.sha256"
    
    # Remove uncompressed directory
    rm -rf "${BACKUP_NAME}"
    
    log "Backup compressed: ${BACKUP_NAME}.tar.gz"
}

# Upload to S3 (optional)
upload_to_s3() {
    if [ -z "${S3_BUCKET}" ]; then
        log "S3 backup skipped (S3_BUCKET not configured)"
        return 0
    fi
    
    log "Uploading backup to S3..."
    
    aws s3 cp \
        "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz" \
        "s3://${S3_BUCKET}/${S3_PREFIX}/${BACKUP_NAME}.tar.gz" \
        --region "${AWS_REGION}" \
        --storage-class STANDARD_IA \
        --metadata "timestamp=${TIMESTAMP}" \
        || error_exit "Failed to upload backup to S3"
    
    # Upload checksum
    aws s3 cp \
        "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz.sha256" \
        "s3://${S3_BUCKET}/${S3_PREFIX}/${BACKUP_NAME}.tar.gz.sha256" \
        --region "${AWS_REGION}" \
        || true
    
    log "Backup uploaded to S3: s3://${S3_BUCKET}/${S3_PREFIX}/${BACKUP_NAME}.tar.gz"
}

# Clean old backups
cleanup_old_backups() {
    log "Cleaning old backups..."
    
    # Local cleanup
    find "${BACKUP_DIR}" -name "bdt_backup_*.tar.gz" -mtime +${RETENTION_DAYS} -delete
    find "${BACKUP_DIR}" -name "bdt_backup_*.tar.gz.sha256" -mtime +${RETENTION_DAYS} -delete
    
    # S3 cleanup
    if [ -n "${S3_BUCKET}" ]; then
        aws s3 ls "s3://${S3_BUCKET}/${S3_PREFIX}/" \
            --region "${AWS_REGION}" \
            | grep "bdt_backup_" \
            | while read -r line; do
                backup_date=$(echo "${line}" | awk '{print $1}')
                backup_file=$(echo "${line}" | awk '{print $4}')
                
                if [ "$(date -d "${backup_date}" +%s 2>/dev/null)" -lt "$(date -d "-${RETENTION_DAYS} days" +%s)" ]; then
                    aws s3 rm "s3://${S3_BUCKET}/${S3_PREFIX}/${backup_file}" --region "${AWS_REGION}" || true
                fi
            done
    fi
    
    log "Old backups cleaned"
}

# Verify backup
verify_backup() {
    log "Verifying backup..."
    
    # Check file exists and has size
    if [ ! -f "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz" ]; then
        error_exit "Backup file not found"
    fi
    
    local backup_size=$(stat -c%s "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz")
    if [ "${backup_size}" -lt 1024 ]; then
        error_exit "Backup file too small: ${backup_size} bytes"
    fi
    
    # Verify checksum
    cd "${BACKUP_DIR}"
    sha256sum -c "${BACKUP_NAME}.tar.gz.sha256" || error_exit "Checksum verification failed"
    
    # Test archive integrity
    tar -tzf "${BACKUP_NAME}.tar.gz" > /dev/null || error_exit "Archive integrity check failed"
    
    log "Backup verified successfully"
}

# Generate backup report
generate_report() {
    log "Generating backup report..."
    
    local report_file="${BACKUP_DIR}/backup_report_${TIMESTAMP}.txt"
    
    {
        echo "BDT Platform Backup Report"
        echo "=========================="
        echo ""
        echo "Timestamp: ${TIMESTAMP}"
        echo "Backup Name: ${BACKUP_NAME}"
        echo "Total Size: $(du -sh ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz | cut -f1)"
        echo ""
        echo "Components Backed Up:"
        echo "- PostgreSQL databases: ${DB_NAMES}"
        echo "- Redis data"
        echo "- Qdrant vectors"
        echo "- Configuration files"
        echo "- Uploaded files"
        echo ""
        echo "Location:"
        echo "- Local: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
        if [ -n "${S3_BUCKET}" ]; then
            echo "- S3: s3://${S3_BUCKET}/${S3_PREFIX}/${BACKUP_NAME}.tar.gz"
        fi
        echo ""
        echo "Retention: ${RETENTION_DAYS} days"
        echo ""
        echo "Status: SUCCESS"
    } > "${report_file}"
    
    log "Report generated: ${report_file}"
}

# Main execution
main() {
    log "=== Starting BDT Platform Backup ==="
    
    # Trap errors
    trap 'error_exit "Backup failed at line $LINENO"' ERR
    
    # Execute backup steps
    check_prerequisites
    backup_postgres
    backup_redis
    backup_qdrant
    backup_configs
    backup_files
    create_metadata
    compress_backup
    upload_to_s3
    verify_backup
    cleanup_old_backups
    generate_report
    
    # Send success notification
    local backup_size=$(du -sh "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz" | cut -f1)
    send_notification "success" "Backup completed successfully. Size: ${backup_size}"
    
    log "=== Backup completed successfully ==="
}

# Run main function
main "$@"
