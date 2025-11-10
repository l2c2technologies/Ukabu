#!/bin/bash
# Copyright (c) 2025 by L2C2 Technologies. All rights reserved.
#
# UKABU WAF - Unjail Script
# Removes expired entries from ip_blacklist.conf and updates ipsets

set -euo pipefail

# Configuration
BLACKLIST_FILE="/etc/ukabu/config/ip_blacklist.conf"
TEMP_FILE="${BLACKLIST_FILE}.tmp"
BACKUP_DIR="/etc/ukabu/config/.backups"
LOG_FILE="/var/log/ukabu/unjail.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] $1" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
    log "INFO: $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    log "WARN: $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    log "ERROR: $1"
}

# Parse ISO 8601 timestamp to epoch
iso_to_epoch() {
    local timestamp=$1
    date -d "$timestamp" +%s 2>/dev/null || echo 0
}

# Get current epoch time
current_epoch() {
    date +%s
}

# Remove IP from ipset
remove_from_ipset() {
    local ip=$1
    local found=false
    
    # Check all temporary ipsets
    for ipset_name in $(ipset list -n | grep "ukabu-temporary"); do
        if ipset test "$ipset_name" "$ip" 2>/dev/null; then
            ipset del "$ipset_name" "$ip" 2>/dev/null && {
                log_info "Removed $ip from $ipset_name"
                found=true
            }
        fi
    done
    
    if [ "$found" = false ]; then
        log_warn "IP $ip not found in any ipset"
    fi
}

# Main unjail logic
main() {
    log_info "Starting unjail check..."
    
    # Check if blacklist file exists
    if [ ! -f "$BLACKLIST_FILE" ]; then
        log_warn "Blacklist file not found: $BLACKLIST_FILE"
        exit 0
    fi
    
    # Create backup directory if it doesn't exist
    mkdir -p "$BACKUP_DIR"
    
    # Backup current blacklist
    cp "$BLACKLIST_FILE" "${BACKUP_DIR}/ip_blacklist.conf.$(date +%Y%m%d-%H%M%S)"
    
    local now=$(current_epoch)
    local expired_count=0
    local kept_count=0
    local permanent_count=0
    
    # Create temporary file
    : > "$TEMP_FILE"
    
    # Process each line in blacklist
    while IFS= read -r line; do
        # Skip empty lines and comments
        [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
        
        # Try to parse JSON
        if echo "$line" | jq empty 2>/dev/null; then
            ip=$(echo "$line" | jq -r '.ip_address')
            timestamp=$(echo "$line" | jq -r '.timestamp')
            lockout_period=$(echo "$line" | jq -r '.lockout_period')
            
            # Check if permanent (lockout_period = 0)
            if [ "$lockout_period" = "0" ]; then
                echo "$line" >> "$TEMP_FILE"
                ((permanent_count++))
                continue
            fi
            
            # Calculate expiry
            block_epoch=$(iso_to_epoch "$timestamp")
            expiry_epoch=$((block_epoch + lockout_period * 60))
            
            if [ "$now" -ge "$expiry_epoch" ]; then
                log_info "Expired: $ip (blocked at $timestamp, lockout ${lockout_period}m)"
                remove_from_ipset "$ip"
                ((expired_count++))
            else
                # Keep the entry
                echo "$line" >> "$TEMP_FILE"
                ((kept_count++))
            fi
        else
            # Invalid JSON, keep it but log warning
            log_warn "Invalid JSON line, keeping: $line"
            echo "$line" >> "$TEMP_FILE"
        fi
    done < "$BLACKLIST_FILE"
    
    # Replace blacklist with cleaned version
    mv "$TEMP_FILE" "$BLACKLIST_FILE"
    
    log_info "Unjail complete: $expired_count removed, $kept_count temporary kept, $permanent_count permanent"
    
    # If there were any changes, rotate logs
    if [ "$expired_count" -gt 0 ]; then
        log_info "Blacklist updated successfully"
    fi
}

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Run main function
main "$@"
