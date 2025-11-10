# ========================================
# UKABU WAF v1.0 - Component A (ukabu-core)
# PoW Endpoints Configuration
# Copyright (c) 2025 by L2C2 Technologies. All rights reserved.
# ========================================
#
# This file defines all UKABU endpoints
# Include in server{} block BEFORE main location
#
# ========================================

# ────────────────────────────────────────────────────────────────
# User-Facing Endpoints (visible in browser)
# ────────────────────────────────────────────────────────────────

# Main PoW Challenge Page
location = /ukabu_verify {
    # Serve challenge.html
    alias /etc/ukabu/pages/challenge.html;
    
    # No caching
    add_header Cache-Control "no-store, no-cache, must-revalidate";
    add_header Pragma "no-cache";
    add_header Expires "0";
    
    # Security headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    
    # CORS for challenge page
    add_header Access-Control-Allow-Origin "*";
    
    # Log access
    access_log /var/log/nginx/access.log ukabu_combined;
}

# No-JavaScript Help Page (browser-specific)
location = /ukabu_help {
    # Serve appropriate browser-specific page
    # Based on $detected_browser variable
    
    default_type text/html;
    
    # Try to serve browser-specific page, fallback to generic
    try_files /etc/ukabu/pages/nojs-$detected_browser.html
              /etc/ukabu/pages/nojs-generic.html;
    
    # Alias to pages directory
    root /;
    
    # No caching
    add_header Cache-Control "no-store, no-cache, must-revalidate";
    add_header Pragma "no-cache";
    add_header Expires "0";
    
    # Security headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    
    # Log access
    access_log /var/log/nginx/access.log ukabu_combined;
}

# Blocked IP Information Page
location = /ukabu_blocked {
    # Serve blocked.html
    alias /etc/ukabu/pages/blocked.html;
    
    # No caching
    add_header Cache-Control "no-store, no-cache, must-revalidate";
    add_header Pragma "no-cache";
    add_header Expires "0";
    
    # Security headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    
    # Log access
    access_log /var/log/nginx/access.log ukabu_combined;
}

# ────────────────────────────────────────────────────────────────
# API Endpoints (called by JavaScript)
# ────────────────────────────────────────────────────────────────

# Generate PoW Challenge
location = /ukabu_challenge {
    # Call NJS function
    js_content pow.generateChallenge;
    
    # JSON content type
    default_type application/json;
    
    # No caching
    add_header Cache-Control "no-store, no-cache, must-revalidate";
    add_header Pragma "no-cache";
    add_header Expires "0";
    
    # CORS headers
    add_header Access-Control-Allow-Origin "*";
    add_header Access-Control-Allow-Methods "GET, OPTIONS";
    add_header Access-Control-Allow-Headers "Content-Type";
    
    # Rate limiting (prevent challenge flooding)
    limit_req zone=ukabu_challenge burst=5 nodelay;
    
    # Log access
    access_log /var/log/nginx/access.log ukabu_combined;
}

# Validate PoW Solution
location = /ukabu_validate {
    # Call NJS function
    js_content pow.validateSolution;
    
    # JSON content type
    default_type application/json;
    
    # Only allow POST
    limit_except POST {
        deny all;
    }
    
    # Read request body
    client_body_buffer_size 16k;
    client_max_body_size 16k;
    
    # No caching
    add_header Cache-Control "no-store, no-cache, must-revalidate";
    add_header Pragma "no-cache";
    add_header Expires "0";
    
    # CORS headers
    add_header Access-Control-Allow-Origin "*";
    add_header Access-Control-Allow-Methods "POST, OPTIONS";
    add_header Access-Control-Allow-Headers "Content-Type";
    
    # Rate limiting (prevent brute force)
    limit_req zone=ukabu_validate burst=3 nodelay;
    
    # Log access
    access_log /var/log/nginx/access.log ukabu_combined;
}

# ────────────────────────────────────────────────────────────────
# Rate Limiting Zones (define in http{} block)
# ────────────────────────────────────────────────────────────────
# Add to nginx.conf http{} block:
#
# limit_req_zone $binary_remote_addr zone=ukabu_challenge:10m rate=10r/s;
# limit_req_zone $binary_remote_addr zone=ukabu_validate:10m rate=3r/s;
#
# ────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────
# END OF ENDPOINTS
# ────────────────────────────────────────────────────────────────
