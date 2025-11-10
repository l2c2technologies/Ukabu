# UKABU WAF - Project Decisions & Requirements
**Version:** 1.0  
**Date:** 2025-11-09  
**Status:** Finalized

**Copyright:** Copyright (c) 2025 by L2C2 Technologies. All rights reserved.

**Licensing Contact:**
- Indranil Das Gupta
- Email: indradg@l2c2.co.in
- Organization: L2C2 Technologies

---

## Executive Summary

UKABU is a collaborative anti-AI scraper bot WAF architected around nginx as a reverse proxy for multi-tenant solutions. It uses JavaScript-based proof-of-work (SHA-256) challenges to distinguish real browsers from automated bots, with intelligent strike tracking and IP blocking mechanisms.

### Two-Layer Defense Architecture

```
                         Client Request
                               â†“
    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
    â”‚  LAYER 1: Kernel/Firewall (iptables + ipset)        â”‚
    â”‚  â€¢ Known bad IPs dropped BEFORE nginx                â”‚
    â”‚  â€¢ <1ms response time                                â”‚
    â”‚  â€¢ Zero nginx overhead                               â”‚
    â”‚  â€¢ Client: Connection timeout                        â”‚
    â”‚  â€¢ Status: 001 (daemon log only)                     â”‚
    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                               â†“
                   (Only if IP not blacklisted)
                               â†“
    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
    â”‚  LAYER 2: nginx Application Logic                   â”‚
    â”‚  â€¢ PoW challenge system                              â”‚
    â”‚  â€¢ Token validation                                  â”‚
    â”‚  â€¢ Path-based rules                                  â”‚
    â”‚  â€¢ Strike tracking â†’ feeds back to Layer 1          â”‚
    â”‚  â€¢ Status: 002, 100-104, 200-201 (HTTP responses)  â”‚
    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                               â†“
                     Protected Application
```

**Key Innovation:** Firewall speed + Application intelligence = Maximum protection with minimal overhead

---

## Quick Reference - All Finalized Decisions

| # | Decision Area | Choice |
|---|---------------|--------|
| **1** | Failure types counting as strikes | Timeout + invalid solution + HMAC failure (not expired challenge) |
| **2** | Strike timeout behavior | Permanent until successful PoW or lockout expiry |
| **3** | First timeout rule | Optional per-domain: can excuse first timeout (disabled by default) |
| **4** | nginxâ†’daemon communication | Unix socket (real-time, JSON protocol) |
| **5** | Path matching for exempt paths | Prefix match (e.g., `/opac-tmpl/*` matches all subpaths) |
| **6** | Config file structure | Single master file: `/etc/ukabu/config/domains.json` |
| **7** | Strike counter reset | On successful PoW OR lockout TTL expiry |
| **8** | Search engine detection | Google: IP whitelist (daily update)<br>Bing: Reverse DNS verification |
| **9** | Restricted paths behavior | Complete PoW bypass for whitelisted IPs |
| **10** | HMAC secret rotation | 12-hour grace period (both secrets valid) |
| **11** | Daemon strike persistence | SQLite at `/var/lib/ukabu/strikes.db` |
| **12** | X-Forwarded-For handling | **Disabled by default** (secure default), enable per-domain with auto-updating CDN proxies (CF, AWS, GOOG, DO) |
| **13** | Request logging for ML | nginx `$request_id` in logs, on-demand extraction |
| **14** | Log fields | Add: `$request_time`, `$upstream_response_time`, `$ssl_protocol`, `$ssl_cipher` |
| **15** | nginx config generation | Auto-generate on save (Option 1) |
| **16** | Secret storage | Separate files: `/etc/ukabu/secrets/*.key` (Option 2) |
| **17** | Log format | Structured JSON for ukabu logs |
| **18** | journald usage | Only for systemd unit/timer errors |
| **19** | Installation method | Manual installation (v1.0), packages later |
| **20** | Implementation path | Path C: Critical Path (core flow first) |
| **21** | Copyright & Licensing | Â© 2025 L2C2 Technologies - Contact: indradg@l2c2.co.in |
| **22** | ukabu-manager operations | All CRUD operations must be **idempotent** (no duplicates) |

**âš ï¸ Important Architectural Note:**
UKABU uses a **two-layer blocking system**:
1. **Layer 1 (Firewall):** Known bad IPs blocked at kernel level (iptables/nftables + ipset) **before** reaching nginx - zero nginx overhead
2. **Layer 2 (nginx):** Application logic for PoW challenges, token validation, path-based rules

**Status Code 001** (IP Blacklisted) appears **only in daemon logs**, never as an HTTP response. Blocked IPs experience connection timeouts.

---

---

## Project Standards

### Copyright & Attribution

**All project files must include appropriate copyright notices:**

**1. Source Code Files** (Go, Python, JavaScript, shell scripts):
```bash
# Copyright (c) 2025 by L2C2 Technologies. All rights reserved.
# 
# For licensing inquiries, contact:
# Indranil Das Gupta <indradg@l2c2.co.in>
```

**2. HTML Files** (challenge pages, error pages):
```html
<div class="footer">
    Copyright (c) 2025 by L2C2 Technologies. All rights reserved.
</div>
```

**3. Configuration Files** (nginx configs, JSON):
```nginx
# ========================================
# UKABU WAF - [Component Name]
# Copyright (c) 2025 by L2C2 Technologies. All rights reserved.
# ========================================
```

**4. Documentation Files** (Markdown, text):
```markdown
---
Copyright (c) 2025 by L2C2 Technologies. All rights reserved.

For licensing inquiries, contact:
Indranil Das Gupta <indradg@l2c2.co.in>
---
```

**5. README and Setup Scripts:**
Must prominently display copyright and licensing contact information at the beginning.

---

## Core Architecture Decisions

### 1. Technology Stack
- **Web Server:** nginx (reverse proxy)
- **PoW Module:** nginx-njs (JavaScript module for challenge generation/validation)
- **Strike Tracking:** Go daemon (ukabu-trackerd)
- **Management CLI:** Python (ukabu-manager)
- **Monitoring:** Go (ukabu-monitor with Prometheus exporter)
- **Persistence:** SQLite for strike tracking
- **Firewall:** ipset + iptables/nftables (auto-detected)

### 2. Key Components

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚  nginx (reverse proxy)                                      â”‚
â”‚  â€¢ PoW challenge pages (challenge.html, nojs-chrome.html)  â”‚
â”‚  â€¢ NJS module (pow-challenge.js)                            â”‚
â”‚  â€¢ Access logs with unique request serials                  â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
             â”‚
             â”œâ”€â†’ Unix socket â†’ ukabu-trackerd (Go daemon)
             â”‚                 â€¢ Strike tracking (in-memory + SQLite)
             â”‚                 â€¢ ipset management
             â”‚                 â€¢ Metrics endpoint (:9090/metrics)
             â”‚
             â””â”€â†’ Access logs â†’ ukabu-manager (Python CLI)
                               â€¢ On-demand ML extraction
                               â€¢ Domain/IP/path management
                               â€¢ Configuration management
```

---

## Finalized Decisions

### âœ… 1. Failure Types & Strike Logic

**What counts as a strike:**
- âœ“ A: Never submitted solution (timeout after 5 minutes)
- âœ“ B: Invalid solution (wrong nonce)
- âœ“ D: HMAC verification failed (tampering)

**Note:** Expired challenge (C) is treated as timeout (A) - challenge expiry is 5 minutes.

**Optional leniency rule (per-domain setting):**
- **Default:** All timeouts count as strikes
- **Optional:** "Excuse first timeout" can be enabled per-domain
  - First timeout (A) doesn't count as strike
  - Second and subsequent timeouts count normally
  - Configurable via: `ukabu-manager domain set example.com --excuse-first-timeout true`

**How first timeout excuse works:**
```
Scenario 1: excuse_first_timeout = false (default)
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
Request 1: Timeout          â†’ Strike 1
Request 2: Timeout          â†’ Strike 2
Request 3: Timeout          â†’ Strike 3 â†’ BLOCKED

Scenario 2: excuse_first_timeout = true
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
Request 1: Timeout          â†’ Excused (strike count = 0, flag set)
Request 2: Timeout          â†’ Strike 1 (no more excuses)
Request 3: Invalid solution â†’ Strike 2
Request 4: Timeout          â†’ Strike 3 â†’ BLOCKED

Scenario 3: excuse_first_timeout = true (mixed failures)
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
Request 1: Invalid solution â†’ Strike 1 (excuse only for timeouts)
Request 2: Timeout          â†’ Strike 2 (excuse not available)
Request 3: HMAC failed      â†’ Strike 3 â†’ BLOCKED
```

**Implementation notes:**
- Daemon tracks `first_timeout_excused` flag per IP/domain in SQLite
- Only applies to timeout failures (A), not invalid solutions (B) or HMAC failures (D)
- Flag persists until strike counter is reset (successful PoW or lockout expiry)
- If disabled for domain, all timeouts count immediately

**Strike persistence:** Strikes are permanent until:
- Successful PoW completion (clears all strikes), OR
- Lockout period TTL expires (configurable per-domain)

**Blocking threshold:** 3 strikes â†’ IP added to ipset â†’ blocked

---

### âœ… 2. Communication Architecture

**nginx â†’ ukabu-trackerd:** Unix socket at `/var/run/ukabu/tracker.sock`

**Protocol:** JSON messages over Unix socket

**Message types:**
```json
// Failure notification
{
  "type": "failure",
  "ip": "1.2.3.4",
  "reason": "invalid_solution|timeout|expired_challenge|hmac_failed",
  "domain": "example.com",
  "timestamp": "2025-11-09T10:30:00Z"
}

// Success notification
{
  "type": "success",
  "ip": "1.2.3.4",
  "domain": "example.com",
  "timestamp": "2025-11-09T10:30:00Z"
}

// Daemon response
{
  "strike_count": 2,
  "blocked": false,
  "lockout_expires": null
}
```

**Benefits:**
- Real-time blocking (sub-millisecond latency)
- Immediate strike updates
- Synchronous confirmation to nginx

---

### âœ… 3. Path Matching Rules

**Type:** Prefix match

**Examples:**
- `/opac-tmpl/*` â†’ matches `/opac-tmpl/css/style.css` and `/opac-tmpl/js/deep/script.js`
- `/static/*` â†’ matches all paths starting with `/static/`
- `/api/v1/health` â†’ exact match only

**Implementation:** nginx map with prefix matching logic

---

### âœ… 4. Configuration Structure

**Single master file:** `/etc/ukabu/config/domains.json`

**Schema:**
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
      "pow_difficulty": 20,
      "hmac_secret": "auto-generated-or-manual",
      "hmac_secret_old": null,
      "secret_rotation_expires": null,
      "cookie_duration": 604800,
      "lockout_period": 10080,
      "excuse_first_timeout": false,
      "exempt_paths": [
        "/opac-tmpl/*",
        "/images/*",
        "/favicon.ico",
        "/robots.txt"
      ],
      "restricted_paths": {
        "/admin/*": ["10.0.0.0/8", "192.168.1.100"],
        "/wp-admin/*": ["192.168.1.0/24"]
      },
      "xff_handling": {
        "enabled": false
      }
    },
    "cdn-site.com": {
      "pow_difficulty": 18,
      "hmac_secret": "different-secret",
      "lockout_period": 10080,
      "excuse_first_timeout": false,
      "exempt_paths": ["/static/*"],
      "xff_handling": {
        "enabled": true,
        "trusted_proxy_sources": ["cloudflare"],
        "custom_proxies": []
      }
    },
    "direct-site.com": {
      "pow_difficulty": 18,
      "hmac_secret": "another-secret",
      "lockout_period": 20160,
      "excuse_first_timeout": false,
      "exempt_paths": ["/images/*"],
      "xff_handling": {
        "enabled": false
      }
    }
  }
}
```

**Configuration notes:**
- `excuse_first_timeout: false` (default) - All timeouts count as strikes immediately
- `excuse_first_timeout: true` - First timeout per IP is excused, subsequent timeouts count
- `xff_handling.enabled: false` (default) - **Secure by default**: Only enable if YOUR nginx is behind a CDN/proxy
- Per-domain examples:
  - `example.com` - Direct connection (XFF disabled)
  - `cdn-site.com` - Behind Cloudflare (XFF enabled with trusted sources)
  - `direct-site.com` - Direct connection (XFF explicitly disabled)
- This setting is independent per domain, allowing different policies
- Example use case: Enable for public-facing site with slower connections, disable for admin interfaces

**Additional config files:**
- `/etc/ukabu/config/ip_whitelist.conf` - Line-by-line IP/CIDR list
- `/etc/ukabu/config/ip_blacklist.conf` - JSON with lockout periods
- `/etc/ukabu/config/path_whitelist.conf` - Global path exemptions
- `/etc/ukabu/config/path_blacklist.conf` - Global path blocks
- `/etc/ukabu/config/search_engines_google.conf` - Auto-updated Google IPs
- `/etc/ukabu/config/search_engines_bing.conf` - Verified Bing IPs

---

### âœ… 5. Strike Counter Reset Conditions

**Strikes are cleared when:**
1. IP successfully completes PoW challenge (immediate reset)
2. Lockout period TTL expires (automatic cleanup)

**Implementation:**
- Go daemon tracks strike TTL in-memory
- SQLite persistence ensures state survives restarts
- Background goroutine cleans expired strikes every 60 seconds

---

### âœ… 6. Search Engine Detection

**Multi-strategy approach:**

#### **Google/Googlebot:**
- **Method:** IP whitelist (auto-updated daily)
- **Source:** https://www.gstatic.com/ipranges/goog.json
- **Update:** systemd timer runs daily at 3 AM
- **Implementation:**
  ```bash
  # /usr/local/bin/ukabu-fetch-google-ips.sh
  curl -s https://www.gstatic.com/ipranges/goog.json | \
    jq -r '.prefixes[] | select(.ipv4Prefix) | .ipv4Prefix' \
    > /etc/ukabu/config/search_engines_google.conf
  ```

#### **Bing/Bingbot:**
- **Method:** Reverse DNS verification (2-step process)
- **Step 1:** Reverse DNS lookup - verify name ends with `.search.msn.com`
- **Step 2:** Forward DNS lookup - verify it resolves back to same IP
- **Implementation:** Real-time verification in ukabu-trackerd or cached batch verification

**Future support:** Yandex, Baidu, DuckDuckGo (community contributions)

---

### âœ… 7. Restricted Paths Behavior

**For whitelisted IPs accessing restricted paths:**
- **Complete PoW bypass** - no challenge, no token required
- **No strike tracking** for these IPs on these paths
- **Direct pass-through** to upstream

**Example:**
```json
"restricted_paths": {
  "/admin/*": ["10.0.0.0/8", "192.168.1.100"]
}
```

**Behavior:**
- IP `192.168.1.100` accessing `/admin/dashboard` â†’ immediate 200 OK (no PoW)
- IP `203.0.113.50` accessing `/admin/dashboard` â†’ blocked (status 002)
- IP `192.168.1.100` accessing `/public/page` â†’ normal PoW flow (if not whitelisted globally)

---

### âœ… 8. HMAC Secret Rotation

**Strategy:** 12-hour grace period

**Process:**
1. Admin runs: `ukabu-manager domain rotate-secret example.com`
2. New secret generated and stored in `hmac_secret`
3. Old secret moved to `hmac_secret_old`
4. `secret_rotation_expires` set to `now + 12 hours`
5. During grace period: nginx validates tokens against **both** secrets
6. After 12 hours: old secret purged automatically

**Token validation logic during rotation:**
```javascript
// In pow-challenge.js
function validateToken(token, timestamp, ip) {
    var expectedNew = hmac_sha256(hmac_secret, timestamp + ':' + ip);
    if (token === expectedNew) return true;
    
    if (hmac_secret_old && Date.now() < secret_rotation_expires) {
        var expectedOld = hmac_sha256(hmac_secret_old, timestamp + ':' + ip);
        if (token === expectedOld) return true;
    }
    
    return false;
}
```

**Benefits:**
- Zero downtime during rotation
- Existing users not logged out
- Secure migration window

---

### âœ… 9. Daemon Persistence

**Primary storage:** SQLite at `/var/lib/ukabu/strikes.db`

**Schema:**
```sql
CREATE TABLE strikes (
    ip TEXT PRIMARY KEY,
    domain TEXT NOT NULL,
    strike_count INTEGER NOT NULL,
    first_failure TIMESTAMP NOT NULL,
    last_failure TIMESTAMP NOT NULL,
    first_timeout_excused BOOLEAN DEFAULT 0,
    expires_at TIMESTAMP,
    UNIQUE(ip, domain)
);

CREATE INDEX idx_expires ON strikes(expires_at);
CREATE INDEX idx_domain ON strikes(domain);

CREATE TABLE blocked_ips (
    ip TEXT PRIMARY KEY,
    domain TEXT NOT NULL,
    blocked_at TIMESTAMP NOT NULL,
    lockout_expires TIMESTAMP,
    reason TEXT,
    ipset_name TEXT
);
```

**Note:** `first_timeout_excused` tracks whether this IP has already used its "first timeout excuse" for this domain (if enabled).

**In-memory cache:**
- Go daemon loads all active strikes into memory on startup
- Writes persist to SQLite every 5 seconds (batched)
- Immediate writes on critical events (3rd strike â†’ block)

**Backup strategy:**
- SQLite auto-backup via `PRAGMA wal_checkpoint` every hour
- Manual backup: `ukabu-manager backup create`

---

### âœ… 10. X-Forwarded-For Handling

**Strategy:** Disabled by default (secure default), enable per-domain as needed with auto-updating trusted proxy lists for major CDN providers

**Default Behavior:**
- XFF handling **disabled by default** for all domains (secure default)
- Only enable if nginx is behind a CDN/proxy (Cloudflare, AWS CloudFront, etc.)
- When enabled: Trusted proxies auto-updated daily for: Cloudflare, AWS, Google Cloud, DigitalOcean
- Can be enabled per-domain for sites behind CDN/proxy
- Real client IP extraction only when explicitly enabled and request is from trusted proxy

**Trusted Proxy Sources (Auto-Updated Daily):**

| Provider | Source URL | Update Mechanism |
|----------|------------|------------------|
| **Cloudflare** | https://www.cloudflare.com/ips-v4<br>https://www.cloudflare.com/ips-v6 | systemd timer |
| **AWS** | https://ip-ranges.amazonaws.com/ip-ranges.json | systemd timer |
| **Google Cloud** | https://www.gstatic.com/ipranges/cloud.json | systemd timer |
| **DigitalOcean** | https://digitalocean.com/geo/google.csv | systemd timer |

**Update Schedule:**
- **Timer:** `ukabu-update-proxies.timer` runs daily at 3:00 AM
- **Service:** `ukabu-update-proxies.service` executes update script
- **Script:** `/usr/local/bin/ukabu-fetch-cdn-ips.sh`
- **Output:** `/etc/ukabu/config/trusted_proxies_<provider>.conf`
- **Post-update:** Auto-regenerate nginx maps â†’ Test config â†’ Reload nginx
- **Logging:** `/var/log/ukabu/trusted-proxies.log`

**Configuration Structure:**

```json
{
  "default": {
    "pow_difficulty": 18,
    "cookie_duration": 604800,
    "lockout_period": 10080,
    "excuse_first_timeout": false,
    "xff_handling": {
      "enabled": false,
      "header_name": "X-Forwarded-For",
      "recursive": true,
      "trusted_proxy_sources": ["cloudflare", "aws", "google", "digitalocean"],
      "custom_proxies": []
    }
  },
  "domains": {
    "example.com": {
      "pow_difficulty": 20,
      "xff_handling": {
        "enabled": false
      }
    },
    "cdn-site.com": {
      "pow_difficulty": 18,
      "xff_handling": {
        "enabled": true,
        "trusted_proxy_sources": ["cloudflare"],
        "custom_proxies": []
      }
    },
    "direct-server.com": {
      "pow_difficulty": 18,
      "xff_handling": {
        "enabled": false
      }
    }
  }
}
```

**Per-domain inheritance:**
- Domains inherit global XFF settings by default (`enabled: false` - secure default)
- Must explicitly enable XFF for domains behind CDN/proxy (opt-in security model)
- Can add custom trusted proxies (internal load balancers, reverse proxies)
- Can customize specific CDN sources via `trusted_proxy_sources: ["cloudflare"]`

**Three deployment scenarios:**

#### **Scenario A: Direct to nginx (no CDN) - DEFAULT**
```json
"xff_handling": {
  "enabled": false
}
```
- Uses `$remote_addr` directly (most secure)
- Ignores all XFF headers (prevents spoofing)
- **Default behavior** - no configuration needed
- Best for direct connections without CDN/proxy

#### **Scenario B: Behind Cloudflare (opt-in)**
```json
"xff_handling": {
  "enabled": true,
  "trusted_proxy_sources": ["cloudflare"]
}
```
- Explicitly enable XFF for this domain
- Uses global trusted proxy lists (auto-updated)
- Cloudflare IPs refreshed daily at 3 AM
- Real client IP extracted from XFF
- Prevents spoofing (only trusts Cloudflare source IPs)

#### **Scenario C: Behind HAProxy + Cloudflare**
```json
"xff_handling": {
  "enabled": true,
  "custom_proxies": ["10.0.0.5", "10.0.0.6"]
}
```
- Trusts both Cloudflare (auto) and internal HAProxy (manual)
- Recursive mode strips both proxy layers
- Gets actual client IP through chain

**Security guarantee:**
- If `$remote_addr` NOT in trusted proxies (CDN + custom) â†’ XFF ignored
- Auto-updated lists prevent stale IPs
- Manual custom proxies for internal infrastructure
- Attacker cannot spoof from non-trusted source

**nginx implementation:**
```nginx
# Auto-generated from trusted proxy sources + custom
geo $trusted_proxy {
    default 0;
    
    # Auto-updated CDN ranges
    include /etc/ukabu/config/trusted_proxies_cloudflare.conf;
    include /etc/ukabu/config/trusted_proxies_aws.conf;
    include /etc/ukabu/config/trusted_proxies_google.conf;
    include /etc/ukabu/config/trusted_proxies_digitalocean.conf;
    
    # Custom proxies (manually configured)
    include /etc/ukabu/config/trusted_proxies_custom.conf;
}

map $trusted_proxy:$http_x_forwarded_for $real_client_ip {
    ~^1:(.+)$ $1;           # Trust XFF if from trusted proxy
    default $remote_addr;   # Otherwise use direct IP
}
```

**Trusted proxy files format:**
```nginx
# /etc/ukabu/config/trusted_proxies_cloudflare.conf
# Auto-generated: 2025-11-09 03:00:00 UTC
# Source: https://www.cloudflare.com/ips-v4
# Last update: 2025-11-09 03:00:15 UTC (45 ranges fetched)
173.245.48.0/20 1;
103.21.244.0/22 1;
103.22.200.0/22 1;
103.31.4.0/22 1;
# ... (all Cloudflare IPv4 ranges)
```

```nginx
# /etc/ukabu/config/trusted_proxies_custom.conf
# Custom trusted proxies (manual configuration)
# Updated: 2025-11-09 via ukabu-manager
10.0.0.5 1;        # Internal HAProxy
10.0.0.6 1;        # Internal HAProxy (backup)
192.168.1.100 1;   # Office gateway
```

---

### âœ… 11. Logging Architecture

**nginx access log format:**
```nginx
log_format combined_enhanced '$host $remote_addr - $remote_user [$time_iso8601] '
                             '"$request" $status $body_bytes_sent '
                             '"$http_referer" "$http_user_agent" '
                             '"$ukabu_status" "$ukabu_decision" "$strike_type" '
                             '"$http_x_forwarded_for" "$request_serial" '
                             '$request_time $upstream_response_time '
                             '"$ssl_protocol" "$ssl_cipher"';
```

**Request serial generation:**
```nginx
map $pow_protected $request_serial {
    default "-";
    1 "$request_id";  # nginx built-in unique ID
}
```

**Example log line:**
```
example.com 1.2.3.4 - - [2025-11-09T10:30:45+00:00] "GET /search HTTP/1.1" 200 1234 
"https://google.com" "Mozilla/5.0..." "200" "challenge_issued" "-" 
"1.2.3.4" "8f14e45fceea167a" 0.234 0.189 "TLSv1.3" "TLS_AES_256_GCM_SHA384"
```

**Log files:**
```
/var/log/nginx/
  â”œâ”€â”€ access.log                 # Main access log (combined_enhanced format)
  â””â”€â”€ error.log                  # nginx errors

/var/log/ukabu/
  â”œâ”€â”€ trackerd.log               # Daemon operational log
  â”œâ”€â”€ failures.log               # Failed PoW attempts (from socket)
  â”œâ”€â”€ blocks.log                 # IP blocking events
  â”œâ”€â”€ search-engines.log         # Search engine IP updates
  â””â”€â”€ audit.log                  # Config changes, manual actions
```

**ML data extraction:**
- On-demand via `ukabu-manager ml extract`
- Parses nginx access.log
- Filters by request_serial (protected hosts only)
- Outputs CSV/JSON for training

**Benefits:**
- No separate ML logging pipeline needed
- Standard log rotation (logrotate)
- Query historical data anytime
- No performance impact

---

## UKABU Endpoints

All UKABU endpoints use the `/ukabu_*` namespace to prevent conflicts with existing site URLs and maintain clear separation.

### User-Facing Endpoints

These endpoints are visible in the browser address bar:

| Endpoint | Purpose | User Sees |
|----------|---------|-----------|
| `/ukabu_verify` | Main PoW challenge page | "Security Verification" page with mining progress |
| `/ukabu_help` | No-JavaScript help page | Browser-specific instructions to enable JS |
| `/ukabu_blocked` | Block information page | Explanation of why access is blocked and how to resolve |

**Example redirect:**
```
User requests: https://example.com/search
nginx redirects: https://example.com/ukabu_verify?redirect=/search
```

### API Endpoints

These endpoints are called by JavaScript (not visible to users):

| Endpoint | Method | Purpose | Returns |
|----------|--------|---------|---------|
| `/ukabu_challenge` | GET | Fetch new PoW challenge | JSON: `{challenge, hmac, difficulty}` |
| `/ukabu_validate` | POST | Submit PoW solution | JSON: `{success, redirect}` or `{success: false, error}` |

**Example API flow:**
```javascript
// 1. Fetch challenge
GET /ukabu_challenge
â† {challenge: "1731153045:a1b2c3d4", hmac: "9876...", difficulty: 18}

// 2. Solve PoW (browser mines for solution)
// nonce = 187423

// 3. Submit solution
POST /ukabu_validate?redirect=/search
{challenge: "1731153045:a1b2c3d4", hmac: "9876...", nonce: 187423}
â† {success: true, redirect: "/search"}
```

### nginx Configuration

```nginx
# User-facing pages
location = /ukabu_verify {
    alias /etc/ukabu/pages/challenge.html;
}

location = /ukabu_help {
    # Serves browser-specific help page
    # Can detect browser via User-Agent and serve appropriate version
    alias /etc/ukabu/pages/nojs-chrome.html;  # or nojs-firefox.html, etc.
}

location = /ukabu_blocked {
    alias /etc/ukabu/pages/blocked.html;
}

# API endpoints (NJS handlers)
location = /ukabu_challenge {
    js_content pow.generateChallenge;
}

location = /ukabu_validate {
    js_content pow.validateSolution;
}
```

---

## PoW Challenge Mechanism

### Algorithm
- **Hash function:** SHA-256
- **Challenge format:** `timestamp:random_hex` (HMAC signed)
- **Solution:** Find nonce where `SHA256(challenge + ':' + nonce)` has N leading zero bits
- **Difficulty:** Configurable bits (default: 18 bits â‰ˆ 262,144 attempts)
- **Validity:** 5 minutes timeout

### Difficulty Mapping
```
12 bits = ~4,096 attempts     (~1-2s on modern browser)
16 bits = ~65,536 attempts    (~5-10s)
18 bits = ~262,144 attempts   (~15-30s) [DEFAULT]
20 bits = ~1,048,576 attempts (~1-2min)
24 bits = ~16,777,216 attempts (~5-10min)
```

### Token/Cookie Design
- **Format:** `token:timestamp` where `token = HMAC(timestamp + ':' + IP, secret)`
- **IP-bound:** Token won't work from different IP
- **Attributes:** `HttpOnly; Secure; SameSite=Lax`
- **Duration:** Configurable (default: 604800 seconds = 7 days)

---

## Status Code System

UKABU uses a two-layer blocking architecture:

### **Layer 1: Kernel/Firewall (iptables/nftables + ipset)**
- Blocks known bad IPs **before they reach nginx**
- Ultra-fast (kernel-space filtering)
- Client experiences: **Connection timeout** (no HTTP response)
- No nginx overhead for blocked IPs

### **Layer 2: nginx Application Logic**
- Path-based blocking with exceptions
- PoW challenge system
- Token validation
- Sends **X-Ukabu-Status** headers

---

### **Status Codes:**

#### **Daemon Log Only (No HTTP Response)**
These codes appear only in daemon logs (`/var/log/ukabu/blocks.log`). nginx never sends these to clients.

- **`001`** - IP Blacklisted (added to ipset)
  - Logged when daemon adds IP to `ukabu-permanent` or `ukabu-temporary_*`
  - Client experiences: Connection timeout (dropped at firewall)
  - No HTTP response sent

**Example daemon log entry:**
```json
{
  "timestamp": "2025-11-09T10:30:00Z",
  "event": "ip_blocked",
  "ip": "203.0.113.50",
  "ukabu_status": "001",
  "strike_count": 3,
  "ipset": "ukabu-temporary_0"
}
```

---

#### **nginx Responses (HTTP)**
These codes appear in the **X-Ukabu-Status** response header sent by nginx.

**Blocked (444 response - nginx closes connection):**
- **`002`** - Path Blacklisted
  - Request matches path_blacklist.conf AND IP not in whitelist
  - nginx returns 444 (connection closed without response body)
  - X-Ukabu-Status: 002

**Allowed (200 response - proxied to upstream):**
- **`100`** - Path Whitelisted
  - Request matches exempt_paths (e.g., `/static/*`)
  - Bypasses PoW challenge
  
- **`101`** - IP Whitelisted
  - Source IP in ip_whitelist.conf
  - Bypasses PoW challenge
  
- **`102`** - Search Engine
  - IP verified as Google/Bing crawler
  - Bypasses PoW challenge
  
- **`103`** - Valid PoW Token
  - Client has valid pow_token cookie
  - Token validated successfully
  
- **`104`** - Domain Not Protected
  - Domain not configured in domains.json
  - No PoW required

**Challenged (302/406 response):**
- **`200`** - Browser Redirected to Challenge
  - Browser client without valid token
  - 302 redirect to `/ukabu_verify?redirect=<original_url>`
  
- **`201`** - Non-Browser Blocked
  - Non-browser client (no JS support)
  - 406 Not Acceptable response

---

### **Request Flow Summary:**

```
Client Request
    â†“
[Layer 1: Firewall]
    â”œâ”€ IP in ipset? â†’ DROP (no response, timeout)  [Status: 001 in logs]
    â””â”€ Not in ipset â†’ Forward to nginx
                      â†“
              [Layer 2: nginx]
                      â”œâ”€ Path blacklisted? â†’ 444  [X-Ukabu-Status: 002]
                      â”œâ”€ IP whitelisted? â†’ 200    [X-Ukabu-Status: 101]
                      â”œâ”€ Path whitelisted? â†’ 200  [X-Ukabu-Status: 100]
                      â”œâ”€ Search engine? â†’ 200     [X-Ukabu-Status: 102]
                      â”œâ”€ Valid token? â†’ 200       [X-Ukabu-Status: 103]
                      â””â”€ Need PoW? â†’ 302          [X-Ukabu-Status: 200]
```

---

### **Client Experience:**

| Status | What Client Sees | Response Time |
|--------|------------------|---------------|
| **001** | Connection timeout | Varies (TCP timeout) |
| **002** | Connection closed | Immediate |
| **100-104** | Normal page load | Normal |
| **200** | Challenge page | Immediate redirect |
| **201** | Error message | Immediate |

---

## IP Blocking System

### Two-Layer Blocking Architecture

UKABU uses a **two-layer defense** system for maximum performance and security:

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚  LAYER 1: Kernel/Firewall (iptables/nftables + ipset)      â”‚
â”‚  â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€  â”‚
â”‚  â€¢ Known bad IPs blocked BEFORE reaching nginx             â”‚
â”‚  â€¢ Ultra-fast: <1ms per packet (kernel-space)              â”‚
â”‚  â€¢ Zero nginx overhead                                      â”‚
â”‚  â€¢ Client gets: Connection timeout (no HTTP response)       â”‚
â”‚  â€¢ Status: 001 logged by daemon (not sent to client)       â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                            â†“
              (Only if IP NOT in blacklist)
                            â†“
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚  LAYER 2: nginx Application Logic                          â”‚
â”‚  â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€  â”‚
â”‚  â€¢ Path-based blocking (with whitelist exceptions)         â”‚
â”‚  â€¢ PoW challenge system                                     â”‚
â”‚  â€¢ Token validation                                         â”‚
â”‚  â€¢ Strike tracking (feeds back to Layer 1 via daemon)      â”‚
â”‚  â€¢ Status: 002, 100-104, 200-201 sent to client            â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

### How an IP Gets Blocked

**Step-by-step process:**

1. **Client fails PoW challenge** (invalid solution, timeout, HMAC failure)
2. **nginx notifies daemon** via Unix socket: `{type: "failure", ip: "1.2.3.4"}`
3. **Daemon increments strike counter** in memory + SQLite
4. **After 3rd strike:**
   ```go
   // Daemon adds IP to ipset
   ipset add ukabu-temporary_0 1.2.3.4
   // Log event
   log({"ukabu_status": "001", "ip": "1.2.3.4", "ipset": "ukabu-temporary_0"})
   ```
5. **Kernel automatically blocks** all future packets from that IP
6. **Client experiences:** Connection timeout on next request

**No nginx processing for blocked IPs** - saves CPU and protects against DoS.

### Why Two Layers?

| Aspect | Layer 1 (Firewall) | Layer 2 (nginx) |
|--------|-------------------|-----------------|
| **Speed** | <1ms (kernel) | 5-50ms (application) |
| **Resources** | Minimal | nginx worker thread |
| **Flexibility** | IP-only | Path, token, whitelist logic |
| **Logging** | Daemon logs only | Full HTTP logs + headers |
| **Use Case** | Block known attackers | Challenge new visitors |

**Best of both worlds:** Firewall speed + Application intelligence

---

### ipset Management

**Permanent blacklist:**
```bash
ipset create ukabu-permanent hash:net maxelem 1000000
# IPs with lockout_period=0
```

**Temporary blacklists:**
```bash
ipset create ukabu-temporary_0 hash:net maxelem 10000
ipset create ukabu-temporary_1 hash:net maxelem 10000
# ... up to ukabu-temporary_N as needed
# IPs with lockout_period > 0
```

**Whitelist:**
```bash
ipset create ukabu-whitelist hash:net maxelem 100000
```

**Search engines:**
```bash
ipset create ukabu-search-engines hash:net maxelem 50000
```

### iptables/nftables Rules

**iptables example:**
```bash
iptables -I INPUT -m set --match-set ukabu-permanent src -j DROP
iptables -I INPUT -m set --match-set ukabu-temporary_0 src -j DROP
iptables -I INPUT -m set --match-set ukabu-whitelist src -j ACCEPT
```

**nftables example:**
```bash
table inet ukabu {
    set permanent {
        type ipv4_addr
        flags interval
        elements = { ... }
    }
    
    chain input {
        type filter hook input priority filter; policy accept;
        ip saddr @permanent drop
        ip saddr @whitelist accept
    }
}
```

### Blacklist File Format

`/etc/ukabu/config/ip_blacklist.conf`:
```json
{"ip_address": "172.0.0.1/24", "timestamp": "2025-11-08T20:30:00Z", "lockout_period": 0}
{"ip_address": "192.168.1.1", "timestamp": "2025-11-08T20:30:00Z", "lockout_period": 10080}
```

**Fields:**
- `ip_address` - IP or CIDR notation
- `timestamp` - When blocked (ISO 8601)
- `lockout_period` - Minutes (0 = permanent)

---

### Complete Blocking Lifecycle

**Visual Summary:**

```
[1] Client makes request with bad behavior
        â†“
[2] nginx processes request, detects failure
        â†“
[3] nginx â†’ Unix socket â†’ ukabu-trackerd
        â†“
[4] Daemon increments strike counter
        Strike 1: Logged, no action
        Strike 2: Logged, warning
        Strike 3: Add to ipset + log (status 001)
        â†“
[5] iptables/nftables rule matches ipset
        â†“
[6] Kernel drops packet (no nginx involvement)
        â†“
[7] Client experiences: Connection timeout
```

**Timeline Example:**

```
T+0s:  Request 1 fails â†’ Strike 1 â†’ nginx logs ukabu_status=200
T+5s:  Request 2 fails â†’ Strike 2 â†’ nginx logs ukabu_status=200
T+10s: Request 3 fails â†’ Strike 3 â†’ daemon adds to ipset
                                  â†’ daemon logs ukabu_status=001
T+15s: Request 4 arrives â†’ Kernel drops (no nginx)
                         â†’ No nginx log entry
                         â†’ Client timeout
```

**Key Points:**
- âœ… Status 001 = Daemon log only (never in nginx logs)
- âœ… Status 002-201 = nginx response headers (in nginx logs)
- âœ… Blocked IPs consume zero nginx resources
- âœ… Firewall rules are applied immediately after ipset update
- âœ… No race condition: ipset updates are atomic

---

## Directory Structure

```
/etc/ukabu/
  â”œâ”€â”€ config/
  â”‚   â”œâ”€â”€ domains.json                    # Main configuration
  â”‚   â”œâ”€â”€ ip_whitelist.conf               # Whitelisted IPs
  â”‚   â”œâ”€â”€ ip_blacklist.conf               # Blacklisted IPs (JSON)
  â”‚   â”œâ”€â”€ path_whitelist.conf             # Global exempt paths
  â”‚   â”œâ”€â”€ path_blacklist.conf             # Global blocked paths
  â”‚   â”œâ”€â”€ search_engines_google.conf      # Google IP ranges (auto-updated)
  â”‚   â”œâ”€â”€ search_engines_bing.conf        # Bing verified IPs
  â”‚   â”œâ”€â”€ trusted_proxies_cloudflare.conf # Cloudflare IPs (auto-updated)
  â”‚   â”œâ”€â”€ trusted_proxies_aws.conf        # AWS IPs (auto-updated)
  â”‚   â”œâ”€â”€ trusted_proxies_google.conf     # Google Cloud IPs (auto-updated)
  â”‚   â”œâ”€â”€ trusted_proxies_digitalocean.conf # DigitalOcean IPs (auto-updated)
  â”‚   â””â”€â”€ trusted_proxies_custom.conf     # Custom proxies (manual)
  â”‚
  â”œâ”€â”€ includes/
  â”‚   â”œâ”€â”€ config.conf                     # nginx variables and maps
  â”‚   â”œâ”€â”€ endpoints.inc                   # PoW endpoint definitions
  â”‚   â”œâ”€â”€ enforcement.inc                 # Priority-based enforcement logic
  â”‚   â””â”€â”€ browser-detection.inc           # User-agent detection
  â”‚
  â”œâ”€â”€ njs/
  â”‚   â””â”€â”€ pow-challenge.js                # NJS module for PoW
  â”‚
  â”œâ”€â”€ pages/
  â”‚   â”œâ”€â”€ challenge.html                  # PoW challenge page (served at /ukabu_verify)
  â”‚   â”œâ”€â”€ blocked.html                    # Blocked IP info page (served at /ukabu_blocked)
  â”‚   â”œâ”€â”€ nojs-chrome.html                # No-JS error page - Chrome (served at /ukabu_help)
  â”‚   â”œâ”€â”€ nojs-firefox.html               # No-JS error page - Firefox
  â”‚   â”œâ”€â”€ nojs-edge.html                  # No-JS error page - Edge
  â”‚   â”œâ”€â”€ nojs-safari.html                # No-JS error page - Safari
  â”‚   â””â”€â”€ nojs-generic.html               # No-JS error page - generic
  â”‚   # NOTE: All HTML files must include copyright footer:
  â”‚   # <div class="footer">Copyright (c) 2025 by L2C2 Technologies. All rights reserved.</div>
  â”‚
  â””â”€â”€ secrets/
      â”œâ”€â”€ example.com.key                 # Per-domain secrets (600 permissions)
      â””â”€â”€ another.com.key

/var/lib/ukabu/
  â”œâ”€â”€ strikes.db                          # SQLite strike database
  â”œâ”€â”€ strikes.db-wal                      # SQLite WAL file
  â”œâ”€â”€ strikes.db-shm                      # SQLite shared memory
  â””â”€â”€ ipset.rules                         # ipset state backup

/var/log/ukabu/
  â”œâ”€â”€ trackerd.log                        # Daemon log
  â”œâ”€â”€ failures.log                        # PoW failures
  â”œâ”€â”€ blocks.log                          # Blocking events
  â”œâ”€â”€ search-engines.log                  # Search engine updates
  â”œâ”€â”€ trusted-proxies.log                 # CDN proxy updates
  â””â”€â”€ audit.log                           # Configuration changes

/usr/local/bin/
  â”œâ”€â”€ ukabu-trackerd                      # Go daemon binary
  â”œâ”€â”€ ukabu-manager                       # Python CLI
  â”œâ”€â”€ ukabu-exporter                      # Prometheus exporter
  â”œâ”€â”€ ukabu-fetch-google-ips.sh           # Search engine IP fetcher
  â””â”€â”€ ukabu-fetch-cdn-ips.sh              # CDN proxy IP fetcher (CF, AWS, GOOG, DO)

/etc/systemd/system/
  â”œâ”€â”€ ukabu-trackerd.service              # Daemon service
  â”œâ”€â”€ ukabu-unjail.service                # Unjail expired blocks
  â”œâ”€â”€ ukabu-unjail.timer                  # Unjail timer (every 5 min)
  â”œâ”€â”€ ukabu-search-engines.service        # Update search engine IPs
  â”œâ”€â”€ ukabu-search-engines.timer          # Daily at 3 AM
  â”œâ”€â”€ ukabu-update-proxies.service        # Update CDN proxy IPs
  â””â”€â”€ ukabu-update-proxies.timer          # Daily at 3:00 AM
```

---

## Request Flow

### 0. Firewall Check (Before nginx)
```
Packet arrives at server
    â†“
[Kernel netfilter / iptables / nftables]
    â†“
Check ipset membership (ukabu-permanent, ukabu-temporary_*)
    â”œâ”€ IP in blacklist? â†’ DROP packet immediately
    â”‚                     Client gets: Connection timeout
    â”‚                     nginx never sees request
    â”‚                     Status: 001 (logged by daemon only)
    â””â”€ IP NOT in blacklist â†’ Forward to nginx
                              Continue to Step 1
```

**Critical:** Blacklisted IPs **never reach nginx**. They are dropped at the kernel/firewall level for maximum performance.

---

### 1. Initial Request (No Token)
**Prerequisite:** IP passed firewall check (not in ipset blacklist)

```
nginx receives request
    â†“
Extract real IP (XFF handling if enabled)
    â†“
Check path blacklist
    â”œâ”€ Match + IP not whitelisted? â†’ 444 (Status: 002)
    â””â”€ No match â†’ Continue
        â†“
Check IP whitelist
    â”œâ”€ Match? â†’ Proxy to upstream (Status: 101)
    â””â”€ No match â†’ Continue
        â†“
Check path whitelist (exempt_paths)
    â”œâ”€ Match? â†’ Proxy to upstream (Status: 100)
    â””â”€ No match â†’ Continue
        â†“
Check search engine
    â”œâ”€ Match? â†’ Proxy to upstream (Status: 102)
    â””â”€ No match â†’ Continue
        â†“
Check if domain protected
    â”œâ”€ Not protected? â†’ Proxy to upstream (Status: 104)
    â””â”€ Protected â†’ Continue
        â†“
Check PoW token
    â”œâ”€ Valid token? â†’ Proxy to upstream (Status: 103)
    â””â”€ No/invalid token â†’ Redirect to challenge (Status: 200)
```

---

### 2. Challenge Flow
```
Browser loads challenge.html
           â†“
Fetch /ukabu_challenge
           â†“
NJS generates: {challenge: "timestamp:random", hmac: "signature", difficulty: 18}
           â†“
Browser solves PoW (SHA-256 brute force)
           â†“
Submit to /ukabu_validate
           â†“
NJS validates solution
    â”œâ”€ Valid: Set cookie, redirect to original URL, notify daemon (success)
    â””â”€ Invalid: Return error, notify daemon (failure â†’ strike++)
```

---

### 3. Subsequent Requests (With Token)
**Prerequisite:** IP passed firewall check

```
nginx receives request
    â†“
Extract real IP
    â†“
Check token validity (NJS)
    â”œâ”€ Valid token? â†’ Proxy to upstream (Status: 103)
    â””â”€ Invalid/expired â†’ Redirect to challenge (Status: 200)
```

---

### 4. Failure Tracking & Blocking
```
Invalid solution â†’ NJS â†’ Unix socket â†’ ukabu-trackerd
                                    â†“
                            Increment strike counter (in-memory + SQLite)
                                    â†“
                            Check: strike_count >= 3?
                                    â†“
                                  [YES]
                                    â†“
                            Execute: ipset add ukabu-temporary_0 <IP>
                                    â†“
                            Log: {"ukabu_status": "001", "ip": "<IP>", "ipset": "..."}
                                    â†“
                            [RESULT: Next request from this IP]
                                    â†“
                            Dropped at firewall (Step 0)
                                    â†“
                            nginx never sees it
```

**Important:** Once an IP is added to ipset, it's blocked at the **kernel level**. The IP cannot reach nginx to accumulate more strikes or consume resources.

---

## ukabu-manager CLI Reference

### Installation
```bash
ukabu-manager install                     # Setup directories, configs, systemd
ukabu-manager uninstall                   # Remove all UKABU components
```

### Domain Management
```bash
ukabu-manager domain add example.com --difficulty 18
ukabu-manager domain remove example.com
ukabu-manager domain list
ukabu-manager domain show example.com
ukabu-manager domain set example.com --difficulty 20 --lockout 20160
ukabu-manager domain set example.com --excuse-first-timeout true
ukabu-manager domain set example.com --excuse-first-timeout false
ukabu-manager domain set-secret example.com [--auto | --value SECRET]
ukabu-manager domain rotate-secret example.com
```

### IP Whitelist/Blacklist
```bash
ukabu-manager whitelist add 192.168.1.0/24
ukabu-manager whitelist remove 192.168.1.0/24
ukabu-manager whitelist list
ukabu-manager whitelist import /path/to/list.txt

ukabu-manager blacklist add 1.2.3.4 --duration 10080
ukabu-manager blacklist add 1.2.3.4 --permanent
ukabu-manager blacklist remove 1.2.3.4
ukabu-manager blacklist list [--permanent | --temporary]
ukabu-manager blacklist export /path/to/backup.json
```

### Path Management
```bash
ukabu-manager paths add-exempt example.com /static/*
ukabu-manager paths remove-exempt example.com /static/*
ukabu-manager paths list-exempt example.com

ukabu-manager paths add-restricted example.com /admin/* --ip 10.0.0.0/8
ukabu-manager paths remove-restricted example.com /admin/*
ukabu-manager paths list-restricted example.com
```

### XFF Management
```bash
ukabu-manager xff enable example.com
ukabu-manager xff disable example.com
ukabu-manager xff add-proxy example.com 104.21.0.0/16
ukabu-manager xff remove-proxy example.com 104.21.0.0/16
ukabu-manager xff list-proxies example.com
ukabu-manager xff test example.com --client-ip X --proxy-ip Y

# Auto-update CDN proxy lists
ukabu-manager xff update-cdn-proxies          # Manual update (all providers)
ukabu-manager xff update-cdn-proxies --provider cloudflare  # Single provider
ukabu-manager xff list-cdn-providers          # Show enabled CDN sources
ukabu-manager xff enable-cdn example.com --provider aws     # Enable AWS for domain
ukabu-manager xff disable-cdn example.com --provider aws    # Disable AWS for domain
```

### Search Engine Management
```bash
ukabu-manager search-engines update             # Fetch Google IPs, verify Bing
ukabu-manager search-engines list
ukabu-manager search-engines add 1.2.3.4 --name "CustomBot"
ukabu-manager search-engines remove 1.2.3.4
```

### Status & Monitoring
```bash
ukabu-manager status                            # Overall status
ukabu-manager strikes list [--ip 1.2.3.4]       # Current strikes
ukabu-manager strikes clear 1.2.3.4             # Manual reset
ukabu-manager blocks list                       # Currently blocked IPs
ukabu-manager blocks clear 1.2.3.4              # Manual unblock
```

### ML/Analysis
```bash
ukabu-manager ml extract \
  --start 2025-11-01 --end 2025-11-08 \
  --format csv --output training.csv

ukabu-manager ml analyze-ip 1.2.3.4 --last 24h
ukabu-manager ml patterns --type burst --min-requests 100/min
ukabu-manager ml trace REQ-8f14e45fceea167a
```

### nginx Integration
```bash
ukabu-manager nginx generate-config            # Generate nginx maps
ukabu-manager nginx test                       # nginx -t
ukabu-manager nginx reload                     # Graceful reload
ukabu-manager nginx validate example.com       # Test domain config
```

### Logs
```bash
ukabu-manager logs tail [--failures | --blocks | --daemon]
ukabu-manager logs analyze --last 24h
ukabu-manager logs export --start DATE --end DATE --output FILE
```

### Backup/Restore
```bash
ukabu-manager backup create [--output FILE]
ukabu-manager backup restore FILE
ukabu-manager backup list
```

---

---

## Additional Architectural Decisions

### âœ… 12. nginx Config Generation Strategy

**Chosen: Option 1 - Generate at config save**

**Behavior:**
```bash
ukabu-manager domain add example.com --difficulty 18
# Automatically executes:
# 1. Update domains.json
# 2. Generate nginx maps from domains.json
# 3. Run nginx -t (test configuration)
# 4. If valid: nginx -s reload (graceful reload)
# 5. If invalid: Rollback changes, show error
```

**Benefits:**
- Immediate feedback on configuration errors
- No manual step to forget
- Atomic operations (update + reload or rollback)
- Reduced risk of config drift

**Implementation:**
- Python CLI calls `generate_nginx_config()` after each domain operation
- Validates nginx config before applying
- Maintains backup of last known-good config

---

### âœ… 13. Secret Storage

**Chosen: Option 2 - Separate secrets file**

**Structure:**
```bash
/etc/ukabu/secrets/
  â”œâ”€â”€ example.com.key      # HMAC secret (600 permissions, root only)
  â”œâ”€â”€ another.com.key
  â””â”€â”€ .secrets.index       # JSON index for rotation tracking
```

**Secret file format:**
```
# /etc/ukabu/secrets/example.com.key
hmac_secret=a1b2c3d4e5f6...
hmac_secret_old=x9y8z7w6v5u4...
rotation_expires=2025-11-09T22:30:00Z
```

**Benefits:**
- Secrets separated from config
- Fine-grained file permissions (600)
- Easier backup strategy (exclude secrets from config backups)
- Supports secret rotation with grace period

**Security:**
- Only readable by root and nginx user
- Not included in git repos or config exports
- Automatic permission enforcement on write

---

### âœ… 14. Logging Strategy

**nginx logs:**
```bash
/var/log/nginx/access.log          # Main access log (with ukabu fields)
/var/log/nginx/error.log           # nginx errors
```

**ukabu logs:**
```bash
/var/log/ukabu/trackerd.log        # Daemon operational log
/var/log/ukabu/failures.log        # Failed PoW attempts (from socket)
/var/log/ukabu/blocks.log          # IP blocking events
/var/log/ukabu/search-engines.log  # Search engine updates
/var/log/ukabu/trusted-proxies.log # CDN/proxy IP range updates
/var/log/ukabu/audit.log           # Config changes, manual actions
```

**journald (systemd logs):**
- **Only systemd unit/timer errors** are logged to journald
- Application logs stay in `/var/log/ukabu/`
- View with: `journalctl -u ukabu-trackerd`

**Structured logging:**
- **Format: JSON** for all ukabu logs
- Enables easy parsing, querying, and integration with log aggregators

**Example log entries:**

`/var/log/ukabu/failures.log`:
```json
{"timestamp":"2025-11-09T10:30:45.123Z","level":"warn","ip":"1.2.3.4","domain":"example.com","event":"pow_failure","reason":"invalid_solution","strike_count":2,"user_agent":"Mozilla/5.0..."}
```

`/var/log/ukabu/blocks.log`:
```json
{"timestamp":"2025-11-09T10:31:00.456Z","level":"info","ip":"1.2.3.4","domain":"example.com","event":"ip_blocked","strike_count":3,"lockout_period":10080,"ipset":"ukabu-temporary_0"}
```

`/var/log/ukabu/trackerd.log`:
```json
{"timestamp":"2025-11-09T10:00:00.000Z","level":"info","event":"daemon_start","version":"1.0.0","config_loaded":true}
{"timestamp":"2025-11-09T10:00:01.234Z","level":"info","event":"socket_listening","path":"/var/run/ukabu/tracker.sock"}
```

**Benefits:**
- Machine-readable (JSON)
- Easy to parse with jq, grep, or log aggregators
- Consistent structure across all components
- Supports structured queries

---

### âœ… 15. Installation Method

**Chosen: Option 1 - Manual installation (v1.0)**

**Current approach:**
```bash
# Clone repository
git clone https://github.com/your-org/ukabu.git
cd ukabu

# Build Go daemon
cd ukabu-core
make build
sudo make install

# Install Python CLI
cd ../ukabu-manager
pip3 install -e .

# Run installation script
sudo ukabu-manager install
```

**Future enhancements (v1.1+):**
- **Option 2:** Automated installer script (`curl | bash`)
- **Option 3:** Package management (`.deb`, `.rpm`)
- **Option 4:** Docker/container images
- **Option 5:** Ansible playbook

**Reasoning:**
- Manual install gives most control for early adopters
- Easier to debug during development
- No packaging overhead for initial release
- Add automated methods based on community feedback

---

### âœ… 16. ukabu-manager Idempotency Requirements

**Principle:** All CRUD operations must be idempotent - running the same command multiple times produces the same result without creating duplicates or errors.

**Core Rules:**

**1. CREATE Operations (Add)** - No duplicates
```bash
ukabu-manager domain add example.com --difficulty 18
ukabu-manager domain add example.com --difficulty 18
# First run:  Creates domain â†’ "Domain example.com added successfully"
# Second run: Detects existing â†’ "Domain example.com already exists, no changes made"
# Exit code: 0 (both runs)
```

**2. UPDATE Operations (Set)** - Detect no-op
```bash
ukabu-manager domain set example.com --difficulty 20
ukabu-manager domain set example.com --difficulty 20
# First run:  Updates â†’ "Difficulty changed from 18 to 20"
# Second run: Detects same â†’ "Difficulty already set to 20, no changes made"
# Exit code: 0 (both runs)
```

**3. DELETE Operations (Remove)** - Graceful handling
```bash
ukabu-manager domain remove example.com
ukabu-manager domain remove example.com
# First run:  Removes â†’ "Domain example.com removed successfully"
# Second run: Not found â†’ "Domain example.com not found, nothing to remove"
# Exit code: 0 (both runs, not an error)
```

**Specific Idempotency Cases:**

**IP Lists:**
```bash
# Duplicate IP detection
ukabu-manager whitelist add 192.168.1.100
ukabu-manager whitelist add 192.168.1.100
# Result: IP stored once, second add is no-op

# Overlapping CIDR handling
ukabu-manager whitelist add 192.168.1.0/24
ukabu-manager whitelist add 192.168.1.0/25
# Result: Both stored (no auto-merge), warn user about overlap

# Remove non-existent IP
ukabu-manager whitelist remove 10.0.0.1
# Result: No error, "IP not in whitelist"
```

**Path Management:**
```bash
# Duplicate path detection
ukabu-manager paths add-exempt example.com /static/*
ukabu-manager paths add-exempt example.com /static/*
# Result: Path stored once, second add is no-op

# Case sensitivity (paths are case-sensitive)
ukabu-manager paths add-exempt example.com /Static/*
ukabu-manager paths add-exempt example.com /static/*
# Result: Both stored as different paths
```

**XFF Proxy Management:**
```bash
# Duplicate proxy detection
ukabu-manager xff add-proxy example.com 10.0.0.5
ukabu-manager xff add-proxy example.com 10.0.0.5
# Result: Proxy stored once, second add is no-op

# Toggle operations
ukabu-manager xff enable example.com
ukabu-manager xff enable example.com
# Result: Enabled once, second enable is no-op
```

**Configuration Regeneration:**
```bash
# Multiple regenerations produce identical output
ukabu-manager nginx generate-config
ukabu-manager nginx generate-config
# Result: Same nginx maps generated, only timestamp changes
# No duplicate entries in nginx config files
```

**Implementation Strategy:**

**1. Pre-flight checks before modifications:**
```python
def add_domain(domain, **kwargs):
    # Check if already exists
    if domain_exists(domain):
        print(f"Domain {domain} already exists, no changes made")
        return 0  # Success exit code
    
    # Proceed with creation
    create_domain(domain, **kwargs)
    print(f"Domain {domain} added successfully")
    return 0
```

**2. Deduplication in data structures:**
```python
# Use sets for IP lists
whitelist_ips = set()
whitelist_ips.add("192.168.1.100")
whitelist_ips.add("192.168.1.100")  # Automatically deduplicated

# Check for duplicates in lists
def add_exempt_path(domain, path):
    current_paths = get_exempt_paths(domain)
    if path in current_paths:
        print(f"Path {path} already exempt for {domain}")
        return 0
    current_paths.append(path)
    save_exempt_paths(domain, current_paths)
```

**3. Atomic file updates:**
```python
# Write to temp file, then atomic rename
def update_config(config_data):
    temp_file = "/etc/ukabu/config/.domains.json.tmp"
    final_file = "/etc/ukabu/config/domains.json"
    
    # Write to temp
    with open(temp_file, 'w') as f:
        json.dump(config_data, f)
    
    # Atomic rename (prevents corruption)
    os.rename(temp_file, final_file)
```

**4. Exit code consistency:**
- **0** - Success (including no-op idempotent operations)
- **1** - User error (invalid input, missing required args)
- **2** - System error (file permissions, nginx test failed)

**Testing Idempotency:**
Every ukabu-manager command must pass this test:
```bash
# Run command twice, both should succeed
ukabu-manager <command> <args>
EXIT1=$?
ukabu-manager <command> <args>
EXIT2=$?

# Both must be 0
[ $EXIT1 -eq 0 ] && [ $EXIT2 -eq 0 ]
```

---

### âœ… 17. Implementation Path

**Chosen: Path C - Critical Path (Core Flow First)**

**Rationale:**
- Get core PoW flow working first (nginx â†’ challenge â†’ validate â†’ block)
- Validate architecture with working prototype
- Iterate and expand from solid foundation
- Demonstrates value early
- Easier to debug with minimal components

**Phase Sequence:**

#### **Component A (ukabu-core): nginx includes (PoW flow working)**
**Goal:** Browser can complete PoW challenge and access protected resources

**Deliverables:**
1. `config.conf` - nginx variables and maps
2. `endpoints.inc` - PoW endpoint definitions (/ukabu_challenge, /ukabu_validate, /ukabu_verify, /ukabu_help, /ukabu_blocked)
3. `enforcement.inc` - Priority-based enforcement logic
4. `pow-challenge.js` (updated) - NJS module with socket communication
5. `challenge.html` - Working PoW challenge page
6. `nojs-chrome.html` - No-JS error page
7. Example vhost config

**Success criteria:** 
- Browser completes challenge manually (without daemon)
- Token issued and validated
- Redirect to original page works

---

#### **Component B (ukabu-monitor): Go daemon (strike tracking + ipset)**
**Goal:** Automatic blocking after 3 failed attempts

**Deliverables:**
1. Strike tracking module (in-memory + SQLite)
2. Unix socket server (JSON protocol)
3. ipset management (create/add/remove)
4. Basic metrics endpoint
5. systemd service file
6. iptables/nftables detection and rule setup
7. Optional first timeout excuse logic (per-domain)

**Success criteria:**
- Daemon tracks failures from nginx
- IP blocked after 3 strikes
- ipset rules active
- Daemon survives restart (SQLite persistence)
- First timeout excuse works when enabled for a domain

---

#### **Component C (ukabu-manager): Basic CLI (domain add/remove, whitelist/blacklist)**
**Goal:** Manage domains and IP lists

**Deliverables:**
1. `ukabu-manager domain add/remove/list/show`
2. `ukabu-manager domain set` (difficulty, lockout, excuse_first_timeout)
3. `ukabu-manager whitelist add/remove/list`
4. `ukabu-manager blacklist add/remove/list`
5. `ukabu-manager nginx generate-config`
6. `ukabu-manager nginx reload`
7. `ukabu-manager install` - Setup wizard

**Success criteria:**
- Add domain â†’ nginx config generated â†’ reload works
- Set excuse_first_timeout â†’ daemon reads config
- Whitelist IP â†’ bypass PoW
- Blacklist IP â†’ blocked immediately

---

#### **Component D (ukabu-extras): Expand CLI (XFF, ML, etc.)**
**Goal:** Advanced features and analysis

**Deliverables:**
1. XFF management commands
2. CDN proxy auto-updater (CF, AWS, Google, DO) with systemd timer
3. Search engine IP fetcher (Google + Bing)
4. ML log extraction (`ml extract`, `ml analyze-ip`)
5. Path management (exempt/restricted)
6. Secret rotation
7. Strike/block management

**Success criteria:**
- XFF handling works with CDN
- CDN proxy IPs auto-update daily at 3 AM
- Search engines bypass PoW
- ML dataset extraction from logs
- Secret rotation with grace period

---

#### **Phase 5: Monitoring + docs**
**Goal:** Production-ready observability and documentation

**Deliverables:**
1. Prometheus exporter (ukabu-monitor)
2. Grafana dashboard JSON
3. Installation guide
4. Configuration reference
5. Troubleshooting guide
6. ML workflow guide
7. API reference (socket protocol)
8. Example configs for common setups

**Success criteria:**
- Metrics visible in Prometheus
- Dashboard shows live data
- Complete documentation
- Tested on fresh system

---

## Implementation Phases

### Component A (ukabu-core): nginx includes (PoW flow working) ðŸŽ¯ CURRENT
- nginx config structure
- PoW challenge/validate endpoints
- Token validation
- Challenge pages (HTML)
- Example vhost configuration

### Component B (ukabu-monitor): Go daemon (strike tracking + ipset)
- Strike tracking module (in-memory + SQLite)
- Unix socket server (JSON protocol)
- ipset management (create/add/remove IPs)
- Basic metrics endpoint (:9090/metrics)
- systemd service file
- iptables/nftables auto-detection
- Optional first timeout excuse logic (per-domain setting)

### Component C (ukabu-manager): Basic CLI (domain add/remove, whitelist/blacklist)
- Domain management commands
- Domain settings (difficulty, lockout, excuse_first_timeout)
- IP whitelist/blacklist commands
- nginx config generation
- nginx reload automation
- Installation wizard
- Status/monitoring commands

### Component D (ukabu-extras): Expand CLI (XFF, ML, etc.)
- XFF management (proxy configuration)
- CDN proxy auto-updater (CF, AWS, Google, DO) + systemd timer
- Search engine IP fetcher (Google + Bing)
- ML log extraction tools
- Path management (exempt/restricted)
- Secret rotation (12hr grace period)
- Strike/block management
- Idempotency enforcement (all CRUD operations)

### Phase 5: Monitoring + docs
- Prometheus exporter (ukabu-monitor)
- Grafana dashboard JSON
- Installation guide
- Configuration reference
- Troubleshooting guide
- ML workflow guide
- API reference (socket protocol)
- Example configurations

### Phase 6: Testing & Hardening
- Unit tests (Go daemon, Python CLI, NJS)
- Integration tests (full PoW flow)
- Load testing (10K req/s)
- Security testing (XFF spoofing, HMAC tampering)
- Performance profiling
- Edge case handling

### Phase 7: Future Enhancements (v1.1+)
- Automated installer (curl | bash)
- Package management (.deb, .rpm)
- Web UI for configuration
- Advanced ML pattern detection
- Docker/container images
- Ansible playbook

---

## Security Considerations

### 1. HMAC Secret Management
- **Storage:** `/etc/ukabu/secrets/` (600 permissions, root only)
- **Generation:** Cryptographically secure random (32+ characters)
- **Rotation:** 12-hour grace period to prevent token invalidation
- **Backup:** Encrypted backups only

### 2. XFF Spoofing Prevention
- Only trust XFF from explicitly configured trusted proxies
- Attacker cannot spoof whitelist IPs through XFF
- Per-domain configuration for flexibility

### 3. Strike Tracking Integrity
- Unix socket with 600 permissions (root/nginx only)
- SQLite with 600 permissions
- In-memory state with checksum validation
- Graceful degradation if daemon unavailable

### 4. ipset Management
- Kernel-space enforcement (can't be bypassed)
- Atomic operations (no race conditions)
- Auto-cleanup of expired entries
- Manual override capability for admins

### 5. Rate Limiting
- PoW difficulty as natural rate limit
- Additional nginx rate limiting on challenge endpoints
- Prevents challenge flooding

---

## Performance Targets

### Response Time
- IP whitelist check: <1ms (ipset kernel lookup)
- Token validation: <5ms (NJS HMAC)
- Strike tracking: <10ms (Unix socket + in-memory)
- PoW challenge generation: <50ms (NJS)

### Throughput
- 10,000+ requests/sec per nginx worker
- 5,000+ PoW validations/sec (ukabu-trackerd)
- 1,000+ strike updates/sec

### Resource Usage
- nginx: +5-10MB memory overhead per worker
- ukabu-trackerd: 50-200MB depending on strike count
- SQLite: ~100KB per 1,000 strikes
- ipset: ~10MB per 100,000 IPs

---

## Future Enhancements (Post-v1.0)

### v1.1
- [ ] Web UI for configuration/monitoring
- [ ] Advanced ML pattern detection
- [ ] Integration with threat intelligence feeds
- [ ] Multi-region coordination

### v1.2
- [ ] Captcha fallback (hCaptcha/reCAPTCHA)
- [ ] Rate limiting per IP/domain
- [ ] Geographic blocking
- [ ] Custom challenge types

### v2.0
- [ ] Distributed deployment (multi-server)
- [ ] Redis cluster support (alternative to SQLite)
- [ ] Real-time dashboard
- [ ] Advanced behavioral analysis
- [ ] AI-powered anomaly detection

---

## Support & Maintenance

### Log Rotation
```bash
# /etc/logrotate.d/ukabu
/var/log/ukabu/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0640 root adm
    sharedscripts
    postrotate
        systemctl reload ukabu-trackerd
    endscript
}
```

### Monitoring Metrics
- Active strikes count
- Blocks per minute
- PoW challenge success rate
- Average solution time
- Failed attempts per IP
- ipset size
- Daemon uptime

### Health Checks
```bash
# Check daemon status
systemctl status ukabu-trackerd

# Check ipset status
ipset list ukabu-permanent | head -20

# Check recent blocks
tail -f /var/log/ukabu/blocks.log

# Check strike database
ukabu-manager strikes list

# Test PoW flow
curl -I https://example.com/protected-page
```

---

## Testing Strategy

### Unit Tests
- Go daemon (strike logic, ipset management)
- Python CLI (config parsing, command execution)
- NJS module (challenge generation, validation)

### Integration Tests
- Full PoW flow (challenge â†’ solve â†’ validate â†’ access)
- Failure tracking (3 strikes â†’ block)
- Token expiration
- Secret rotation
- XFF handling

### Load Tests
- 10,000 req/s with 50% PoW challenges
- Concurrent strike updates
- ipset performance under 1M IPs
- SQLite write throughput

### Security Tests
- XFF spoofing attempts
- HMAC tampering
- Replay attacks
- Race conditions in strike tracking
- ipset bypass attempts

---

## Deployment Checklist

### Pre-deployment
- [ ] Generate HMAC secrets for all domains
- [ ] Configure XFF trusted proxies
- [ ] Import IP whitelist
- [ ] Configure exempt paths
- [ ] Test PoW flow in staging
- [ ] Load test with expected traffic
- [ ] Review security settings

### Deployment
- [ ] Install ukabu packages
- [ ] Configure domains.json
- [ ] Generate nginx configs
- [ ] Test nginx configuration
- [ ] Start ukabu-trackerd
- [ ] Enable systemd timers
- [ ] Reload nginx
- [ ] Monitor logs for errors
- [ ] Verify PoW flow
- [ ] Test from various IPs/browsers

### Post-deployment
- [ ] Monitor strike/block rates
- [ ] Review false positives
- [ ] Adjust difficulty if needed
- [ ] Set up monitoring alerts
- [ ] Schedule regular backups
- [ ] Document operational procedures

---

## License & Credits

**UKABU WAF** - Collaborative Anti-AI Scraper Bot Web Application Firewall

**Copyright:** Copyright (c) 2025 by L2C2 Technologies. All rights reserved.

**Created:** 2025-11-09  
**Architecture:** nginx + Go + Python  

**Licensing:**
- For licensing requirements and inquiries, contact:
- **Indranil Das Gupta**
- Email: indradg@l2c2.co.in
- Organization: L2C2 Technologies

**HTML Footer Requirement:**
All HTML files (challenge pages, error pages) must include in their footer:
```html
<div class="footer">
    Copyright (c) 2025 by L2C2 Technologies. All rights reserved.
</div>
```

**Source Code Headers:**
All source code files (Go, Python, JavaScript, nginx configs) should include:
```
# Copyright (c) 2025 by L2C2 Technologies. All rights reserved.
# 
# For licensing inquiries, contact:
# Indranil Das Gupta <indradg@l2c2.co.in>
```

**Credits:**
- nginx-njs examples and documentation
- ipset/iptables community
- Cloudflare for IP range API
- paomedia.github.io/small-n-flat for icons

---

## Next Steps: Component A (ukabu-core) Implementation

### ðŸŽ¯ Current Phase: nginx includes (PoW flow working)

**Goal:** Get a working PoW challenge that a browser can complete

**What we're building:**

1. **nginx configuration structure**
   - `/etc/ukabu/includes/config.conf` - Variables, maps, XFF handling
   - `/etc/ukabu/includes/endpoints.inc` - PoW endpoints (/ukabu_challenge, /ukabu_validate, /ukabu_verify, /ukabu_help, /ukabu_blocked)
   - `/etc/ukabu/includes/enforcement.inc` - Priority-based access control logic

2. **NJS module (updated)**
   - `/etc/ukabu/njs/pow-challenge.js`
   - Challenge generation with HMAC signing
   - Solution validation (SHA-256 difficulty check)
   - Token generation/validation
   - Unix socket communication (stub for Component B (ukabu-monitor))

3. **HTML pages**
   - `/etc/ukabu/pages/challenge.html` - Interactive PoW solver (served at /ukabu_verify)
   - `/etc/ukabu/pages/blocked.html` - Blocked IP information page (served at /ukabu_blocked)
   - `/etc/ukabu/pages/nojs-chrome.html` - No-JS error page (served at /ukabu_help)
   - **Footer requirement:** All HTML files must include copyright footer:
     ```html
     <div class="footer">
         Copyright (c) 2025 by L2C2 Technologies. All rights reserved.
     </div>
     ```

4. **Example vhost**
   - Working configuration for a Koha OPAC site
   - Demonstrates how to integrate UKABU into existing nginx setup

**Success criteria:**
- âœ… Browser can load challenge page
- âœ… Challenge is generated with valid HMAC
- âœ… Browser solves PoW (SHA-256 mining)
- âœ… Solution validates correctly
- âœ… Token is issued as cookie
- âœ… Subsequent requests with valid token bypass challenge
- âœ… Invalid/expired tokens trigger re-challenge
- âœ… No-JS users see helpful error page

**What's NOT in Component A (ukabu-core):**
- âŒ Strike tracking (Component B (ukabu-monitor))
- âŒ IP blocking (Component B (ukabu-monitor))
- âŒ CLI management tools (Component C (ukabu-manager))
- âŒ Search engine detection (Component D (ukabu-extras))
- âŒ ML extraction (Component D (ukabu-extras))

**Testing approach:**
1. Manual browser test (Chrome/Firefox)
2. curl test with token manipulation
3. Load test with ApacheBench
4. Verify HMAC signature validation

---

## Development Workflow

```bash
# Component A (ukabu-core): nginx configs
git checkout -b phase-1-nginx-includes
# Generate configs â†’ Test â†’ Review â†’ Merge

# Component B (ukabu-monitor): Go daemon
git checkout -b phase-2-daemon
# Build daemon â†’ Test with Component A (ukabu-core) nginx â†’ Review â†’ Merge

# Component C (ukabu-manager): Basic CLI
git checkout -b phase-3-basic-cli
# Build CLI â†’ Test CRUD operations â†’ Review â†’ Merge

# Component D (ukabu-extras): Expanded CLI
git checkout -b phase-4-expanded-cli
# Add XFF, ML, search engines â†’ Test â†’ Review â†’ Merge

# Phase 5: Monitoring
git checkout -b phase-5-monitoring
# Prometheus exporter â†’ Grafana â†’ Docs â†’ Review â†’ Merge
```

---

**END OF DECISIONS DOCUMENT**
