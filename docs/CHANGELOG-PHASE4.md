# UKABU WAF - Component D (ukabu-extras) Changelog

**Copyright (c) 2025 by L2C2 Technologies. All rights reserved.**

For licensing inquiries: **Indranil Das Gupta** <indradg@l2c2.co.in>

---

## Version 4.0.0 - 2025-11-09

### ðŸŽ¯ Major Features

#### X-Forwarded-For (XFF) Handling
- **Secure by default**: XFF disabled unless explicitly enabled per-domain
- **Per-domain configuration**: Enable/disable XFF independently for each domain
- **Auto-updating CDN proxies**: Daily updates from official sources
  - Cloudflare (https://www.cloudflare.com/ips-v4)
  - AWS CloudFront (https://ip-ranges.amazonaws.com/ip-ranges.json)
  - Google Cloud CDN (https://www.gstatic.com/ipranges/cloud.json)
  - DigitalOcean Spaces CDN
- **Custom trusted proxies**: Support for internal load balancers
- **XFF spoofing prevention**: Only trusts XFF when request from trusted proxy IP

#### Search Engine Detection
- **Google/Googlebot**: IP whitelist verification (status 102)
  - Auto-updated from https://www.gstatic.com/ipranges/goog.json
  - Fast ipset-based lookup (<1ms)
  - Daily updates via systemd timer
- **Bing/Bingbot**: Reverse DNS verification (status 102)
  - 2-step verification: reverse + forward DNS
  - 24-hour caching for performance
  - Prevents spoofing
- **Automatic bypass**: Verified search engines skip PoW challenge

#### Path Management CLI
- **Exempt paths**: Add/remove paths that bypass PoW challenge
  - `ukabu-manager paths add-exempt <domain> <path>`
  - `ukabu-manager paths remove-exempt <domain> <path>`
  - `ukabu-manager paths list-exempt <domain>`
- **Restricted paths**: IP-restricted access control
  - `ukabu-manager paths add-restricted <domain> <path> <allowed_ip>`
  - `ukabu-manager paths remove-restricted-ip <domain> <path> <ip>`
  - `ukabu-manager paths remove-restricted <domain> <path>`
  - `ukabu-manager paths list-restricted <domain>`
- **Idempotent operations**: Safe to run multiple times

#### ML Log Extraction
- **On-demand extraction**: Extract training datasets from nginx access logs
- **Multiple formats**: JSON and CSV output
- **Time-based filtering**: Last N hours/days or specific date range
- **Domain filtering**: Extract data for specific domains only
- **Field selection**: Customize which fields to extract
- **Extracted fields**:
  - timestamp, ip, domain, method, path, status
  - ukabu_status, user_agent, request_time
  - upstream_response_time, ssl_protocol, ssl_cipher
  - request_id, xff, referer

#### Enhanced Logging
- **Request timing**: Added $request_time to nginx logs
- **Upstream timing**: Added $upstream_response_time
- **TLS metrics**: Added $ssl_protocol and $ssl_cipher
- **Request IDs**: Unique identifier for each request

### ðŸ”§ CLI Commands

#### XFF Management
```bash
ukabu-manager xff enable <domain> [--sources cloudflare,aws,google,digitalocean]
ukabu-manager xff disable <domain>
ukabu-manager xff add-proxy <domain> <ip_or_cidr>
ukabu-manager xff remove-proxy <domain> <ip_or_cidr>
ukabu-manager xff show <domain>
ukabu-manager xff list
```

#### Path Management
```bash
ukabu-manager paths add-exempt <domain> <path>
ukabu-manager paths remove-exempt <domain> <path>
ukabu-manager paths list-exempt <domain>
ukabu-manager paths add-restricted <domain> <path> <allowed_ip>
ukabu-manager paths remove-restricted-ip <domain> <path> <ip>
ukabu-manager paths remove-restricted <domain> <path>
ukabu-manager paths list-restricted <domain>
```

#### Search Engine Management
```bash
ukabu-manager search-engine verify <ip>
ukabu-manager search-engine update [--google] [--bing]
ukabu-manager search-engine list
ukabu-manager search-engine clear-cache --bing
```

#### ML Extraction
```bash
ukabu-manager ml extract --format <json|csv> --output <file>
ukabu-manager ml extract --hours <N>
ukabu-manager ml extract --days <N>
ukabu-manager ml extract --start <date> --end <date>
ukabu-manager ml extract --domains <domain1,domain2>
ukabu-manager ml extract --ukabu-status <status>
ukabu-manager ml extract --min-request-time <seconds>
ukabu-manager ml extract --fields <field1,field2>
```

### ðŸ¤– Automation

#### Systemd Timers
- **ukabu-update-proxies.timer**: Daily at 3:00 AM
  - Updates Cloudflare, AWS, Google, DigitalOcean IP ranges
  - Regenerates nginx config
  - Tests and reloads nginx
- **ukabu-update-search-engines.timer**: Daily at 3:05 AM
  - Updates Google bot IP whitelist
  - Regenerates nginx config
  - Tests and reloads nginx

#### Update Scripts
- **ukabu-fetch-cdn-ips.sh**: CDN proxy IP updater
- **ukabu-fetch-google-ips.sh**: Google bot IP updater
- **ukabu-verify-bing.py**: Bing bot DNS verifier

### ðŸ“ New Files

#### Python Modules
- `/usr/local/lib/ukabu/xff.py` - XFF management
- `/usr/local/lib/ukabu/paths.py` - Path management
- `/usr/local/lib/ukabu/ml_extract.py` - ML extraction
- `/usr/local/lib/ukabu/search_engines.py` - Search engine detection

#### Scripts
- `/usr/local/bin/ukabu-fetch-cdn-ips.sh` - CDN IP updater
- `/usr/local/bin/ukabu-fetch-google-ips.sh` - Google IP updater
- `/usr/local/bin/ukabu-verify-bing.py` - Bing verifier

#### Configuration Files
- `/etc/ukabu/config/trusted_proxies_cloudflare.conf`
- `/etc/ukabu/config/trusted_proxies_aws.conf`
- `/etc/ukabu/config/trusted_proxies_google.conf`
- `/etc/ukabu/config/trusted_proxies_digitalocean.conf`
- `/etc/ukabu/config/trusted_proxies_custom.conf`
- `/etc/ukabu/config/search_engines_google.conf`
- `/etc/ukabu/config/search_engines_bing_cache.json`

#### Systemd Units
- `/etc/systemd/system/ukabu-update-proxies.service`
- `/etc/systemd/system/ukabu-update-proxies.timer`
- `/etc/systemd/system/ukabu-update-search-engines.service`
- `/etc/systemd/system/ukabu-update-search-engines.timer`

#### Logs
- `/var/log/ukabu/cdn-updates.log` - CDN IP update log
- `/var/log/ukabu/search-engines.log` - Search engine update log

### ðŸ”’ Security Enhancements

- **XFF disabled by default**: Prevents IP spoofing attacks
- **Trusted proxy validation**: Only accepts XFF from verified CDN IPs
- **Search engine verification**: 2-step DNS verification for Bing prevents spoofing
- **Secure file permissions**: Extracted ML datasets created with 0600 permissions
- **Systemd hardening**: Services run with restricted permissions

### âš¡ Performance

- **XFF lookup**: <1ms (nginx geo map)
- **Google verification**: <1ms (ipset lookup)
- **Bing verification**: 50-200ms first request, <1ms cached (24h TTL)
- **ML extraction**: 1GB log ~10-30 seconds (offline processing)

### ðŸ“Š Compatibility

- **Requires**: Component A (ukabu-core), 2, and 3
- **Python**: 3.10+
- **Tools**: curl, jq
- **nginx**: With NJS module
- **OS**: Ubuntu 20.04+, Debian 11+, RHEL 8+

### ðŸ› Bug Fixes

- None (initial release)

### ðŸ”„ Breaking Changes

- None (backward compatible with Component C (ukabu-manager))

### ðŸ“ Documentation

- **README-PHASE4.md**: Complete Component D (ukabu-extras) guide
- **CHANGELOG-PHASE4.md**: This file
- **test-component4.sh**: Test script
- **install-component4.sh**: Installation script

### ðŸ™ Credits

- Cloudflare for IP range API
- AWS for IP ranges JSON
- Google for GCP and search IP ranges
- DigitalOcean for CDN documentation

---

## Upgrade Notes

### From Component C (ukabu-manager) to Component D (ukabu-extras)

1. Extract Component D (ukabu-extras) tarball:
   ```bash
   tar -xzf ukabu-component4.tar.gz
   cd ukabu-component4
   ```

2. Run installation script:
   ```bash
   sudo bash install-component4.sh
   ```

3. Test installation:
   ```bash
   sudo bash test-component4.sh
   ```

4. Enable XFF for CDN-backed domains (if applicable):
   ```bash
   sudo ukabu-manager xff enable cdn-site.com --sources cloudflare
   sudo ukabu-manager nginx generate-config -d cdn-site.com
   sudo ukabu-manager nginx reload
   ```

5. Configure path rules as needed:
   ```bash
   sudo ukabu-manager paths add-exempt example.com /static/*
   sudo ukabu-manager paths add-restricted example.com /admin/* 192.168.1.0/24
   sudo ukabu-manager nginx generate-config -d example.com
   sudo ukabu-manager nginx reload
   ```

6. Verify systemd timers are running:
   ```bash
   systemctl status ukabu-update-proxies.timer
   systemctl status ukabu-update-search-engines.timer
   ```

### Configuration Changes

Component D (ukabu-extras) adds the following to `domains.json`:

```json
{
  "domains": {
    "example.com": {
      "xff_handling": {
        "enabled": false,
        "trusted_proxy_sources": [],
        "custom_proxies": []
      }
    }
  }
}
```

This is automatically added when using `ukabu-manager xff enable`.

---

## Known Issues

- **Bing verification latency**: First verification can take 50-200ms due to DNS lookups. This is cached for 24 hours.
- **DigitalOcean ranges**: Not published officially, using known data center ranges
- **ML extraction log format**: Requires nginx log format to match `combined_enhanced` exactly

---

## Future Enhancements (Phase 5)

- Prometheus exporter enhancements
- Grafana dashboards
- Web UI for configuration
- Real-time monitoring
- Additional search engines (Yandex, Baidu, DuckDuckGo)
- ML-based anomaly detection
- Automatic difficulty adjustment

---

**Copyright (c) 2025 by L2C2 Technologies. All rights reserved.**

For licensing inquiries:  
**Indranil Das Gupta** <indradg@l2c2.co.in>  
L2C2 Technologies
