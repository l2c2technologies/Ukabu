# UKABU WAF - Component D (ukabu-extras) Quick Start

**Copyright (c) 2025 by L2C2 Technologies. All rights reserved.**

For licensing inquiries: **Indranil Das Gupta** <indradg@l2c2.co.in>

---

## 5-Minute Setup

### Prerequisites

âœ“ Component A (ukabu-core), 2, and 3 installed  
âœ“ Python 3.10+  
âœ“ curl, jq installed  
âœ“ Root access

### Step 1: Install Component D (ukabu-extras) (2 minutes)

```bash
# Extract and install
tar -xzf ukabu-component4.tar.gz
cd ukabu-component4
sudo bash install-component4.sh
```

### Step 2: Verify Installation (1 minute)

```bash
# Run test suite
sudo bash test-component4.sh

# Should see: "âœ“ All tests passed!"
```

### Step 3: Configure Features (2 minutes)

#### Scenario A: Domain Behind Cloudflare

```bash
# Enable XFF for CDN-backed domain
sudo ukabu-manager xff enable cdn-site.com --sources cloudflare

# Regenerate config and reload
sudo ukabu-manager nginx generate-config -d cdn-site.com
sudo ukabu-manager nginx reload
```

#### Scenario B: Direct Connection (No CDN)

```bash
# Add exempt paths
sudo ukabu-manager paths add-exempt example.com /static/*
sudo ukabu-manager paths add-exempt example.com /images/*

# Add restricted admin area
sudo ukabu-manager paths add-restricted example.com /admin/* 192.168.1.0/24

# Regenerate config and reload
sudo ukabu-manager nginx generate-config -d example.com
sudo ukabu-manager nginx reload
```

---

## Common Tasks

### Enable XFF for Domain

```bash
# Cloudflare only
sudo ukabu-manager xff enable example.com --sources cloudflare

# Multiple CDNs
sudo ukabu-manager xff enable example.com --sources cloudflare,aws,google

# Add custom proxy (internal load balancer)
sudo ukabu-manager xff add-proxy example.com 10.0.0.5
```

### Configure Paths

```bash
# Exempt static assets (bypass PoW)
sudo ukabu-manager paths add-exempt example.com /static/*
sudo ukabu-manager paths add-exempt example.com /favicon.ico

# Restrict admin area to office network
sudo ukabu-manager paths add-restricted example.com /admin/* 203.0.113.0/24
```

### Search Engine Verification

```bash
# Verify IP is search engine
sudo ukabu-manager search-engine verify 66.249.64.1

# Manual update (runs automatically daily)
sudo systemctl start ukabu-update-search-engines.service

# List recognized engines
sudo ukabu-manager search-engine list
```

### Extract ML Dataset

```bash
# Last 24 hours to JSON
sudo ukabu-manager ml extract --format json --output /tmp/data.json --hours 24

# Last week to CSV
sudo ukabu-manager ml extract --format csv --output /tmp/week.csv --days 7

# Specific domain only
sudo ukabu-manager ml extract --format json --output /tmp/cdn.json \
  --domains cdn-site.com --hours 48
```

---

## Verification

### Check XFF Configuration

```bash
# Show XFF settings for domain
sudo ukabu-manager xff show cdn-site.com

# Should show:
#   Enabled: True
#   Trusted CDN Sources: cloudflare
```

### Check CDN IP Updates

```bash
# View Cloudflare ranges
head -20 /etc/ukabu/config/trusted_proxies_cloudflare.conf

# Check update log
tail -f /var/log/ukabu/cdn-updates.log
```

### Check Search Engine IPs

```bash
# View Google bot ranges
head -20 /etc/ukabu/config/search_engines_google.conf

# Check update log
tail -f /var/log/ukabu/search-engines.log
```

### Verify Systemd Timers

```bash
# Check timer status
systemctl status ukabu-update-proxies.timer
systemctl status ukabu-update-search-engines.timer

# View next run time
systemctl list-timers | grep ukabu
```

---

## Troubleshooting

### XFF Not Working

```bash
# Check domain has XFF enabled
sudo ukabu-manager xff show example.com

# Verify CDN IPs are populated
wc -l /etc/ukabu/config/trusted_proxies_cloudflare.conf

# Test nginx config
sudo nginx -t

# Check logs
sudo tail -f /var/log/nginx/error.log
```

### Search Engines Not Recognized

```bash
# Check IP lists
wc -l /etc/ukabu/config/search_engines_google.conf

# Force update
sudo systemctl start ukabu-update-search-engines.service

# Verify specific IP
sudo ukabu-manager search-engine verify 66.249.64.1
```

### ML Extraction Errors

```bash
# Check log format
sudo grep "log_format combined_enhanced" /etc/nginx/nginx.conf

# Verify log file exists
ls -lh /var/log/nginx/access.log

# Test extraction with verbose
sudo ukabu-manager -v ml extract --format json --output /tmp/test.json --hours 1
```

---

## What's Next?

- **Fine-tune difficulty**: Adjust PoW difficulty per domain
- **Monitor performance**: Check Prometheus metrics
- **Extract datasets**: Use ML extraction for analysis
- **Customize paths**: Add more exempt and restricted paths

See **README-PHASE4.md** for complete documentation.

---

**Copyright (c) 2025 by L2C2 Technologies. All rights reserved.**
