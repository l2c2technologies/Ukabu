# UKABU WAF - Production Deployment Checklist & Hardening Guide

**Copyright © 2025 L2C2 Technologies. All rights reserved.**  
**Contact:** Indranil Das Gupta <indradg@l2c2.co.in>

---

## Pre-Deployment Checklist

### System Requirements ✅

#### Hardware Requirements
- [ ] **CPU:** 2+ cores (4+ recommended for high traffic)
- [ ] **RAM:** 2GB minimum (4GB+ recommended)
- [ ] **Disk:** 10GB minimum (20GB+ recommended for logs)
- [ ] **Network:** 1Gbps network interface

#### Software Requirements
- [ ] **OS:** Ubuntu 20.04+ / Debian 11+ / RHEL 8+ / Rocky Linux 8+
- [ ] **nginx:** 1.18+ with njs module
- [ ] **Go:** 1.19+ (for building ukabu-trackerd)
- [ ] **Python:** 3.10+
- [ ] **iptables** OR **nftables**
- [ ] **ipset:** Latest version
- [ ] **SQLite3:** 3.x

#### Verify Installation
```bash
# Check nginx with njs
nginx -V 2>&1 | grep njs

# Check Go version
go version

# Check Python version
python3 --version

# Check iptables/nftables
which iptables || which nft

# Check ipset
ipset --version
```

---

## Phase-by-Phase Installation

### Component A (ukabu-core): nginx PoW Flow ✅

**Time Estimate:** 30 minutes

```bash
# 1. Extract Component A (ukabu-core)
cd /tmp
tar -xzf ukabu-component1.tar.gz
cd ukabu-component1

# 2. Run installation
sudo bash install.sh

# 3. Configure first domain
sudo nano /etc/ukabu/config/domains.json
# Add your domain configuration

# 4. Generate HMAC secret
openssl rand -hex 32 | sudo tee /etc/ukabu/secrets/yourdomain.com.key
sudo chmod 600 /etc/ukabu/secrets/yourdomain.com.key

# 5. Configure nginx vhost
sudo cp examples/example-vhost.conf /etc/nginx/sites-available/yourdomain.com.conf
sudo nano /etc/nginx/sites-available/yourdomain.com.conf
# Update domain name and upstream

# 6. Enable site
sudo ln -s /etc/nginx/sites-available/yourdomain.com.conf /etc/nginx/sites-enabled/

# 7. Test configuration
sudo nginx -t

# 8. Reload nginx
sudo systemctl reload nginx
```

**Verification:**
```bash
# Test static asset (should bypass PoW)
curl -I https://yourdomain.com/static/style.css
# Expected: X-Ukabu-Status: 100

# Test protected page (should challenge)
curl -I https://yourdomain.com/
# Expected: X-Ukabu-Status: 200, HTTP/1.1 302
```

---

### Component B (ukabu-monitor): Go Daemon (Strike Tracking) ✅

**Time Estimate:** 20 minutes

```bash
# 1. Build Go daemon
cd /tmp/ukabu-component2/ukabu-core
make build

# 2. Install daemon
sudo make install

# 3. Create directories
sudo mkdir -p /var/run/ukabu
sudo mkdir -p /var/lib/ukabu

# 4. Install systemd units
sudo cp systemd/ukabu-trackerd.service /etc/systemd/system/
sudo cp systemd/ukabu-ipset-init.service /etc/systemd/system/
sudo cp systemd/ukabu-unjail.service /etc/systemd/system/
sudo cp systemd/ukabu-unjail.timer /etc/systemd/system/

# 5. Reload systemd
sudo systemctl daemon-reload

# 6. Enable and start services
sudo systemctl enable ukabu-ipset-init
sudo systemctl start ukabu-ipset-init

sudo systemctl enable ukabu-trackerd
sudo systemctl start ukabu-trackerd

sudo systemctl enable ukabu-unjail.timer
sudo systemctl start ukabu-unjail.timer

# 7. Verify daemon is running
sudo systemctl status ukabu-trackerd

# 8. Check logs
sudo journalctl -u ukabu-trackerd -f
```

**Verification:**
```bash
# Check ipsets created
sudo ipset list | grep ukabu

# Check daemon socket
sudo ls -la /var/run/ukabu/tracker.sock

# Test daemon communication
echo '{"type":"test"}' | sudo nc -U /var/run/ukabu/tracker.sock
```

---

### Component C (ukabu-manager): Python CLI (ukabu-manager) ✅

**Time Estimate:** 15 minutes

```bash
# 1. Install Python dependencies
sudo pip3 install click jinja2

# 2. Run installation
cd /tmp/ukabu-component3
sudo bash install-component3.sh

# 3. Verify installation
ukabu-manager --version

# 4. Run tests
sudo bash test-component3.sh
```

**Verification:**
```bash
# List domains
sudo ukabu-manager domain list

# Check status
sudo ukabu-manager status

# View strikes
sudo ukabu-manager status --strikes
```

---

### Component D (ukabu-extras): Advanced Features ✅

**Time Estimate:** 20 minutes

```bash
# 1. Run installation
cd /tmp/ukabu-component4
sudo bash install-component4.sh

# 2. Enable timers
sudo systemctl enable ukabu-update-proxies.timer
sudo systemctl start ukabu-update-proxies.timer

sudo systemctl enable ukabu-update-search-engines.timer
sudo systemctl start ukabu-update-search-engines.timer

# 3. Run initial updates
sudo /usr/local/bin/ukabu-fetch-cdn-ips.sh
sudo /usr/local/bin/ukabu-fetch-google-ips.sh

# 4. Run tests
sudo bash test-component4.sh
```

**Verification:**
```bash
# Check CDN IP files
ls -la /etc/ukabu/config/trusted_proxies_*.conf

# Check search engine IPs
cat /etc/ukabu/config/search_engines_google.conf

# Verify timer status
sudo systemctl status ukabu-update-proxies.timer
sudo systemctl status ukabu-update-search-engines.timer
```

---

## Critical Security Hardening

### 1. Rate Limiting (HIGH PRIORITY) ⚠️

**Add to nginx http block:**
```nginx
# /etc/nginx/nginx.conf (inside http block)

# Rate limit zones
limit_req_zone $binary_remote_addr zone=pow_challenge:10m rate=10r/m;
limit_req_zone $binary_remote_addr zone=pow_validate:10m rate=20r/m;
limit_req_zone $binary_remote_addr zone=general:10m rate=100r/m;

# Connection limit
limit_conn_zone $binary_remote_addr zone=conn_limit:10m;
```

**Add to UKABU endpoints.inc:**
```nginx
# /etc/ukabu/includes/endpoints.inc

location = /__pow_challenge {
    limit_req zone=pow_challenge burst=5 nodelay;
    js_content powModule.generateChallenge;
}

location = /__pow_validate {
    limit_req zone=pow_validate burst=10 nodelay;
    js_content powModule.validateSolution;
}

location = /__pow_verify {
    limit_req zone=pow_challenge burst=5 nodelay;
    alias /etc/ukabu/pages/challenge.html;
}
```

**Add to vhost:**
```nginx
# Inside server block
limit_conn conn_limit 50;
limit_req zone=general burst=200 nodelay;
```

---

### 2. Nonce Replay Protection (HIGH PRIORITY) ⚠️

**Add to pow-challenge.js:**
```javascript
// Global nonce cache (in-memory, expires after 10 minutes)
var nonceCache = {};
var NONCE_EXPIRY = 600000; // 10 minutes in milliseconds

// Cleanup old nonces periodically
function cleanupNonces() {
    var now = Date.now();
    for (var nonce in nonceCache) {
        if (now - nonceCache[nonce] > NONCE_EXPIRY) {
            delete nonceCache[nonce];
        }
    }
}

// In validateSolution function, add before HMAC verification:
function validateSolution(r) {
    try {
        var nonce = r.variables.arg_nonce;
        
        // Check for replay
        if (nonceCache[nonce]) {
            r.error("Replay attack detected: " + nonce);
            r.return(403, JSON.stringify({
                error: "Invalid solution: replay detected"
            }));
            return;
        }
        
        // Mark nonce as used
        nonceCache[nonce] = Date.now();
        
        // Cleanup old nonces every 100 requests
        if (Math.random() < 0.01) {
            cleanupNonces();
        }
        
        // Continue with existing validation...
        // ...
    } catch (e) {
        r.error("Validation error: " + e.message);
        r.return(500, JSON.stringify({error: "Server error"}));
    }
}
```

---

### 3. Connection Limits & DoS Protection (MEDIUM PRIORITY)

**Add to nginx http block:**
```nginx
# /etc/nginx/nginx.conf

# Client buffer limits (anti-DoS)
client_body_buffer_size 128k;
client_max_body_size 10m;
client_header_buffer_size 1k;
large_client_header_buffers 4 8k;

# Timeouts
client_body_timeout 12;
client_header_timeout 12;
keepalive_timeout 15;
send_timeout 10;

# Gzip compression (save bandwidth)
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_types text/plain text/css text/xml text/javascript application/javascript application/json;
```

---

### 4. SSL/TLS Hardening (HIGH PRIORITY) ⚠️

**Strong SSL configuration:**
```nginx
# /etc/nginx/sites-available/yourdomain.com.conf

server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    # SSL protocols (TLS 1.2 and 1.3 only)
    ssl_protocols TLSv1.2 TLSv1.3;
    
    # Strong ciphers
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305';
    ssl_prefer_server_ciphers off;
    
    # OCSP stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_trusted_certificate /etc/letsencrypt/live/yourdomain.com/chain.pem;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # ... rest of config
}

# Force HTTPS redirect
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

---

### 5. File Permissions (CRITICAL) ⚠️

**Set correct permissions:**
```bash
# Configuration files
sudo chown root:root /etc/ukabu/config/*.conf
sudo chmod 644 /etc/ukabu/config/*.conf

# HMAC secrets (CRITICAL - root only)
sudo chown root:root /etc/ukabu/secrets/*.key
sudo chmod 600 /etc/ukabu/secrets/*.key

# nginx includes
sudo chown root:root /etc/ukabu/includes/*
sudo chmod 644 /etc/ukabu/includes/*

# NJS module
sudo chown root:root /etc/ukabu/njs/pow-challenge.js
sudo chmod 644 /etc/ukabu/njs/pow-challenge.js

# HTML pages
sudo chown root:root /etc/ukabu/pages/*.html
sudo chmod 644 /etc/ukabu/pages/*.html

# Daemon socket directory
sudo chown root:root /var/run/ukabu
sudo chmod 755 /var/run/ukabu

# Log directory (nginx must write)
sudo chown root:nginx /var/log/ukabu
sudo chmod 750 /var/log/ukabu

# Database directory
sudo chown root:root /var/lib/ukabu
sudo chmod 755 /var/lib/ukabu
sudo chmod 644 /var/lib/ukabu/strikes.db
```

---

### 6. Firewall Rules (CRITICAL) ⚠️

**Only allow necessary ports:**
```bash
# iptables example
sudo iptables -A INPUT -i lo -j ACCEPT
sudo iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT  # SSH
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT  # HTTP
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT # HTTPS
sudo iptables -A INPUT -p icmp -j ACCEPT            # Ping
sudo iptables -A INPUT -j DROP                       # Drop all else

# Save rules
sudo iptables-save | sudo tee /etc/iptables/rules.v4

# For nftables
sudo nft add rule inet filter input iif lo accept
sudo nft add rule inet filter input ct state established,related accept
sudo nft add rule inet filter input tcp dport 22 accept
sudo nft add rule inet filter input tcp dport 80 accept
sudo nft add rule inet filter input tcp dport 443 accept
sudo nft add rule inet filter input icmp type echo-request accept
sudo nft add rule inet filter input drop

# Save nftables
sudo nft list ruleset | sudo tee /etc/nftables.conf
```

**Note:** Prometheus metrics port (9090) should NOT be exposed publicly. Use firewall rules or bind to localhost only.

---

### 7. Privacy & GDPR Compliance

**Add privacy notice to challenge page:**

Edit `/etc/ukabu/pages/challenge.html`:
```html
<!-- Add before closing </body> tag -->
<div class="privacy-notice" style="margin-top: 20px; padding: 10px; background: #f0f0f0; font-size: 12px;">
    <strong>Privacy Notice:</strong> We process your IP address for security purposes 
    to protect against automated abuse. This data is retained for 
    [YOUR_RETENTION_PERIOD] days. For more information, see our 
    <a href="https://yourdomain.com/privacy">Privacy Policy</a>.
</div>
```

**Document data retention:**

Create `/etc/ukabu/config/data-retention-policy.txt`:
```
UKABU WAF - Data Retention Policy

IP Addresses:
- Strike database: 30 days (automatic cleanup)
- nginx access logs: 30 days (logrotate)
- Blacklist (temporary): Per lockout_period (default 7 days)
- Blacklist (permanent): Until manually removed

Legal Basis (GDPR):
- Legitimate interest (security)
- Contract performance (service protection)

Data Subject Rights:
- Right to erasure: Contact admin@yourdomain.com
- Right to access: Contact admin@yourdomain.com
```

---

## Monitoring & Alerting Setup

### 1. Prometheus Setup

**Install Prometheus:**
```bash
# Ubuntu/Debian
sudo apt-get install prometheus

# Or download from prometheus.io
wget https://github.com/prometheus/prometheus/releases/download/v2.45.0/prometheus-2.45.0.linux-amd64.tar.gz
```

**Configure Prometheus (`/etc/prometheus/prometheus.yml`):**
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'ukabu-trackerd'
    static_configs:
      - targets: ['localhost:9090']
```

**Start Prometheus:**
```bash
sudo systemctl start prometheus
sudo systemctl enable prometheus
```

**Access metrics:**
```bash
# View metrics
curl http://localhost:9090/metrics

# Example queries
curl 'http://localhost:9090/api/v1/query?query=ukabu_strikes_total'
```

---

### 2. Log Monitoring

**Install logwatch:**
```bash
sudo apt-get install logwatch

# Configure for UKABU logs
sudo nano /etc/logwatch/conf/logfiles/ukabu.conf
```

**Content:**
```
LogFile = /var/log/ukabu/*.log
Archive = /var/log/ukabu/*.log.*.gz
```

**Set up daily reports:**
```bash
# Edit crontab
sudo crontab -e

# Add daily logwatch report
0 6 * * * /usr/sbin/logwatch --detail High --service all --range yesterday --mailto admin@yourdomain.com
```

---

### 3. Alert Setup (Optional)

**Install alertmanager:**
```bash
sudo apt-get install prometheus-alertmanager
```

**Configure alerts (`/etc/prometheus/alerts.yml`):**
```yaml
groups:
  - name: ukabu_alerts
    interval: 1m
    rules:
      - alert: HighBlockRate
        expr: rate(ukabu_blocks_total[5m]) > 100
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High block rate detected"
          description: "{{ $value }} blocks per second"
      
      - alert: IpsetCapacity
        expr: ukabu_ipset_entries > 9000
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "ipset approaching capacity"
          description: "{{ $value }} entries in ipset"
      
      - alert: DaemonDown
        expr: up{job="ukabu-trackerd"} == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "ukabu-trackerd is down"
```

---

## Backup & Recovery

### 1. Backup Script

**Create `/usr/local/bin/ukabu-backup.sh`:**
```bash
#!/bin/bash
# UKABU WAF Backup Script

BACKUP_DIR="/backup/ukabu"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/ukabu-backup-$DATE.tar.gz"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup configuration (excluding secrets)
tar -czf "$BACKUP_FILE" \
    /etc/ukabu/config/ \
    /etc/ukabu/includes/ \
    /etc/ukabu/njs/ \
    /etc/ukabu/pages/ \
    /var/lib/ukabu/strikes.db \
    /etc/nginx/sites-available/*ukabu* \
    --exclude="/etc/ukabu/secrets"

# Backup secrets separately (ENCRYPTED)
tar -czf "$BACKUP_DIR/ukabu-secrets-$DATE.tar.gz" \
    /etc/ukabu/secrets/

# Encrypt secrets backup
gpg --symmetric --cipher-algo AES256 "$BACKUP_DIR/ukabu-secrets-$DATE.tar.gz"
rm "$BACKUP_DIR/ukabu-secrets-$DATE.tar.gz"

# Remove backups older than 30 days
find "$BACKUP_DIR" -name "ukabu-backup-*.tar.gz" -mtime +30 -delete
find "$BACKUP_DIR" -name "ukabu-secrets-*.tar.gz.gpg" -mtime +30 -delete

echo "Backup complete: $BACKUP_FILE"
```

**Make executable and schedule:**
```bash
sudo chmod +x /usr/local/bin/ukabu-backup.sh

# Add to crontab (daily at 2 AM)
sudo crontab -e
0 2 * * * /usr/local/bin/ukabu-backup.sh
```

---

### 2. Recovery Procedure

**Restore from backup:**
```bash
# 1. Extract configuration
sudo tar -xzf /backup/ukabu/ukabu-backup-YYYYMMDD_HHMMSS.tar.gz -C /

# 2. Restore secrets (ENCRYPTED)
gpg --decrypt /backup/ukabu/ukabu-secrets-YYYYMMDD_HHMMSS.tar.gz.gpg | sudo tar -xz -C /

# 3. Fix permissions
sudo chmod 600 /etc/ukabu/secrets/*.key
sudo chown root:root /etc/ukabu/secrets/*.key

# 4. Reload services
sudo systemctl reload nginx
sudo systemctl restart ukabu-trackerd

# 5. Verify
sudo nginx -t
sudo systemctl status ukabu-trackerd
```

---

## Testing & Validation

### 1. Security Testing

**Test PoW challenge:**
```bash
# Should require PoW
curl -I https://yourdomain.com/
# Expected: HTTP/1.1 302, X-Ukabu-Status: 200

# Test with invalid token
curl -I -H "Cookie: pow_token=invalid:1234567890" https://yourdomain.com/
# Expected: HTTP/1.1 302 (re-challenge)
```

**Test IP whitelist:**
```bash
# Add your IP to whitelist
sudo ukabu-manager whitelist add YOUR_IP

# Test bypass
curl -I https://yourdomain.com/
# Expected: X-Ukabu-Status: 101
```

**Test blocking:**
```bash
# Trigger 3 failures from a test IP
# (Requires manual browser testing or automated script)

# Check if blocked
sudo ukabu-manager status --strikes
sudo ipset list ukabu-temporary_0
```

---

### 2. Load Testing

**Install Apache Bench:**
```bash
sudo apt-get install apache2-utils
```

**Run load test:**
```bash
# Test with 1000 requests, 10 concurrent
ab -n 1000 -c 10 https://yourdomain.com/static/test.css

# Monitor during test
watch -n 1 'sudo ipset list ukabu-temporary_0 | grep "Number of entries"'
```

**Expected Results:**
- Static assets (whitelisted paths): < 10ms response time
- PoW challenges: < 50ms challenge generation
- No service degradation under load

---

### 3. Penetration Testing

**Test attack vectors:**
```bash
# 1. Test SQL injection on paths
curl "https://yourdomain.com/index.php?id=1' OR '1'='1"
# Should be blocked by path_blacklist if configured

# 2. Test XSS attempts
curl "https://yourdomain.com/search?q=<script>alert(1)</script>"
# Should be blocked by path_blacklist if configured

# 3. Test brute force
for i in {1..10}; do
    curl -X POST https://yourdomain.com/login \
        -d "user=admin&pass=wrong$i"
done
# Should accumulate strikes and eventually block

# 4. Test header injection
curl -H "X-Forwarded-For: 1.2.3.4, 5.6.7.8" https://yourdomain.com/
# Should ignore XFF unless explicitly enabled
```

---

## Post-Deployment Maintenance

### Daily Tasks
- [ ] Review `/var/log/ukabu/blocks.log` for unusual patterns
- [ ] Check Prometheus dashboard for anomalies
- [ ] Verify all systemd services running

### Weekly Tasks
- [ ] Review strike database: `sudo ukabu-manager status --strikes`
- [ ] Check disk space: `df -h /var/log/ukabu`
- [ ] Review nginx error log: `sudo tail -100 /var/log/nginx/error.log`

### Monthly Tasks
- [ ] Review and cleanup old blocked IPs
- [ ] Audit whitelist and blacklist
- [ ] Update CDN proxy lists manually (if auto-update fails)
- [ ] Review log rotation settings
- [ ] Test backup restoration

### Quarterly Tasks
- [ ] Rotate HMAC secrets: `sudo ukabu-manager domain set-secret DOMAIN --rotate`
- [ ] Security audit (review configurations)
- [ ] Performance tuning (adjust difficulty based on traffic)
- [ ] Update nginx and dependencies

---

## Troubleshooting Guide

### Issue: nginx won't start

**Solution:**
```bash
# Check nginx config
sudo nginx -t

# Check logs
sudo tail -50 /var/log/nginx/error.log

# Common issues:
# - Missing NJS module: Install nginx-module-njs
# - Syntax error in config: Check line number in error
# - Permission issues: Check file ownership
```

---

### Issue: Daemon not blocking IPs

**Solution:**
```bash
# Check daemon status
sudo systemctl status ukabu-trackerd

# Check daemon logs
sudo journalctl -u ukabu-trackerd -n 100

# Test socket communication
echo '{"type":"test"}' | sudo nc -U /var/run/ukabu/tracker.sock

# Check ipsets
sudo ipset list | grep ukabu

# Common issues:
# - Socket permission denied: Check /var/run/ukabu permissions
# - ipset not found: Install ipset package
# - SQLite locked: Check /var/lib/ukabu permissions
```

---

### Issue: CDN IPs not updating

**Solution:**
```bash
# Check timer status
sudo systemctl status ukabu-update-proxies.timer

# Run update manually
sudo /usr/local/bin/ukabu-fetch-cdn-ips.sh

# Check logs
sudo journalctl -u ukabu-update-proxies.service

# Verify files updated
ls -la /etc/ukabu/config/trusted_proxies_*.conf
```

---

### Issue: High false positive rate

**Solution:**
```bash
# 1. Lower PoW difficulty
sudo ukabu-manager domain set yourdomain.com --difficulty 16

# 2. Increase cookie duration
sudo ukabu-manager domain set yourdomain.com --cookie-duration 1209600  # 14 days

# 3. Excuse first timeout
sudo ukabu-manager domain set yourdomain.com --excuse-first-timeout

# 4. Whitelist known good IPs
sudo ukabu-manager whitelist add 1.2.3.4

# 5. Review exempt paths (static assets)
sudo ukabu-manager paths list-exempt yourdomain.com
```

---

## Emergency Procedures

### 1. Disable UKABU (Emergency)

**If UKABU is causing issues:**
```bash
# Option 1: Comment out enforcement.inc in vhost
sudo nano /etc/nginx/sites-available/yourdomain.com.conf
# Comment line: include /etc/ukabu/includes/enforcement.inc;
sudo nginx -t && sudo systemctl reload nginx

# Option 2: Mark domain as not protected
sudo ukabu-manager domain set yourdomain.com --not-protected

# Option 3: Stop daemon (keeps nginx protection but no blocking)
sudo systemctl stop ukabu-trackerd
```

---

### 2. Clear All Blocks (Emergency)

**If legitimate users are blocked:**
```bash
# Flush all temporary blocks
sudo ipset flush ukabu-temporary_0
sudo ipset flush ukabu-temporary_1
# ... (for all temporary sets)

# Clear strike database
sudo rm /var/lib/ukabu/strikes.db
sudo systemctl restart ukabu-trackerd

# Clear blacklist file
echo "" | sudo tee /etc/ukabu/config/ip_blacklist.conf
```

---

### 3. Rollback to Previous Configuration

**If new config breaks something:**
```bash
# ukabu-manager creates automatic backups
ls -la /etc/ukabu/config/.backups/

# Restore previous config
sudo cp /etc/ukabu/config/.backups/domains.json.TIMESTAMP /etc/ukabu/config/domains.json

# Regenerate nginx config
sudo ukabu-manager nginx generate-config

# Test and reload
sudo nginx -t && sudo systemctl reload nginx
```

---

## Performance Tuning

### For High-Traffic Sites (10,000+ req/s)

**nginx worker optimization:**
```nginx
# /etc/nginx/nginx.conf

# Set to number of CPU cores
worker_processes auto;

# Max connections per worker
events {
    worker_connections 4096;
    use epoll;
}

# Disable access logging for static assets (reduce I/O)
location /static/ {
    access_log off;
    expires 30d;
}
```

**Increase ipset capacity:**
```bash
# Edit systemd unit
sudo nano /etc/systemd/system/ukabu-ipset-init.service

# Change maxelem parameter
ipset create ukabu-temporary_0 hash:net maxelem 50000
```

**Enable SQLite WAL mode:**
```go
// In tracker.go, after opening database
db.Exec("PRAGMA journal_mode=WAL")
db.Exec("PRAGMA synchronous=NORMAL")
```

---

## Success Criteria

### ✅ Deployment Successful When:

- [ ] nginx serves pages without errors
- [ ] PoW challenge works in browser (Chrome, Firefox, Safari, Edge)
- [ ] Valid tokens allow access to protected pages
- [ ] Whitelisted IPs bypass PoW
- [ ] Static assets bypass PoW
- [ ] Failed attempts increment strike counter
- [ ] 3+ strikes result in IP blocking via ipset
- [ ] Blocked IPs cannot access site (connection timeout)
- [ ] Automatic unjailing works after lockout expiry
- [ ] Daemon survives restarts (SQLite persistence)
- [ ] Logs are being written correctly
- [ ] Prometheus metrics are accessible
- [ ] systemd timers are running
- [ ] Backups are being created daily

---

## Support & Resources

**Official Documentation:**
- Main README: `/mnt/project/README.md`
- Component-specific guides: `/mnt/project/README-PHASE*.md`
- Examples: `/mnt/project/EXAMPLES.md`
- Testing: `/mnt/project/TESTING.md`

**Contact:**
- **L2C2 Technologies**
- Email: indradg@l2c2.co.in
- Licensing inquiries: indradg@l2c2.co.in

**Community:**
- Check project repository for updates
- Report issues via project issue tracker
- Contribute improvements via pull requests

---

**END OF DEPLOYMENT GUIDE**

**Document Version:** 1.0  
**Last Updated:** November 9, 2025  
**Classification:** Deployment Guide
