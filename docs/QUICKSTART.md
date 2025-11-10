# UKABU WAF Component C (ukabu-manager) - Quick Start Guide

**Copyright (c) 2025 by L2C2 Technologies. All rights reserved.**

---

## 5-Minute Setup

### 1. Install Component C (ukabu-manager)

```bash
tar -xzf ukabu-component3.tar.gz
cd ukabu-component3
sudo bash install-component3.sh
```

### 2. Add Your First Domain

```bash
sudo ukabu-manager domain add example.com
```

### 3. Add Trusted IPs (Optional)

```bash
sudo ukabu-manager whitelist add 192.168.1.0/24
sudo ukabu-manager whitelist add 10.0.0.0/8
```

### 4. Generate nginx Config

```bash
sudo ukabu-manager nginx generate-config
```

### 5. Update Your vhost

Edit `/etc/nginx/sites-available/example.com`:

```nginx
server {
    listen 443 ssl http2;
    server_name example.com;
    
    # SSL configuration
    ssl_certificate /etc/ssl/certs/example.com.crt;
    ssl_certificate_key /etc/ssl/private/example.com.key;
    
    # Add these UKABU includes
    include /etc/ukabu/includes/config.conf;
    include /etc/ukabu/includes/domains/example.com.conf;
    include /etc/ukabu/includes/endpoints.inc;
    include /etc/ukabu/includes/enforcement.inc;
    
    # Your existing location blocks
    location / {
        proxy_pass http://localhost:8080;
        # ...
    }
}
```

### 6. Reload nginx

```bash
sudo ukabu-manager nginx test
sudo ukabu-manager nginx reload
```

### 7. Check Status

```bash
sudo ukabu-manager status
```

---

## Common Tasks

### Add a New Domain

```bash
sudo ukabu-manager domain add new-site.com -d 20
sudo ukabu-manager nginx generate-config -d new-site.com
# Update vhost to include UKABU configs
sudo ukabu-manager nginx reload
```

### Increase Security

```bash
# Higher difficulty (more computation required)
sudo ukabu-manager domain set example.com -d 22

# Longer lockout period (14 days)
sudo ukabu-manager domain set example.com -l 20160

sudo ukabu-manager nginx generate-config -d example.com
sudo ukabu-manager nginx reload
```

### Whitelist Your Office

```bash
sudo ukabu-manager whitelist add 203.0.113.0/24
sudo ukabu-manager nginx reload
```

### Block Malicious IP

```bash
# Permanent block
sudo ukabu-manager blacklist add 198.51.100.42 -r "Scraper bot"

# Temporary block (24 hours)
sudo ukabu-manager blacklist add 192.0.2.100 -d 1440 -r "Suspicious activity"
```

### Unblock an IP

```bash
sudo ukabu-manager unblock 198.51.100.42
```

### Rotate Secret

```bash
sudo ukabu-manager domain set-secret example.com --rotate
sudo ukabu-manager nginx reload
```

### Check Active Blocks

```bash
sudo ukabu-manager status --verbose --strikes
```

---

## Troubleshooting

### "Command not found"

```bash
# Check installation
which ukabu-manager

# Reinstall if needed
cd ukabu-component3
sudo bash install-component3.sh
```

### "nginx reload failed"

```bash
# Test config first
sudo ukabu-manager nginx test

# Check error log
sudo tail -f /var/log/nginx/error.log
```

### "Daemon not responsive"

```bash
# Check daemon status
systemctl status ukabu-trackerd

# Restart if needed
sudo systemctl restart ukabu-trackerd
```

---

## Next Steps

- Read the full [README-PHASE3.md](README-PHASE3.md)
- Review [CHANGELOG-PHASE3.md](CHANGELOG-PHASE3.md)
- Check daemon logs: `tail -f /var/log/ukabu/trackerd.log`
- Monitor audit log: `tail -f /var/log/ukabu/manager.log`

---

**Need Help?**

Contact: Indranil Das Gupta <indradg@l2c2.co.in>
