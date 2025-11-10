# Ukabu WAF - Domain Configuration Guide

**Version:** 1.0.0  
**Copyright:** (c) 2025 L2C2 Technologies. All rights reserved.

---

## Table of Contents

1. [Introduction](#introduction)
2. [Configuration Structure](#configuration-structure)
3. [Default Settings](#default-settings)
4. [Use Case Examples](#use-case-examples)
   - [Basic Website](#use-case-1-basic-website)
   - [Library OPAC (Koha ILS)](#use-case-2-library-opac-koha-ils)
   - [WordPress Blog](#use-case-3-wordpress-blog)
   - [E-commerce Site](#use-case-4-e-commerce-site)
   - [API Service](#use-case-5-api-service)
   - [DSpace Institutional Repository](#use-case-6-dspace-institutional-repository)
   - [Corporate Intranet](#use-case-7-corporate-intranet)
   - [CDN Origin Server](#use-case-8-cdn-origin-server)
5. [Configuration Parameters Reference](#configuration-parameters-reference)
6. [Path Pattern Matching](#path-pattern-matching)
7. [Best Practices](#best-practices)
8. [Quick Start Guide](#quick-start-guide)

---

## Introduction

This guide provides comprehensive examples for configuring Ukabu WAF domain protection. Each use case demonstrates real-world scenarios with appropriate security settings, path exemptions, and access restrictions.

**Important Notes:**
- All configurations should be placed in `/etc/ukabu/config/domains.json`
- HMAC secrets must be generated for each domain
- Validate JSON syntax before applying: `jq . /etc/ukabu/config/domains.json`
- Test nginx configuration: `nginx -t`
- Reload nginx after changes: `systemctl reload nginx`

---

## Configuration Structure

The main configuration file (`/etc/ukabu/config/domains.json`) has the following structure:

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
      "excuse_first_timeout": false,
      "exempt_paths": [],
      "restricted_paths": {},
      "xff_handling": {
        "enabled": false
      }
    }
  }
}
```

---

## Default Settings

Default settings apply to all domains unless explicitly overridden:

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
  }
}
```

### Default Parameter Explanations

| Parameter | Value | Description |
|-----------|-------|-------------|
| `pow_difficulty` | 18 | Number of leading zero bits required in PoW solution (~4.5 hex zeros) |
| `cookie_duration` | 604800 | Token validity duration in seconds (7 days) |
| `lockout_period` | 10080 | IP lockout duration in minutes (7 days) |
| `excuse_first_timeout` | false | Whether to excuse the first timeout without counting as a strike |
| `xff_handling.enabled` | false | Whether to enable X-Forwarded-For header processing (Component D (ukabu-extras) feature) |

---

## Use Case Examples

### Use Case 1: Basic Website

**Scenario:** Simple static site or basic web application with standard content delivery.

**Characteristics:**
- Standard security (difficulty 18)
- 7-day cookie duration for good user experience
- Exempt static assets (CSS, JS, images)
- No restricted paths (fully public)

**Configuration:**

```json
{
  "domains": {
    "example.com": {
      "pow_difficulty": 18,
      "hmac_secret_file": "/etc/ukabu/secrets/example.com.key",
      "cookie_duration": 604800,
      "lockout_period": 10080,
      "excuse_first_timeout": false,
      "exempt_paths": [
        "/static/*",
        "/images/*",
        "/css/*",
        "/js/*",
        "/favicon.ico",
        "/robots.txt",
        "/sitemap.xml"
      ],
      "restricted_paths": {},
      "xff_handling": {
        "enabled": false
      }
    }
  }
}
```

**Why These Settings?**
- **Standard difficulty (18):** Balances security with user experience
- **Static asset exemption:** Prevents PoW challenges on every CSS/JS/image request
- **SEO-friendly:** Exempts robots.txt and sitemap.xml for search engines
- **No restrictions:** Public website accessible to all

**When to Use:**
- Personal websites
- Company websites
- Portfolio sites
- Documentation sites
- Public information portals

---

### Use Case 2: Library OPAC (Koha ILS)

**Scenario:** Integrated Library System with public catalog and restricted reservation functions.

**Characteristics:**
- Standard security (difficulty 18)
- Exempt static templates and resources
- Restrict reservation/checkout to library network only
- Protect against catalog scraping while allowing public access

**Configuration:**

```json
{
  "domains": {
    "opac.library.org": {
      "pow_difficulty": 18,
      "hmac_secret_file": "/etc/ukabu/secrets/opac.library.org.key",
      "cookie_duration": 604800,
      "lockout_period": 10080,
      "excuse_first_timeout": false,
      "exempt_paths": [
        "/opac-tmpl/*",
        "/intranet-tmpl/*",
        "/images/*",
        "/favicon.ico",
        "/robots.txt"
      ],
      "restricted_paths": {
        "/cgi-bin/koha/opac-reserve.pl": ["192.168.1.0/24"],
        "/cgi-bin/koha/opac-shelves.pl": ["192.168.1.0/24"],
        "/cgi-bin/koha/svc/*": ["192.168.1.0/24"]
      },
      "xff_handling": {
        "enabled": false
      }
    }
  }
}
```

**Why These Settings?**
- **Koha template exemption:** Prevents challenges on static template assets
- **Network-restricted actions:** Reserve and shelves functions only from library network (192.168.1.0/24)
- **Service endpoint protection:** Backend services restricted to trusted network
- **Public catalog access:** General browsing protected by PoW but accessible to all

**When to Use:**
- Koha OPAC instances
- Library catalogs (Symphony, Sierra, Alma)
- Academic library systems
- Public library systems

**Important Notes:**
- Replace `192.168.1.0/24` with your actual library network CIDR
- Adjust Koha paths if using different URL schemes
- Consider adding staff client paths to restricted_paths

---

### Use Case 3: WordPress Blog

**Scenario:** Content management system with lower difficulty for better user experience and restricted admin access.

**Characteristics:**
- Lower difficulty (16 bits) for faster solving
- Longer cookie duration (30 days) for returning readers
- Excuse first timeout for mobile users
- Restrict wp-admin to office IP only
- Block xmlrpc.php completely

**Configuration:**

```json
{
  "domains": {
    "blog.example.com": {
      "pow_difficulty": 16,
      "hmac_secret_file": "/etc/ukabu/secrets/blog.example.com.key",
      "cookie_duration": 2592000,
      "lockout_period": 20160,
      "excuse_first_timeout": true,
      "exempt_paths": [
        "/wp-content/themes/*",
        "/wp-content/uploads/*",
        "/wp-content/plugins/*",
        "/wp-includes/*",
        "/feed/",
        "/comments/feed/",
        "/favicon.ico",
        "/robots.txt",
        "/sitemap.xml",
        "/sitemap_index.xml"
      ],
      "restricted_paths": {
        "/wp-admin/*": ["203.0.113.50"],
        "/wp-login.php": ["203.0.113.50"],
        "/xmlrpc.php": []
      },
      "xff_handling": {
        "enabled": false
      }
    }
  }
}
```

**Why These Settings?**
- **Lower difficulty (16):** Faster PoW solving improves reader experience
- **30-day cookie:** Reduces re-challenges for regular readers
- **Excuse first timeout:** Mobile users with intermittent connectivity get second chance
- **Admin restriction:** wp-admin only accessible from office IP (203.0.113.50)
- **xmlrpc.php blocked:** Empty array means no IPs allowed (blocks brute force attacks)
- **Feed exemption:** RSS/Atom feeds accessible to feed readers
- **SEO optimization:** Sitemaps exempted for search engines

**When to Use:**
- WordPress blogs
- WordPress news sites
- Content-focused WordPress sites
- Multi-author blogs

**Important Notes:**
- Replace `203.0.113.50` with your actual office/admin IP
- Consider adding additional admin IPs for remote work
- Monitor xmlrpc.php blocking - some legitimate plugins use it
- Lower difficulty may attract more sophisticated bots - monitor and adjust

**Security Considerations:**
- Blocking xmlrpc.php prevents pingback DDoS and brute force
- Restricting wp-login.php prevents admin brute force
- Consider adding `/wp-json/wp/v2/users` to restricted_paths to prevent user enumeration

---

### Use Case 4: E-commerce Site

**Scenario:** Online store balancing security with customer experience, exempting checkout flow to prevent cart abandonment.

**Characteristics:**
- Standard security (difficulty 18)
- Excuse first timeout for mobile shoppers
- Exempt entire checkout/cart/payment flow
- Restrict admin/backend to internal network
- Longer lockout for persistent bad actors

**Configuration:**

```json
{
  "domains": {
    "shop.example.com": {
      "pow_difficulty": 18,
      "hmac_secret_file": "/etc/ukabu/secrets/shop.example.com.key",
      "cookie_duration": 604800,
      "lockout_period": 10080,
      "excuse_first_timeout": true,
      "exempt_paths": [
        "/static/*",
        "/media/*",
        "/skin/*",
        "/js/*",
        "/checkout/*",
        "/cart/*",
        "/payment/*",
        "/api/cart/*",
        "/favicon.ico",
        "/robots.txt"
      ],
      "restricted_paths": {
        "/admin/*": ["10.0.0.0/8"],
        "/backend/*": ["10.0.0.0/8"],
        "/manager/*": ["10.0.0.0/8"]
      },
      "xff_handling": {
        "enabled": false
      }
    }
  }
}
```

**Why These Settings?**
- **Checkout exemption:** No PoW during checkout prevents cart abandonment
- **Cart API exemption:** AJAX cart operations work seamlessly
- **Mobile-friendly:** First timeout excused for shoppers with poor connectivity
- **Admin isolation:** Backend only accessible from private network (10.0.0.0/8)
- **Standard cookie duration:** 7-day validity for returning customers

**When to Use:**
- WooCommerce stores
- Magento installations
- Shopify Plus with custom checkout
- Custom e-commerce platforms
- OpenCart stores

**Important Notes:**
- Replace `10.0.0.0/8` with your actual internal network range
- Consider exempting `/account/*` if customers frequently check order status
- Payment gateway webhooks may need exemption
- Test checkout flow thoroughly after deployment

**Performance Considerations:**
- Product browsing is PoW-protected to prevent scraping
- Static assets (product images) are exempted
- Consider CDN for `/media/*` and `/static/*` paths

**Security Trade-offs:**
- Checkout exemption means scrapers can access checkout pages
- Balance: Cart abandonment risk > scraper access to checkout flow
- Admin paths should ONLY be accessible via VPN or office network
- Consider 2FA for admin accounts as additional layer

---

### Use Case 5: API Service

**Scenario:** REST/GraphQL API endpoint with higher security and protection from scraping while allowing authenticated access.

**Characteristics:**
- Higher difficulty (20 bits) for strong protection
- Shorter cookie duration (24 hours)
- Fast lockout (24 hours) for API abuse
- Exempt health/status/metrics endpoints
- Restrict admin/internal APIs to private network

**Configuration:**

```json
{
  "domains": {
    "api.example.com": {
      "pow_difficulty": 20,
      "hmac_secret_file": "/etc/ukabu/secrets/api.example.com.key",
      "cookie_duration": 86400,
      "lockout_period": 1440,
      "excuse_first_timeout": false,
      "exempt_paths": [
        "/static/*",
        "/docs/static/*",
        "/health",
        "/status",
        "/metrics"
      ],
      "restricted_paths": {
        "/admin/*": ["10.0.0.0/8"],
        "/internal/*": ["10.0.0.0/8", "172.16.0.0/12"]
      },
      "xff_handling": {
        "enabled": false
      }
    }
  }
}
```

**Why These Settings?**
- **High difficulty (20):** Significantly slows down automated scraping attempts
- **24-hour cookie:** API consumers need to prove work daily
- **Fast lockout (24h):** Quick response to API abuse
- **Monitoring exemption:** Health checks and metrics accessible without PoW
- **Internal API isolation:** Admin/internal endpoints only from trusted networks
- **No timeout excuse:** API clients should complete challenges reliably

**When to Use:**
- Public REST APIs
- GraphQL endpoints
- API documentation sites with interactive consoles
- Microservice gateways (public-facing)
- Third-party integrations

**Important Notes:**
- API clients with valid authentication tokens should have separate authentication
- PoW is for browser-based API console/documentation access
- Monitoring tools need `/health`, `/status`, `/metrics` exempted
- Consider adding authenticated API clients to IP whitelist
- Replace network ranges with your actual private networks

**Integration Patterns:**

**Pattern 1: API Console (Browser Access)**
- User visits API documentation at `https://api.example.com/docs`
- PoW challenge presented
- Once solved, user can access interactive API console
- Cookie valid for 24 hours

**Pattern 2: Programmatic API Access**
- API clients should use API keys/OAuth tokens
- Whitelist known API client IPs if possible
- PoW should not block authenticated API calls
- Consider separate subdomain for API vs. documentation

**Performance Considerations:**
- Difficulty 20 may take 30-60 seconds to solve on average browser
- Acceptable for documentation access, not for API calls themselves
- Ensure authenticated endpoints bypass PoW via `exempt_paths`

---

### Use Case 6: DSpace Institutional Repository

**Scenario:** Academic digital repository protecting content while allowing open access and scholarly harvesting.

**Characteristics:**
- Standard security (difficulty 18)
- Exempt OAI-PMH harvesting endpoints
- Exempt bitstreams (PDF downloads)
- Restrict admin interface to campus network
- Support for DSpace themes and static content

**Configuration:**

```json
{
  "domains": {
    "dspace.university.edu": {
      "pow_difficulty": 18,
      "hmac_secret_file": "/etc/ukabu/secrets/dspace.university.edu.key",
      "cookie_duration": 604800,
      "lockout_period": 10080,
      "excuse_first_timeout": false,
      "exempt_paths": [
        "/themes/*",
        "/static/*",
        "/bitstream/*",
        "/oai/request",
        "/rss/*",
        "/feed/*",
        "/sword/*",
        "/favicon.ico",
        "/robots.txt"
      ],
      "restricted_paths": {
        "/xmlui/dspace-admin/*": ["192.168.0.0/16"],
        "/jspui/dspace-admin/*": ["192.168.0.0/16"],
        "/server/api/system/*": ["192.168.0.0/16"]
      },
      "xff_handling": {
        "enabled": false
      }
    }
  }
}
```

**Why These Settings?**
- **OAI-PMH exemption:** Allows scholarly harvesting by other repositories
- **Bitstream exemption:** PDF/document downloads work without PoW
- **SWORD exemption:** Deposit protocols for automated submissions
- **RSS/Feed exemption:** Automated alerts and subscriptions work
- **Campus-only admin:** DSpace administration restricted to university network
- **Standard difficulty:** Protects browsing while allowing scholarly access

**When to Use:**
- DSpace 6.x and 7.x installations
- Institutional repositories
- Digital libraries
- Open access repositories
- Academic archives

**Important Notes:**
- Replace `192.168.0.0/16` with your campus network CIDR
- Both XMLUI and JSPUI admin paths covered
- DSpace 7+ REST API admin endpoints also restricted
- OAI-PMH is essential for repository interoperability

**Academic Integration:**
- Harvesting by other repositories continues uninterrupted
- Search engines can index metadata (robots.txt exempted)
- Users can download PDFs without challenge
- Browsing interface is PoW-protected against scraping

**Security Considerations:**
- Bitstream exemption means direct PDF links bypass PoW
- This is acceptable for open access repositories
- Admin interface must only be accessible from secure network
- Consider VPN requirement for remote admin access

---

### Use Case 7: Corporate Intranet

**Scenario:** Internal company portal with very high security, accessible only from corporate network or VPN.

**Characteristics:**
- Very high difficulty (20 bits)
- Short cookie duration (8 hours/workday)
- Fast lockout (24 hours)
- Entire site restricted to corporate networks
- Minimal exempt paths

**Configuration:**

```json
{
  "domains": {
    "intranet.company.com": {
      "pow_difficulty": 20,
      "hmac_secret_file": "/etc/ukabu/secrets/intranet.company.com.key",
      "cookie_duration": 28800,
      "lockout_period": 1440,
      "excuse_first_timeout": false,
      "exempt_paths": [
        "/static/*",
        "/assets/*",
        "/favicon.ico"
      ],
      "restricted_paths": {
        "/*": ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
      },
      "xff_handling": {
        "enabled": false
      }
    }
  }
}
```

**Why These Settings?**
- **Maximum difficulty (20):** Strongest PoW protection
- **8-hour cookie:** Expires at end of workday, requires daily re-authentication
- **24-hour lockout:** Fast response to intrusion attempts
- **Entire site restricted:** `/*` means all paths require network access
- **RFC 1918 networks:** All private IP ranges allowed (adjust to your needs)
- **No timeout excuse:** Corporate users on reliable networks

**When to Use:**
- Internal company portals
- Employee intranets
- Corporate wikis
- Internal tools and dashboards
- HR and payroll systems

**Important Notes:**
- Users MUST be on VPN or office network to access
- Replace IP ranges with your actual corporate networks
- Very short cookie duration for security
- Consider even shorter duration for sensitive HR/payroll sections

**Network Configuration:**
- **10.0.0.0/8:** Class A private network
- **172.16.0.0/12:** Class B private network (172.16.0.0 - 172.31.255.255)
- **192.168.0.0/16:** Class C private network
- Remove ranges you don't use, add VPN pool ranges

**Security Considerations:**
- PoW provides defense-in-depth even within corporate network
- If VPN is compromised, PoW adds additional barrier
- Short cookie duration limits window for stolen token use
- High difficulty makes brute force impractical

**Performance Trade-offs:**
- Difficulty 20 takes 30-60 seconds to solve
- Acceptable for internal systems accessed once daily
- First access of the day requires PoW solving
- Subsequent accesses (within 8 hours) use valid cookie

**Deployment Strategy:**
1. Start with lower difficulty (16) during rollout
2. Monitor false positives and user complaints
3. Gradually increase to 20 over weeks
4. Ensure IT helpdesk is prepared for user questions

---

### Use Case 8: CDN Origin Server

**Scenario:** Origin server behind Cloudflare/Fastly/Akamai with X-Forwarded-For header processing for proper IP detection.

**Characteristics:**
- Standard security (difficulty 18)
- X-Forwarded-For handling enabled (Component D (ukabu-extras))
- Recursive XFF parsing
- Trusted proxy sources configured
- Exempt CDN-specific paths

**Configuration:**

```json
{
  "domains": {
    "cdn-origin.example.com": {
      "pow_difficulty": 18,
      "hmac_secret_file": "/etc/ukabu/secrets/cdn-origin.example.com.key",
      "cookie_duration": 604800,
      "lockout_period": 10080,
      "excuse_first_timeout": false,
      "exempt_paths": [
        "/static/*",
        "/media/*",
        "/cdn-cgi/*",
        "/favicon.ico",
        "/robots.txt"
      ],
      "restricted_paths": {},
      "xff_handling": {
        "enabled": true,
        "header_name": "X-Forwarded-For",
        "recursive": true,
        "trusted_proxy_sources": ["cloudflare", "fastly"],
        "custom_proxies": []
      }
    }
  }
}
```

**Why These Settings?**
- **XFF enabled:** Extract real client IP from X-Forwarded-For header
- **Recursive parsing:** Handle multiple proxy hops correctly
- **Trusted sources:** Only trust IPs from known CDN providers
- **CDN path exemption:** CDN-specific endpoints (/cdn-cgi/*) exempted
- **Standard security:** Balanced protection for CDN-backed sites

**When to Use:**
- Cloudflare-protected sites
- Fastly-backed applications
- Akamai origins
- AWS CloudFront origins
- Any site behind reverse proxy/CDN

**Important Notes:**
- **REQUIRES PHASE 4:** XFF handling is advanced feature
- Configure `trusted_proxy_sources` before enabling
- Test thoroughly - wrong config blocks all traffic
- XFF can be spoofed if proxy sources not properly validated

**Supported CDN Providers:**
- `cloudflare`: Cloudflare CDN
- `fastly`: Fastly CDN
- `akamai`: Akamai CDN (Component D (ukabu-extras))
- `aws_cloudfront`: AWS CloudFront (Component D (ukabu-extras))
- `custom`: Custom proxy IP ranges

**How XFF Works:**

**Without XFF:**
```
Client (1.2.3.4) → CDN (104.16.0.1) → Origin
Origin sees: 104.16.0.1 (CDN IP, not client)
```

**With XFF Enabled:**
```
Client (1.2.3.4) → CDN (104.16.0.1) → Origin
Header: X-Forwarded-For: 1.2.3.4, 104.16.0.1
Origin extracts: 1.2.3.4 (real client IP)
```

**Security Considerations:**
- **CRITICAL:** Only enable if behind trusted proxy
- Validate proxy IP ranges regularly
- Spoofed XFF headers from non-proxy IPs are ignored
- Use `recursive: true` for multiple proxy hops

**Custom Proxy Configuration:**

If using non-standard proxies, add custom IP ranges:

```json
"xff_handling": {
  "enabled": true,
  "header_name": "X-Forwarded-For",
  "recursive": true,
  "trusted_proxy_sources": [],
  "custom_proxies": [
    "203.0.113.0/24",
    "198.51.100.0/24"
  ]
}
```

**Troubleshooting XFF:**

1. **All requests blocked?**
   - Check if CDN IPs are in trusted_proxy_sources
   - Verify CDN provider name matches supported list
   - Check Component D (ukabu-extras) installation

2. **Wrong IPs logged?**
   - Enable `recursive: false` for single proxy
   - Check header_name matches your CDN (CF uses X-Forwarded-For, others may differ)

3. **Still seeing CDN IPs?**
   - XFF handling may not be enabled
   - Verify nginx configuration includes XFF module
   - Check /var/log/ukabu/debug.log

---

## Configuration Parameters Reference

### Core Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `pow_difficulty` | integer | 18 | Number of leading zero bits required in PoW hash (16-22 recommended) |
| `hmac_secret_file` | string | required | Path to file containing HMAC secret for this domain |
| `cookie_duration` | integer | 604800 | Token validity in seconds (604800 = 7 days) |
| `lockout_period` | integer | 10080 | IP lockout duration in minutes (10080 = 7 days) |
| `excuse_first_timeout` | boolean | false | Whether to excuse first timeout without counting as strike |

### Path Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `exempt_paths` | array | `[]` | Paths that bypass PoW challenge (still subject to IP blacklist) |
| `restricted_paths` | object | `{}` | Paths accessible only from specific IP addresses/ranges |

### X-Forwarded-For Handling (Component D (ukabu-extras))

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `xff_handling.enabled` | boolean | false | Enable X-Forwarded-For header processing |
| `xff_handling.header_name` | string | "X-Forwarded-For" | Header name to extract real IP from |
| `xff_handling.recursive` | boolean | true | Parse multiple proxy hops recursively |
| `xff_handling.trusted_proxy_sources` | array | `[]` | Named CDN providers (cloudflare, fastly, etc.) |
| `xff_handling.custom_proxies` | array | `[]` | Custom proxy IP ranges in CIDR notation |

---

## Path Pattern Matching

### Wildcard Syntax

Ukabu supports wildcard patterns in `exempt_paths` and `restricted_paths`:

| Pattern | Matches | Example |
|---------|---------|---------|
| `/exact/path` | Exact path only | `/admin` matches `/admin` only |
| `/path/*` | All direct children | `/api/*` matches `/api/users` but not `/api/v1/users` |
| `/path/**` | Recursive (all descendants) | `/api/**` matches `/api/v1/users/123` |
| `*.extension` | File extension | `*.pdf` matches any PDF file |

### Examples

```json
"exempt_paths": [
  "/static/*",           // Matches /static/style.css, /static/logo.png
  "/api/public/**",      // Matches /api/public/v1/users, /api/public/v2/posts
  "*.jpg",               // Matches any JPEG file at any level
  "/robots.txt",         // Exact match only
  "/uploads/*.pdf"       // PDFs directly in /uploads/ only
]
```

### Precedence Rules

When a path matches multiple rules:

1. **IP Blacklist** (highest priority) - blocks immediately
2. **Restricted Paths** with IP match - allows without PoW
3. **IP Whitelist** - allows without PoW
4. **Exempt Paths** - bypasses PoW but subject to blacklist
5. **Default** - requires PoW challenge

---

## Best Practices

### Security Best Practices

1. **Start Conservative**
   - Begin with difficulty 18 (default)
   - Enable `excuse_first_timeout` for public-facing sites
   - Monitor logs and adjust based on false positives

2. **Exempt Static Content**
   - Always exempt `/static/*`, `/css/*`, `/js/*`, `/images/*`
   - Prevents PoW challenge on every resource load
   - Improves page load performance significantly

3. **Protect Admin Interfaces**
   - Always use `restricted_paths` for admin areas
   - Restrict to specific IP ranges (office, VPN)
   - Consider additional authentication (2FA)

4. **SEO Considerations**
   - Exempt `/robots.txt`, `/sitemap.xml`, `/sitemap_index.xml`
   - Configure search engine verification (Component D (ukabu-extras))
   - Monitor Google Search Console for crawl errors

5. **Secret Management**
   - Generate strong HMAC secrets (32+ characters)
   - Store secrets in `/etc/ukabu/secrets/` with restrictive permissions (600)
   - Rotate secrets periodically (requires user re-challenge)
   - Never commit secrets to version control

6. **Mobile Users**
   - Enable `excuse_first_timeout: true` for public sites
   - Mobile networks can be unreliable
   - First timeout doesn't count as strike

### Performance Best Practices

1. **Difficulty Tuning**
   - Difficulty 16: ~2-5 seconds (low security, fast)
   - Difficulty 18: ~10-20 seconds (balanced, recommended)
   - Difficulty 20: ~30-60 seconds (high security, slow)
   - Difficulty 22: ~2-5 minutes (maximum security, very slow)

2. **Cookie Duration**
   - Longer duration = fewer re-challenges = better UX
   - Shorter duration = better security
   - Public sites: 7-30 days
   - Internal systems: 8-24 hours
   - Sensitive systems: 1-4 hours

3. **Lockout Periods**
   - Shorter = faster recovery for false positives
   - Longer = better protection against persistent attackers
   - Public sites: 7 days (10080 minutes)
   - API services: 1 day (1440 minutes)
   - Adjust based on attack patterns in logs

### Operational Best Practices

1. **Monitoring**
   - Monitor `/var/log/ukabu/failed_attempts.log` daily
   - Set up alerts for high failure rates
   - Review blocked IPs weekly
   - Check for false positives regularly

2. **Testing**
   - Test configuration in staging environment first
   - Validate JSON syntax: `jq . /etc/ukabu/config/domains.json`
   - Test nginx config: `nginx -t`
   - Test PoW challenge flow manually
   - Test from different browsers and devices

3. **Maintenance**
   - Review and update exempt_paths quarterly
   - Rotate HMAC secrets annually
   - Update restricted_paths when IPs change
   - Review lockout periods based on attack patterns

4. **Documentation**
   - Document custom path exemptions and reasons
   - Maintain list of restricted IPs with ownership
   - Document difficulty changes and rationale
   - Keep changelog of configuration changes

---

## Quick Start Guide

### Step 1: Choose Your Use Case

Identify which example matches your needs:
- Basic website → Use Case 1
- Library system → Use Case 2
- WordPress site → Use Case 3
- E-commerce → Use Case 4
- API service → Use Case 5
- Repository → Use Case 6
- Intranet → Use Case 7
- Behind CDN → Use Case 8

### Step 2: Copy Configuration Template

```bash
# Create configuration file
sudo nano /etc/ukabu/config/domains.json
```

Copy the relevant use case configuration from this guide.

### Step 3: Customize for Your Domain

1. Change domain name (e.g., `example.com` → `yourdomain.com`)
2. Update `hmac_secret_file` path
3. Adjust `exempt_paths` for your application structure
4. Configure `restricted_paths` with your actual IP ranges
5. Set appropriate `pow_difficulty` (start with 18)

### Step 4: Generate HMAC Secret

```bash
# Generate secret for your domain
ukabu-manager domain add yourdomain.com --difficulty 18

# Or manually:
openssl rand -hex 32 > /etc/ukabu/secrets/yourdomain.com.key
chmod 600 /etc/ukabu/secrets/yourdomain.com.key
```

### Step 5: Validate and Apply

```bash
# Validate JSON syntax
jq . /etc/ukabu/config/domains.json

# Test nginx configuration
sudo nginx -t

# Apply configuration
sudo systemctl reload nginx
```

### Step 6: Test the Configuration

1. Visit your domain in a browser
2. Verify PoW challenge appears
3. Solve challenge and verify cookie is set
4. Refresh page - should not show challenge again
5. Test exempt paths (should load without challenge)
6. Test restricted paths (should block from unauthorized IPs)

### Step 7: Monitor and Adjust

```bash
# Watch failed attempts
sudo tail -f /var/log/ukabu/failed_attempts.log

# Check nginx access log
sudo tail -f /var/log/nginx/access.log | grep ukabu

# View current status
ukabu-manager status
```

---

## Troubleshooting Common Issues

### Issue: All Requests Blocked

**Symptoms:** Every request returns 403 or 444

**Solutions:**
1. Check if your IP is in blacklist: `ukabu-manager blacklist list`
2. Verify domain exists in domains.json
3. Check nginx error log: `tail /var/log/nginx/error.log`
4. Verify HMAC secret file exists and is readable

### Issue: Challenge Never Completes

**Symptoms:** PoW challenge runs but never redirects

**Solutions:**
1. Check browser console for JavaScript errors
2. Verify `/ukabu_validate` endpoint is accessible
3. Check difficulty isn't too high (try reducing from 20 to 18)
4. Clear browser cache and cookies
5. Test in different browser

### Issue: Challenge Appears on Every Request

**Symptoms:** Cookie not being set/retained

**Solutions:**
1. Verify domain matches (www vs non-www)
2. Check if HTTPS is properly configured
3. Verify cookie attributes (Secure flag requires HTTPS)
4. Check browser cookie settings
5. Review nginx configuration for cookie handling

### Issue: Static Assets Showing Challenge

**Symptoms:** CSS/JS/images triggering PoW

**Solutions:**
1. Add paths to `exempt_paths` array
2. Verify wildcard patterns match correctly
3. Test with explicit path (no wildcards) first
4. Check nginx configuration includes enforcement.inc properly

### Issue: False Positives (Legitimate Users Blocked)

**Symptoms:** Real users getting blocked

**Solutions:**
1. Enable `excuse_first_timeout: true`
2. Reduce difficulty from 20 to 18 or 16
3. Increase `lockout_period` to reduce permanent blocks
4. Add user's IP range to whitelist temporarily
5. Review failed_attempts.log for patterns

---

## Appendix A: Difficulty Reference Table

| Difficulty | Avg Solve Time | Leading Zeros | Use Case |
|------------|----------------|---------------|----------|
| 14 | 1-2 seconds | ~3.5 | Testing only, very weak |
| 16 | 2-5 seconds | ~4.0 | Low security, public blogs |
| 18 | 10-20 seconds | ~4.5 | **Recommended default** |
| 20 | 30-60 seconds | ~5.0 | High security, API/intranet |
| 22 | 2-5 minutes | ~5.5 | Maximum security, rare use |
| 24 | 10-20 minutes | ~6.0 | Not recommended, too slow |

**Note:** Actual solve times vary based on client hardware and browser efficiency.

---

## Appendix B: Cookie Duration Reference

| Duration (seconds) | Duration (human) | Use Case |
|-------------------|------------------|----------|
| 3600 | 1 hour | High security, frequent re-auth |
| 28800 | 8 hours | Workday sessions |
| 86400 | 1 day | API services, daily access |
| 604800 | 7 days | **Default, balanced UX** |
| 2592000 | 30 days | Public blogs, long sessions |
| 7776000 | 90 days | Low security, max convenience |

---

## Appendix C: Lockout Period Reference

| Duration (minutes) | Duration (human) | Use Case |
|-------------------|------------------|----------|
| 60 | 1 hour | Very lenient, testing |
| 1440 | 1 day | API services, fast recovery |
| 10080 | 7 days | **Default, balanced** |
| 20160 | 2 weeks | Public sites, fewer false positives |
| 43200 | 30 days | High security, persistent attackers |
| 0 | Permanent | Manual removal required |

---

## Support and Documentation

For more information:
- Main documentation: `/usr/share/doc/ukabu/README.md`
- CLI reference: `ukabu-manager --help`
- Logs: `/var/log/ukabu/`
- Configuration: `/etc/ukabu/config/`

**Copyright © 2025 L2C2 Technologies. All rights reserved.**
