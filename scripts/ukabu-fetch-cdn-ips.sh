#!/bin/bash
# Copyright (c) 2025 by L2C2 Technologies. All rights reserved.
# 
# For licensing inquiries, contact:
# Indranil Das Gupta <indradg@l2c2.co.in>

#
# ukabu-fetch-cdn-ips.sh - Fetch trusted proxy IP ranges from CDN providers
# Runs daily via systemd timer at 3:00 AM
#

set -euo pipefail

# Configuration
CONFIG_DIR="/etc/ukabu/config"
LOG_FILE="/var/log/ukabu/cdn-updates.log"
TEMP_DIR="/tmp/ukabu-cdn-$$"

# Create temp directory
mkdir -p "$TEMP_DIR"
trap "rm -rf $TEMP_DIR" EXIT

# Logging function
log() {
    echo "[$(date -Iseconds)] $1" | tee -a "$LOG_FILE"
}

# Fetch Cloudflare IPs
fetch_cloudflare() {
    log "Fetching Cloudflare IP ranges..."
    
    local ipv4_url="https://www.cloudflare.com/ips-v4"
    local output="$CONFIG_DIR/trusted_proxies_cloudflare.conf"
    local temp="$TEMP_DIR/cloudflare.conf"
    
    # Fetch IPv4 ranges
    if curl -sf "$ipv4_url" -o "$temp"; then
        # Count ranges
        local count=$(wc -l < "$temp")
        
        # Write with header
        {
            echo "# Cloudflare trusted proxy IP ranges"
            echo "# Auto-generated: $(date -Iseconds)"
            echo "# Source: $ipv4_url"
            echo "# Last update: $(date -Iseconds) ($count ranges fetched)"
            echo ""
            while IFS= read -r ip_range; do
                echo "$ip_range 1;"
            done < "$temp"
        } > "$output"
        
        log "âœ“ Cloudflare: Updated $count IP ranges"
        return 0
    else
        log "âœ— Cloudflare: Failed to fetch IPs"
        return 1
    fi
}

# Fetch AWS CloudFront IPs
fetch_aws() {
    log "Fetching AWS CloudFront IP ranges..."
    
    local url="https://ip-ranges.amazonaws.com/ip-ranges.json"
    local output="$CONFIG_DIR/trusted_proxies_aws.conf"
    local temp="$TEMP_DIR/aws.json"
    
    if curl -sf "$url" -o "$temp"; then
        # Extract CloudFront IPv4 ranges using jq
        if command -v jq &> /dev/null; then
            local count=$(jq -r '.prefixes[] | select(.service=="CLOUDFRONT") | .ip_prefix' "$temp" | wc -l)
            
            {
                echo "# AWS CloudFront trusted proxy IP ranges"
                echo "# Auto-generated: $(date -Iseconds)"
                echo "# Source: $url"
                echo "# Last update: $(date -Iseconds) ($count ranges fetched)"
                echo ""
                jq -r '.prefixes[] | select(.service=="CLOUDFRONT") | .ip_prefix' "$temp" | while IFS= read -r ip_range; do
                    echo "$ip_range 1;"
                done
            } > "$output"
            
            log "âœ“ AWS CloudFront: Updated $count IP ranges"
            return 0
        else
            log "âœ— AWS: jq not installed, skipping"
            return 1
        fi
    else
        log "âœ— AWS: Failed to fetch IPs"
        return 1
    fi
}

# Fetch Google Cloud CDN IPs
fetch_google() {
    log "Fetching Google Cloud CDN IP ranges..."
    
    local url="https://www.gstatic.com/ipranges/cloud.json"
    local output="$CONFIG_DIR/trusted_proxies_google.conf"
    local temp="$TEMP_DIR/google.json"
    
    if curl -sf "$url" -o "$temp"; then
        if command -v jq &> /dev/null; then
            local count=$(jq -r '.prefixes[] | select(.ipv4Prefix) | .ipv4Prefix' "$temp" | wc -l)
            
            {
                echo "# Google Cloud CDN trusted proxy IP ranges"
                echo "# Auto-generated: $(date -Iseconds)"
                echo "# Source: $url"
                echo "# Last update: $(date -Iseconds) ($count ranges fetched)"
                echo ""
                jq -r '.prefixes[] | select(.ipv4Prefix) | .ipv4Prefix' "$temp" | while IFS= read -r ip_range; do
                    echo "$ip_range 1;"
                done
            } > "$output"
            
            log "âœ“ Google Cloud: Updated $count IP ranges"
            return 0
        else
            log "âœ— Google Cloud: jq not installed, skipping"
            return 1
        fi
    else
        log "âœ— Google Cloud: Failed to fetch IPs"
        return 1
    fi
}

# Fetch DigitalOcean Spaces CDN IPs
fetch_digitalocean() {
    log "Fetching DigitalOcean Spaces CDN IP ranges..."
    
    # DigitalOcean doesn't publish a comprehensive list
    # Using known data center ranges
    local output="$CONFIG_DIR/trusted_proxies_digitalocean.conf"
    
    {
        echo "# DigitalOcean Spaces CDN trusted proxy IP ranges"
        echo "# Auto-generated: $(date -Iseconds)"
        echo "# Note: Based on known data center ranges"
        echo "# Last update: $(date -Iseconds)"
        echo ""
        echo "# NYC1"
        echo "198.199.64.0/18 1;"
        echo "# NYC2"
        echo "192.241.128.0/17 1;"
        echo "# NYC3"
        echo "162.243.0.0/16 1;"
        echo "# SFO1"
        echo "107.170.0.0/16 1;"
        echo "# SFO2"
        echo "159.203.0.0/16 1;"
        echo "# AMS2"
        echo "188.166.0.0/16 1;"
        echo "# AMS3"
        echo "178.62.0.0/16 1;"
        echo "# SGP1"
        echo "128.199.0.0/16 1;"
        echo "# LON1"
        echo "178.62.0.0/16 1;"
        echo "# FRA1"
        echo "46.101.0.0/16 1;"
        echo "# TOR1"
        echo "159.203.0.0/16 1;"
        echo "# BLR1"
        echo "139.59.0.0/16 1;"
    } > "$output"
    
    log "âœ“ DigitalOcean: Updated known ranges"
    return 0
}

# Main execution
main() {
    log "=========================================="
    log "Starting CDN IP update process"
    
    # Create config directory if needed
    mkdir -p "$CONFIG_DIR"
    
    # Track success/failure
    local success=0
    local failed=0
    
    # Fetch from each provider
    if fetch_cloudflare; then
        ((success++))
    else
        ((failed++))
    fi
    
    if fetch_aws; then
        ((success++))
    else
        ((failed++))
    fi
    
    if fetch_google; then
        ((success++))
    else
        ((failed++))
    fi
    
    if fetch_digitalocean; then
        ((success++))
    else
        ((failed++))
    fi
    
    log "Completed: $success successful, $failed failed"
    
    # Regenerate nginx config if any succeeded
    if [ $success -gt 0 ]; then
        log "Triggering nginx config regeneration..."
        
        if command -v ukabu-manager &> /dev/null; then
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
                    log "âœ— nginx config test failed, not reloading"
                fi
            else
                log "âœ— nginx config regeneration failed"
            fi
        else
            log "Warning: ukabu-manager not found, skipping nginx reload"
        fi
    fi
    
    log "CDN IP update completed"
    log "=========================================="
    
    # Return 0 if at least one succeeded
    [ $success -gt 0 ]
}

# Run main function
main
