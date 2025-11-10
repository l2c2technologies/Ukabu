# UKABU WAF - Component D (ukabu-extras): Advanced Features

**Copyright (c) 2025 by L2C2 Technologies. All rights reserved.**

For licensing inquiries: **Indranil Das Gupta** <indradg@l2c2.co.in>

---

## Component D (ukabu-extras) Objectives

Ã¢Å“â€¦ **X-Forwarded-For (XFF) Handling** - Per-domain, secure by default  
Ã¢Å“â€¦ **CDN Proxy Auto-Updater** - Daily updates for Cloudflare, AWS, Google, DigitalOcean  
Ã¢Å“â€¦ **Search Engine Detection** - Google (IP whitelist), Bing (reverse DNS)  
Ã¢Å“â€¦ **Path Management CLI** - Add/remove exempt and restricted paths  
Ã¢Å“â€¦ **ML Log Extraction** - On-demand dataset generation from nginx logs  
Ã¢Å“â€¦ **Enhanced Logging** - Request timing, TLS metrics for analysis  

---

## What's New in Component D (ukabu-extras)

### 1. X-Forwarded-For (XFF) Configuration

**Secure by default:** XFF handling is **disabled** unless explicitly enabled per-domain.

**Per-domain XFF control:**
```bash
# Enable XFF for domain behind Cloudflare
sudo ukabu-manager xff enable example.com --sources cloudflare

# Add custom trusted proxy (internal load balancer)
sudo ukabu-manager xff add-proxy example.com 10.0.0.5

# Disable XFF (revert to direct IP)
sudo ukabu-manager xff disable example.com

# Show XFF configuration
sudo ukabu-manager xff show example.com
```

**Supported CDN sources:**
- `cloudflare` - Cloudflare CDN
- `aws` - AWS CloudFront
- `google` - Google Cloud CDN
- `digitalocean` - DigitalOcean Spaces CDN

### 2. CDN IP Auto-Updater

**Automatic daily updates** of trusted proxy IP ranges:

```bash
# Manual update (runs automatically daily at 3 AM)
sudo /usr/local/bin/ukabu-fetch-cdn-ips.sh

# Check last update
sudo systemctl status ukabu-update-proxies.service

# View fetched ranges
cat /etc/ukabu/config/trusted_proxies_cloudflare.conf
```

**Systemd timer:** `ukabu-update-proxies.timer` runs daily at 3:00 AM

### 3. Search Engine Detection

**Google/Googlebot:**
- IP whitelist auto-updated from https://www.gstatic.com/ipranges/goog.json
- Status code: **102** (bypasses PoW)

**Bing/Bingbot:**
- Reverse DNS verification (2-step process)
- Cached results for performance
- Status code: **102** (bypasses PoW)

```bash
# Manual update of search engine IPs
sudo /usr/local/bin/ukabu-fetch-google-ips.sh

# View recognized search engine IPs
cat /etc/ukabu/config/search_engines_google.conf

# Check if IP is recognized as search engine
sudo ukabu-manager search-engine verify 66.249.64.1
```

### 4. Path Management CLI

**Exempt paths** (bypass PoW challenge):
```bash
# Add exempt path
sudo ukabu-manager paths add-exempt example.com /static/*

# Remove exempt path
sudo ukabu-manager paths remove-exempt example.com /static/*

# List exempt paths
sudo ukabu-manager paths list-exempt example.com
```

**Restricted paths** (IP-restricted access):
```bash
# Add restricted path with allowed IP
sudo ukabu-manager paths add-restricted example.com /admin/* 192.168.1.100

# Add additional allowed IP to existing path
sudo ukabu-manager paths add-restricted example.com /admin/* 10.0.0.0/8

# Remove allowed IP from restricted path
sudo ukabu-manager paths remove-restricted-ip example.com /admin/* 192.168.1.100

# Remove entire restricted path
sudo ukabu-manager paths remove-restricted example.com /admin/*

# List restricted paths
sudo ukabu-manager paths list-restricted example.com
```

### 5. ML Log Extraction

**Extract training data** from nginx access logs:

```bash
# Extract last 24 hours to JSON
sudo ukabu-manager ml extract --format json --output /tmp/dataset.json --hours 24

# Extract specific date range to CSV
sudo ukabu-manager ml extract --format csv --output /tmp/data.csv \
  --start "2025-11-01" --end "2025-11-08"

# Include only specific domains
sudo ukabu-manager ml extract --format json --domains example.com,api.example.com \
  --output /tmp/filtered.json

# Extract with specific fields
sudo ukabu-manager ml extract --format csv --output /tmp/custom.csv \
  --fields ip,user_agent,request_time,ukabu_status,ssl_cipher
```

**Extracted fields:**
- `timestamp` - Request time (ISO 8601)
- `ip` - Client IP address
- `domain` - Requested domain
- `method` - HTTP method
- `path` - Request path
- `status` - HTTP status code
- `ukabu_status` - UKABU status code (100-104, 200-201)
- `user_agent` - Client user agent
- `request_time` - Total request time (seconds)
- `upstream_response_time` - Backend response time
- `ssl_protocol` - TLS version
- `ssl_cipher` - Cipher suite
- `request_id` - Unique request identifier

---

## Installation

### Prerequisites

- Component A (ukabu-core), 2, and 3 must be installed
- Python 3.10+
- curl, jq (for CDN IP fetching)
- Root privileges

### Install Component D (ukabu-extras)

```bash
# Extract tarball
tar -xzf ukabu-component4.tar.gz
cd ukabu-component4

# Run installation script
sudo bash install-component4.sh
```

The installer will:
1. Install Component D (ukabu-extras) Python modules
2. Install CDN IP fetcher scripts
3. Set up systemd timers for auto-updates
4. Update nginx configuration templates
5. Enable search engine detection

---

## Configuration

### Enable XFF for CDN-Backed Domain

```bash
# 1. Enable XFF for domain
sudo ukabu-manager xff enable cdn-site.com --sources cloudflare aws

# 2. Regenerate nginx config
sudo ukabu-manager nginx generate-config -d cdn-site.com

# 3. Test and reload
sudo ukabu-manager nginx test
sudo ukabu-manager nginx reload
```

### Configure Search Engine Detection

```bash
# Search engines are automatically detected (no configuration needed)
# Google IPs updated daily via ukabu-update-search-engines.timer

# Manual verification of search engine IP
sudo ukabu-manager search-engine verify 66.249.64.1
# Output: Verified: Google (66.249.64.1 in whitelist)

# Manual update (runs automatically daily)
sudo systemctl start ukabu-update-search-engines.service
```

### Set Up Path Rules

```bash
# Example: E-commerce site
sudo ukabu-manager domain add shop.example.com -d 20

# Exempt static assets
sudo ukabu-manager paths add-exempt shop.example.com /images/*
sudo ukabu-manager paths add-exempt shop.example.com /css/*
sudo ukabu-manager paths add-exempt shop.example.com /js/*
sudo ukabu-manager paths add-exempt shop.example.com /favicon.ico

# Restrict admin area to office network
sudo ukabu-manager paths add-restricted shop.example.com /admin/* 203.0.113.0/24

# Regenerate configs
sudo ukabu-manager nginx generate-config -d shop.example.com
sudo ukabu-manager nginx reload
```

---

## Testing

### Test XFF Handling

```bash
# Run Component D (ukabu-extras) test script
sudo bash test-component4.sh

# Manual XFF test
curl -H "X-Forwarded-For: 1.2.3.4" \
     -H "User-Agent: Mozilla/5.0" \
     https://cdn-site.com/ -v
# Should use XFF IP if request from trusted CDN
```

### Test Search Engine Detection

```bash
# Test Google IP recognition
curl -H "User-Agent: Mozilla/5.0 (compatible; Googlebot/2.1)" \
     --interface 66.249.64.1 \
     https://example.com/ -v
# Should return X-Ukabu-Status: 102

# Test Bing reverse DNS
sudo ukabu-manager search-engine verify 40.77.167.0
```

### Test ML Extraction

```bash
# Generate test traffic
for i in {1..100}; do
  curl -s https://example.com/ > /dev/null
done

# Extract dataset
sudo ukabu-manager ml extract --format json --output /tmp/test.json --hours 1

# Verify output
jq '.[0]' /tmp/test.json
```

---

## File Locations

```
/etc/ukabu/config/
  Ã¢"Å“Ã¢"â‚¬Ã¢"â‚¬ trusted_proxies_cloudflare.conf  # Auto-updated Cloudflare IPs
  Ã¢"Å“Ã¢"â‚¬Ã¢"â‚¬ trusted_proxies_aws.conf         # Auto-updated AWS IPs
  Ã¢"Å“Ã¢"â‚¬Ã¢"â‚¬ trusted_proxies_google.conf      # Auto-updated Google Cloud IPs
  Ã¢"Å“Ã¢"â‚¬Ã¢"â‚¬ trusted_proxies_digitalocean.conf # Auto-updated DigitalOcean IPs
  Ã¢"Å“Ã¢"â‚¬Ã¢"â‚¬ trusted_proxies_custom.conf      # Manually configured proxies
  Ã¢"Å“Ã¢"â‚¬Ã¢"â‚¬ search_engines_google.conf       # Auto-updated Google bot IPs
  Ã¢""Ã¢"â‚¬Ã¢"â‚¬ search_engines_bing_cache.json   # Cached Bing DNS verifications

/usr/local/bin/
  Ã¢"Å“Ã¢"â‚¬Ã¢"â‚¬ ukabu-fetch-cdn-ips.sh           # CDN IP updater script
  Ã¢"Å“Ã¢"â‚¬Ã¢"â‚¬ ukabu-fetch-google-ips.sh        # Google bot IP updater
  Ã¢""Ã¢"â‚¬Ã¢"â‚¬ ukabu-verify-bing.py             # Bing reverse DNS verifier

/usr/local/lib/ukabu/
  Ã¢"Å“Ã¢"â‚¬Ã¢"â‚¬ xff.py                           # XFF management module
  Ã¢"Å“Ã¢"â‚¬Ã¢"â‚¬ paths.py                         # Path management module
  Ã¢"Å“Ã¢"â‚¬Ã¢"â‚¬ ml_extract.py                    # ML data extraction module
  Ã¢""Ã¢"â‚¬Ã¢"â‚¬ search_engines.py                # Search engine detection module

/var/log/ukabu/
  Ã¢"Å“Ã¢"â‚¬Ã¢"â‚¬ cdn-updates.log                  # CDN IP update log
  Ã¢""Ã¢"â‚¬Ã¢"â‚¬ search-engines.log               # Search engine verification log
```

---

## Systemd Timers

### CDN Proxy Updater

```bash
# Timer: ukabu-update-proxies.timer
# Runs daily at 3:00 AM

# Check status
systemctl status ukabu-update-proxies.timer

# Manual trigger
sudo systemctl start ukabu-update-proxies.service

# View logs
journalctl -u ukabu-update-proxies.service -f
```

### Search Engine IP Updater

```bash
# Timer: ukabu-update-search-engines.timer
# Runs daily at 3:05 AM

# Check status
systemctl status ukabu-update-search-engines.timer

# Manual trigger
sudo systemctl start ukabu-update-search-engines.service

# View logs
journalctl -u ukabu-update-search-engines.service -f
```

---

## CLI Command Reference

### XFF Management

```bash
# Enable XFF for domain
ukabu-manager xff enable <domain> [--sources SOURCE1,SOURCE2]

# Disable XFF for domain
ukabu-manager xff disable <domain>

# Add custom trusted proxy
ukabu-manager xff add-proxy <domain> <ip_or_cidr>

# Remove custom trusted proxy
ukabu-manager xff remove-proxy <domain> <ip_or_cidr>

# Show XFF configuration
ukabu-manager xff show <domain>

# List domains with XFF enabled
ukabu-manager xff list
```

### Path Management

```bash
# Exempt paths (bypass PoW)
ukabu-manager paths add-exempt <domain> <path>
ukabu-manager paths remove-exempt <domain> <path>
ukabu-manager paths list-exempt <domain>

# Restricted paths (IP-restricted)
ukabu-manager paths add-restricted <domain> <path> <allowed_ip>
ukabu-manager paths remove-restricted-ip <domain> <path> <ip>
ukabu-manager paths remove-restricted <domain> <path>
ukabu-manager paths list-restricted <domain>
```

### Search Engine Management

```bash
# Verify if IP is a search engine
ukabu-manager search-engine verify <ip>

# Update search engine IP lists (manual)
ukabu-manager search-engine update [--google] [--bing]

# Show recognized search engines
ukabu-manager search-engine list

# Clear Bing DNS cache
ukabu-manager search-engine clear-cache --bing
```

### ML Extraction

```bash
# Basic extraction
ukabu-manager ml extract --format <json|csv> --output <file>

# Time-based extraction
ukabu-manager ml extract --hours <N>          # Last N hours
ukabu-manager ml extract --days <N>           # Last N days
ukabu-manager ml extract --start <date> --end <date>

# Filtered extraction
ukabu-manager ml extract --domains <domain1,domain2>
ukabu-manager ml extract --ukabu-status <status>    # e.g., 200,201
ukabu-manager ml extract --min-request-time <seconds>

# Custom fields
ukabu-manager ml extract --fields <field1,field2,field3>
```

---

## Troubleshooting

### XFF Not Working

```bash
# Check if domain has XFF enabled
sudo ukabu-manager xff show example.com

# Verify CDN IP lists are populated
sudo cat /etc/ukabu/config/trusted_proxies_cloudflare.conf

# Check nginx geo map
sudo ukabu-manager nginx generate-config
sudo nginx -t

# Test with specific IP
sudo ukabu-manager xff test-ip 173.245.48.10
# Should return: Trusted (Cloudflare)
```

### Search Engine Detection Not Working

```bash
# Check Google IP list
cat /etc/ukabu/config/search_engines_google.conf | wc -l
# Should show 100+ ranges

# Manual verification
sudo ukabu-manager search-engine verify 66.249.64.1

# Check systemd timer
systemctl status ukabu-update-search-engines.timer

# Force update
sudo systemctl start ukabu-update-search-engines.service
```

### ML Extraction Issues

```bash
# Check nginx log format
sudo grep "log_format combined_enhanced" /etc/nginx/nginx.conf

# Verify log file exists
ls -lh /var/log/nginx/access.log

# Test extraction with verbose output
sudo ukabu-manager -v ml extract --format json --output /tmp/test.json --hours 1

# Check for parsing errors
sudo tail -f /var/log/ukabu/manager.log
```

---

## Security Considerations

### XFF Spoofing Prevention

- XFF **disabled by default** (secure default)
- Only trusts XFF when `$remote_addr` in trusted proxy list
- Trusted proxy lists auto-updated from official CDN sources
- Attacker cannot spoof from non-trusted IP

### Search Engine Verification

- **Google**: IP whitelist (no DNS lookups, fast)
- **Bing**: Reverse DNS + forward DNS verification (prevents spoofing)
- Cached results (24-hour TTL) to prevent DNS amplification

### ML Data Privacy

- Logs may contain PII (IP addresses)
- Consider anonymization before external use
- Follow GDPR/privacy regulations
- Secure extracted files (chmod 600)

---

## Performance

### XFF Impact

- Geo map lookup: <1ms (nginx hash table)
- No performance degradation when disabled

### Search Engine Detection

- Google whitelist check: <1ms (ipset lookup)
- Bing DNS verification: 50-200ms (first request), <1ms (cached)

### ML Extraction

- 1GB log file (~5M requests): ~10-30 seconds extraction time
- No impact on live traffic (offline processing)

---

## What's Next?

**Phase 5** will add:
- Prometheus exporter enhancements
- Grafana dashboards
- Web UI for configuration
- Real-time monitoring
- Comprehensive documentation

---

## Support

For licensing inquiries and support:

**Indranil Das Gupta**  
Email: indradg@l2c2.co.in  
Organization: L2C2 Technologies

---

## License

**Copyright (c) 2025 by L2C2 Technologies. All rights reserved.**

This software is proprietary. For licensing inquiries, contact:  
**Indranil Das Gupta** <indradg@l2c2.co.in>
