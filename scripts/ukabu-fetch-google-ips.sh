#!/bin/bash
# Copyright (c) 2025 by L2C2 Technologies. All rights reserved.
# 
# For licensing inquiries, contact:
# Indranil Das Gupta <indradg@l2c2.co.in>

#
# ukabu-fetch-google-ips.sh - Fetch Google bot IP ranges
# Runs daily via systemd timer at 3:05 AM
#

set -euo pipefail

# Configuration
CONFIG_DIR="/etc/ukabu/config"
OUTPUT_FILE="$CONFIG_DIR/search_engines_google.conf"
LOG_FILE="/var/log/ukabu/search-engines.log"
TEMP_FILE="/tmp/ukabu-google-ips-$$.json"

trap "rm -f $TEMP_FILE" EXIT

# Logging function
log() {
    echo "[$(date -Iseconds)] GOOGLE: $1" | tee -a "$LOG_FILE"
}

# Main execution
main() {
    log "Fetching Google bot IP ranges..."
    
    local url="https://www.gstatic.com/ipranges/goog.json"
    
    # Fetch JSON
    if ! curl -sf "$url" -o "$TEMP_FILE"; then
        log "âœ— Failed to fetch from $url"
        return 1
    fi
    
    # Check if jq is available
    if ! command -v jq &> /dev/null; then
        log "âœ— jq not installed, cannot parse JSON"
        return 1
    fi
    
    # Extract IPv4 prefixes
    local count=$(jq -r '.prefixes[] | select(.ipv4Prefix) | .ipv4Prefix' "$TEMP_FILE" | wc -l)
    
    if [ "$count" -eq 0 ]; then
        log "âœ— No IPv4 ranges found in response"
        return 1
    fi
    
    # Write to config file
    {
        echo "# Google bot IP ranges"
        echo "# Auto-generated: $(date -Iseconds)"
        echo "# Source: $url"
        echo "# Last update: $(date -Iseconds) ($count ranges fetched)"
        echo ""
        jq -r '.prefixes[] | select(.ipv4Prefix) | .ipv4Prefix' "$TEMP_FILE"
    } > "$OUTPUT_FILE"
    
    log "âœ“ Updated $count Google IP ranges"
    
    # Regenerate nginx config to update geo map
    if command -v ukabu-manager &> /dev/null; then
        log "Regenerating nginx config..."
        
        if ukabu-manager nginx generate-config >> "$LOG_FILE" 2>&1; then
            log "âœ“ nginx config regenerated"
            
            # Test nginx config
            if nginx -t >> "$LOG_FILE" 2>&1; then
                log "âœ“ nginx config test passed"
                
                # Reload nginx
                if systemctl reload nginx >> "$LOG_FILE" 2>&1; then
                    log "âœ“ nginx reloaded successfully"
                else
                    log "âœ— nginx reload failed"
                fi
            else
                log "âœ— nginx config test failed"
            fi
        else
            log "âœ— nginx config regeneration failed"
        fi
    fi
    
    return 0
}

# Run main function
main
