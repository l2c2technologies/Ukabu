# ========================================
# UKABU WAF v1.0 - Component A (ukabu-core)
# Priority-Based Enforcement Logic
# Copyright (c) 2025 by L2C2 Technologies. All rights reserved.
# ========================================
#
# This file implements the decision tree for access control
# Include in main location{} block at the very top
#
# Priority Order (highest to lowest):
#   1. IP Blacklist → Block (444)
#   2. Path Blacklist (not whitelisted IP) → Block (444)
#   3. IP Whitelist → Allow (Status: 101)
#   4. Path Whitelist → Allow (Status: 100)
#   5. Search Engine → Allow (Status: 102) [Component D (ukabu-extras)]
#   6. Domain Not Protected → Allow (Status: 104)
#   7. Valid PoW Token → Allow (Status: 103)
#   8. Browser → Challenge (Status: 200)
#   9. Non-Browser → Block 406 (Status: 201)
#
# ========================================

# ────────────────────────────────────────────────────────────────
# PRIORITY 1: IP Blacklist (Component B (ukabu-monitor) - ipset)
# ────────────────────────────────────────────────────────────────
# Component A (ukabu-core): Structure present, but ipset integration is Component B (ukabu-monitor)
# IPs in blacklist are dropped at firewall before reaching nginx
# Status: 001 (logged by daemon, not by nginx)
# ────────────────────────────────────────────────────────────────

# if ($is_ip_blacklisted) {
#     # Component B (ukabu-monitor): This will be enforced by ipset/iptables
#     # nginx won't see these requests
#     return 444;
# }

# ────────────────────────────────────────────────────────────────
# PRIORITY 2: Path Blacklist
# ────────────────────────────────────────────────────────────────
# Block requests to blacklisted paths
# UNLESS IP is whitelisted (exception)
# Status: 002
# ────────────────────────────────────────────────────────────────

if ($is_path_blacklisted) {
    set $block_check "${is_ip_whitelisted}";
    
    # If IP is NOT whitelisted, block
    if ($block_check = "0") {
        # Set status for logging
        set $ukabu_status "002";
        set $ukabu_decision "path_blacklisted";
        
        # Add status header
        add_header X-Ukabu-Status "002" always;
        
        # Close connection without response
        return 444;
    }
}

# ────────────────────────────────────────────────────────────────
# PRIORITY 3: IP Whitelist
# ────────────────────────────────────────────────────────────────
# Whitelisted IPs bypass ALL PoW challenges
# Status: 101
# ────────────────────────────────────────────────────────────────

if ($is_ip_whitelisted) {
    # Set status for logging
    set $ukabu_status "101";
    set $ukabu_decision "ip_whitelisted";
    
    # Add status header
    add_header X-Ukabu-Status "101" always;
    
    # Continue to upstream (no return, just fall through)
    # nginx will proxy_pass to upstream
}

# ────────────────────────────────────────────────────────────────
# PRIORITY 4: Path Whitelist (Exempt Paths)
# ────────────────────────────────────────────────────────────────
# Paths like /static/*, /favicon.ico bypass PoW
# Status: 100
# ────────────────────────────────────────────────────────────────

if ($is_path_whitelisted) {
    # Set status for logging
    set $ukabu_status "100";
    set $ukabu_decision "path_whitelisted";
    
    # Add status header
    add_header X-Ukabu-Status "100" always;
    
    # Continue to upstream
}

# ────────────────────────────────────────────────────────────────
# PRIORITY 5: Search Engine Detection (Component D (ukabu-extras))
# ────────────────────────────────────────────────────────────────
# Verified search engine crawlers bypass PoW
# Status: 102
# Component A (ukabu-core): Always returns 0 (disabled)
# ────────────────────────────────────────────────────────────────

if ($is_search_engine) {
    # Component D (ukabu-extras): Will verify Google/Bing IPs
    # set $ukabu_status "102";
    # set $ukabu_decision "search_engine";
    # add_header X-Ukabu-Status "102" always;
}

# ────────────────────────────────────────────────────────────────
# PRIORITY 6: Domain Not Protected
# ────────────────────────────────────────────────────────────────
# If domain not in protected list, allow through
# Status: 104
# ────────────────────────────────────────────────────────────────

if ($pow_protected = 0) {
    # Set status for logging
    set $ukabu_status "104";
    set $ukabu_decision "domain_not_protected";
    
    # Add status header
    add_header X-Ukabu-Status "104" always;
    
    # Continue to upstream
}

# ────────────────────────────────────────────────────────────────
# PRIORITY 7: Valid PoW Token
# ────────────────────────────────────────────────────────────────
# Check if client has valid pow_token cookie
# Token validated by NJS module
# Status: 103
# ────────────────────────────────────────────────────────────────

# Call NJS to validate token
js_var $pow_token_valid pow.validateToken;

if ($pow_token_valid = "1") {
    # Set status for logging
    set $ukabu_status "103";
    set $ukabu_decision "valid_token";
    
    # Add status header
    add_header X-Ukabu-Status "103" always;
    
    # Continue to upstream
}

# ────────────────────────────────────────────────────────────────
# PRIORITY 8: Browser Detection → Redirect to Challenge
# ────────────────────────────────────────────────────────────────
# If User-Agent looks like a browser, redirect to PoW challenge
# Status: 200
# ────────────────────────────────────────────────────────────────

set $challenge_redirect "";

if ($pow_protected = 1) {
    set $challenge_redirect "A";
}

if ($pow_token_valid != "1") {
    set $challenge_redirect "${challenge_redirect}B";
}

if ($is_browser = 1) {
    set $challenge_redirect "${challenge_redirect}C";
}

if ($challenge_redirect = "ABC") {
    # Set status for logging
    set $ukabu_status "200";
    set $ukabu_decision "challenge_issued";
    
    # Add status header
    add_header X-Ukabu-Status "200" always;
    
    # Redirect to challenge page with return URL
    return 302 /ukabu_verify?redirect=$request_uri;
}

# ────────────────────────────────────────────────────────────────
# PRIORITY 9: Non-Browser → Block
# ────────────────────────────────────────────────────────────────
# If not a browser (bots, scrapers, curl), block with 406
# Status: 201
# ────────────────────────────────────────────────────────────────

set $block_nonbrowser "";

if ($pow_protected = 1) {
    set $block_nonbrowser "A";
}

if ($pow_token_valid != "1") {
    set $block_nonbrowser "${block_nonbrowser}B";
}

if ($is_browser != 1) {
    set $block_nonbrowser "${block_nonbrowser}C";
}

if ($block_nonbrowser = "ABC") {
    # Set status for logging
    set $ukabu_status "201";
    set $ukabu_decision "non_browser_blocked";
    
    # Add status header
    add_header X-Ukabu-Status "201" always;
    
    # Return 406 Not Acceptable
    return 406 "Browser required for verification. JavaScript must be enabled.\n";
}

# ────────────────────────────────────────────────────────────────
# DEFAULT: Allow (if we reach here)
# ────────────────────────────────────────────────────────────────
# This should rarely happen, but if request passed all checks
# and none of the above conditions matched, allow through
# ────────────────────────────────────────────────────────────────

# If ukabu_status not set, set default
if ($ukabu_status = "-") {
    set $ukabu_status "000";
    set $ukabu_decision "default_allow";
    add_header X-Ukabu-Status "000" always;
}

# ────────────────────────────────────────────────────────────────
# END OF ENFORCEMENT
# ────────────────────────────────────────────────────────────────
# Request continues to proxy_pass or other handlers
# ────────────────────────────────────────────────────────────────
