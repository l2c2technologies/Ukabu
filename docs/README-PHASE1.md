# UKABU WAF - Component A (ukabu-core): nginx PoW Flow

**Copyright (c) 2025 by L2C2 Technologies. All rights reserved.**

For licensing inquiries, contact:
- Indranil Das Gupta <indradg@l2c2.co.in>

---

## Component A (ukabu-core) Objectives

Get a working Proof-of-Work challenge that a browser can complete:

âœ… Browser can load challenge page  
âœ… Challenge is generated with valid HMAC  
âœ… Browser solves PoW (SHA-256 mining)  
âœ… Solution validates correctly  
âœ… Token is issued as cookie  
âœ… Subsequent requests with valid token bypass challenge  
âœ… Invalid/expired tokens trigger re-challenge  
âœ… No-JS users see helpful error page  

## What's Included

### Core nginx Components
- `etc/ukabu/includes/config.conf` - nginx variables and maps
- `etc/ukabu/includes/endpoints.inc` - PoW endpoint definitions
- `etc/ukabu/includes/enforcement.inc` - Priority-based access control logic
- `etc/ukabu/njs/pow-challenge.js` - NJS module for challenge/validation

### HTML Pages
- `etc/ukabu/pages/challenge.html` - Interactive PoW challenge page
- `etc/ukabu/pages/nojs-chrome.html` - No-JS error (Chrome)
- `etc/ukabu/pages/nojs-firefox.html` - No-JS error (Firefox)
- `etc/ukabu/pages/nojs-edge.html` - No-JS error (Edge)
- `etc/ukabu/pages/nojs-safari.html` - No-JS error (Safari)
- `etc/ukabu/pages/nojs-generic.html` - No-JS error (generic)
- `etc/ukabu/pages/blocked.html` - Blocked IP information page

### Configuration Examples
- `etc/ukabu/config/domains.json` - Domain configuration
- `etc/ukabu/config/ip_whitelist.conf` - IP whitelist
- `etc/ukabu/config/ip_blacklist.conf` - IP blacklist (Component B (ukabu-monitor))
- `etc/ukabu/config/path_whitelist.conf` - Global path exemptions
- `etc/ukabu/config/path_blacklist.conf` - Global path blocks
- `etc/ukabu/secrets/example.com.key` - HMAC secret example

### Example Configuration
- `examples/example-vhost.conf` - Working vhost configuration

## What's NOT Included (Future Phases)

âŒ Strike tracking and automatic blocking (Component B (ukabu-monitor))  
âŒ ipset integration (Component B (ukabu-monitor))  
âŒ CLI management tools (Component C (ukabu-manager))  
âŒ Search engine detection (Component D (ukabu-extras))  
âŒ XFF/CDN handling (Component D (ukabu-extras))  
âŒ ML logging and extraction (Component D (ukabu-extras))  

## Installation

### Prerequisites

```bash
# Install nginx with njs module
sudo apt-get install nginx nginx-module-njs

# Or on RHEL/Rocky/Alma
sudo yum install nginx nginx-module-njs
```

### Setup

```bash
# 1. Extract tarball
tar -xzf ukabu-component1.tar.gz
cd ukabu-component1

# 2. Create directory structure
sudo mkdir -p /etc/ukabu/{includes,njs,pages,config,secrets}
sudo mkdir -p /var/log/ukabu
sudo mkdir -p /var/lib/ukabu

# 3. Copy files
sudo cp -r etc/ukabu/* /etc/ukabu/

# 4. Set permissions
sudo chmod 600 /etc/ukabu/secrets/*.key
sudo chown root:root /etc/ukabu/secrets/*.key

# 5. Generate HMAC secrets for your domains
# For now, edit /etc/ukabu/secrets/yourdomain.com.key manually
# Component C (ukabu-manager) CLI will automate this

# 6. Configure your domains
sudo nano /etc/ukabu/config/domains.json
# Add your domain, set difficulty, paths, etc.

# 7. Load njs module in nginx.conf
# Add to top of nginx.conf:
#   load_module modules/ngx_http_js_module.so;

# 8. Include UKABU in your vhost
# See examples/example-vhost.conf for reference

# 9. Test nginx configuration
sudo nginx -t

# 10. Reload nginx
sudo systemctl reload nginx
```

## Configuration

### 1. Domain Setup

Edit `/etc/ukabu/config/domains.json`:

```json
{
  "default": {
    "pow_difficulty": 18,
    "cookie_duration": 604800,
    "lockout_period": 10080,
    "excuse_first_timeout": false,
    "xff_handling": {
      "enabled": false
    }
  },
  "domains": {
    "example.com": {
      "pow_difficulty": 18,
      "hmac_secret_file": "/etc/ukabu/secrets/example.com.key",
      "cookie_duration": 604800,
      "lockout_period": 10080,
      "exempt_paths": [
        "/static/*",
        "/images/*",
        "/favicon.ico",
        "/robots.txt"
      ],
      "restricted_paths": {},
      "xff_handling": {
        "enabled": false
      }
    }
  }
}
```

### 2. HMAC Secret

Create `/etc/ukabu/secrets/example.com.key`:

```
hmac_secret=your-32-plus-character-cryptographically-secure-random-string-here
hmac_secret_old=
rotation_expires=
```

Generate a secure secret:
```bash
openssl rand -base64 48
```

### 3. IP Whitelist

Edit `/etc/ukabu/config/ip_whitelist.conf`:

```
# Office network
192.168.1.0/24

# Monitoring server
10.0.0.5

# Individual trusted IP
203.0.113.100
```

### 4. Path Whitelist

Edit `/etc/ukabu/config/path_whitelist.conf`:

```
# Static assets (prefix match)
/static/*
/assets/*
/images/*
/css/*
/js/*

# Specific files
/favicon.ico
/robots.txt
/sitemap.xml

# Health checks
/health
/ping
```

### 5. Path Blacklist

Edit `/etc/ukabu/config/path_blacklist.conf`:

```
# WordPress admin (if not using WordPress)
/wp-admin/*
/wp-login.php

# Common attack targets
/.git/*
/.env
/phpmyadmin/*
/.well-known/security.txt
```

## Testing

### Test 1: Basic Challenge Flow

```bash
# Request without token (should redirect to challenge)
curl -I -H "User-Agent: Mozilla/5.0" http://example.com/protected-page

# Expected: 302 redirect to /ukabu_verify?redirect=/protected-page
# X-Ukabu-Status: 200
```

### Test 2: Challenge Page

```bash
# Visit in browser
firefox http://example.com/ukabu_verify?redirect=/

# Should see challenge page with progress bar
# After solving (~30 seconds), should redirect to /
```

### Test 3: Static Assets (Path Whitelist)

```bash
# Request static asset
curl -I http://example.com/static/style.css

# Expected: 200 OK (no challenge)
# X-Ukabu-Status: 100
```

### Test 4: Whitelisted IP

```bash
# From whitelisted IP
curl -I http://example.com/protected-page

# Expected: 200 OK (no challenge)
# X-Ukabu-Status: 101
```

### Test 5: No JavaScript

```bash
# Request with JS disabled
# Visit in browser with NoScript extension
firefox http://example.com/protected-page

# Should redirect to /ukabu_help
# Shows browser-specific instructions
```

### Test 6: Non-Browser Client

```bash
# Plain curl (no User-Agent pretending to be browser)
curl -I http://example.com/protected-page

# Expected: 406 Not Acceptable
# X-Ukabu-Status: 201
```

## Status Codes (Component A (ukabu-core))

| Code | Meaning | Component A (ukabu-core) Support |
|------|---------|-----------------|
| 001 | IP Blacklisted | âŒ Component B (ukabu-monitor) (daemon) |
| 002 | Path Blacklisted | âœ… Yes (444 response) |
| 100 | Path Whitelisted | âœ… Yes |
| 101 | IP Whitelisted | âœ… Yes |
| 102 | Search Engine | âŒ Component D (ukabu-extras) |
| 103 | Valid PoW Token | âœ… Yes |
| 104 | Domain Not Protected | âœ… Yes |
| 200 | Browser Redirected | âœ… Yes |
| 201 | Non-Browser Blocked | âœ… Yes |

## Troubleshooting

### Challenge not loading

```bash
# Check nginx error log
sudo tail -f /var/log/nginx/error.log

# Check njs module loaded
nginx -V 2>&1 | grep njs

# Check endpoints accessible
curl -v http://example.com/ukabu_challenge
```

### Token not being set

```bash
# Check cookie in browser DevTools
# Application > Cookies > pow_token

# Check HMAC secret is loaded
# Should be readable by nginx user
sudo -u www-data cat /etc/ukabu/secrets/example.com.key
```

### Challenge solving too slow/fast

```bash
# Adjust difficulty in domains.json
# 12 bits = ~1-2 seconds (testing)
# 18 bits = ~30 seconds (default)
# 20 bits = ~2 minutes (high security)

# Edit /etc/ukabu/config/domains.json
"pow_difficulty": 12  # For faster testing
```

### Path whitelist not working

```bash
# Check map syntax in nginx
sudo nginx -t

# Check path matching (prefix vs exact)
# /static/* matches /static/css/style.css
# /api/health matches /api/health only (not /api/health/check)

# Test with curl
curl -I -H "Accept: text/html" http://example.com/static/test.css
# Should see X-Ukabu-Status: 100
```

## File Locations

```
/etc/ukabu/
â”œâ”€â”€ config/
â”‚   â”œâ”€â”€ domains.json              # Domain configuration
â”‚   â”œâ”€â”€ ip_whitelist.conf         # Whitelisted IPs
â”‚   â”œâ”€â”€ ip_blacklist.conf         # Blacklisted IPs (Component B (ukabu-monitor))
â”‚   â”œâ”€â”€ path_whitelist.conf       # Global exempt paths
â”‚   â””â”€â”€ path_blacklist.conf       # Global blocked paths
â”œâ”€â”€ includes/
â”‚   â”œâ”€â”€ config.conf               # nginx variables/maps
â”‚   â”œâ”€â”€ endpoints.inc             # PoW endpoints
â”‚   â””â”€â”€ enforcement.inc           # Access control logic
â”œâ”€â”€ njs/
â”‚   â””â”€â”€ pow-challenge.js          # NJS challenge module
â”œâ”€â”€ pages/
â”‚   â”œâ”€â”€ challenge.html            # PoW challenge page
â”‚   â”œâ”€â”€ nojs-*.html              # No-JS error pages
â”‚   â””â”€â”€ blocked.html             # Blocked IP page
â””â”€â”€ secrets/
    â””â”€â”€ *.key                     # HMAC secrets (600 perms)

/var/log/ukabu/                   # Logs (Component B (ukabu-monitor)+)
/var/lib/ukabu/                   # State data (Component B (ukabu-monitor)+)
```

## Next Steps

After Component A (ukabu-core) is working:

1. **Component B (ukabu-monitor)**: Add Go daemon for strike tracking and automatic blocking
2. **Component C (ukabu-manager)**: Add Python CLI for configuration management
3. **Component D (ukabu-extras)**: Add search engine detection, XFF handling, ML extraction
4. **Phase 5**: Add monitoring, Prometheus exporter, documentation

## Support

For issues, questions, or licensing:
- Email: indradg@l2c2.co.in
- Organization: L2C2 Technologies

---

**UKABU WAF** - Collaborative Anti-AI Scraper Bot Web Application Firewall
