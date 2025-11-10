#!/bin/bash
# Copyright (c) 2025 by L2C2 Technologies. All rights reserved.
#
# UKABU WAF - IPSet Initialization Script
# Initializes ipsets for permanent and temporary IP blocking

set -euo pipefail

# Configuration
IPSET_PERMANENT="ukabu-permanent"
IPSET_TEMP_PREFIX="ukabu-temporary"
MAX_TEMP_SETS=10
MAX_ELEMENTS=10000

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Detect if using iptables or nftables
detect_firewall() {
    if command -v iptables &> /dev/null; then
        FIREWALL="iptables"
        log_info "Using iptables"
    elif command -v nft &> /dev/null; then
        FIREWALL="nftables"
        log_info "Using nftables"
    else
        log_error "Neither iptables nor nftables found"
        exit 1
    fi
}

# Create ipset if it doesn't exist
create_ipset() {
    local name=$1
    local max_elem=${2:-$MAX_ELEMENTS}
    
    if ipset list "$name" &>/dev/null; then
        log_info "IPSet '$name' already exists"
    else
        ipset create "$name" hash:net family inet maxelem "$max_elem" timeout 0
        log_info "Created IPSet '$name' (maxelem=$max_elem)"
    fi
}

# Add iptables/nftables rule to block ipset
add_firewall_rule() {
    local ipset_name=$1
    
    if [ "$FIREWALL" = "iptables" ]; then
        # Check if rule already exists
        if ! iptables -C INPUT -m set --match-set "$ipset_name" src -j DROP 2>/dev/null; then
            iptables -I INPUT -m set --match-set "$ipset_name" src -j DROP
            log_info "Added iptables rule for '$ipset_name'"
        else
            log_info "iptables rule for '$ipset_name' already exists"
        fi
    elif [ "$FIREWALL" = "nftables" ]; then
        # For nftables, we'll add to the filter table input chain
        # Check if rule exists
        if ! nft list chain ip filter input 2>/dev/null | grep -q "@$ipset_name"; then
            nft add rule ip filter input ip saddr @"$ipset_name" drop
            log_info "Added nftables rule for '$ipset_name'"
        else
            log_info "nftables rule for '$ipset_name' already exists"
        fi
    fi
}

# Main initialization
main() {
    log_info "Initializing UKABU IPSets..."
    
    # Detect firewall backend
    detect_firewall
    
    # Create permanent blacklist ipset
    create_ipset "$IPSET_PERMANENT" 50000
    add_firewall_rule "$IPSET_PERMANENT"
    
    # Create temporary ipsets (for time-limited blocks)
    for i in $(seq 0 $((MAX_TEMP_SETS - 1))); do
        create_ipset "${IPSET_TEMP_PREFIX}_${i}" $MAX_ELEMENTS
        add_firewall_rule "${IPSET_TEMP_PREFIX}_${i}"
    done
    
    # Create whitelist ipset (for exempt IPs)
    create_ipset "ukabu-whitelist" 10000
    log_info "Created IPSet 'ukabu-whitelist' (for exempt IPs)"
    
    log_info "IPSet initialization complete!"
    log_info "Created sets:"
    echo "  - $IPSET_PERMANENT (permanent blocks)"
    for i in $(seq 0 $((MAX_TEMP_SETS - 1))); do
        echo "  - ${IPSET_TEMP_PREFIX}_${i} (temporary blocks)"
    done
    echo "  - ukabu-whitelist (whitelisted IPs)"
    
    # Show current ipset list
    log_info "Current IPSets:"
    ipset list -n | grep ukabu || true
}

# Run main function
main "$@"
