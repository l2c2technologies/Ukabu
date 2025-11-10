# UKABU WAF Component C (ukabu-manager) - Usage Examples

**Copyright (c) 2025 by L2C2 Technologies. All rights reserved.**

---

## Scenario 1: Multi-Site WordPress Hosting

**Setup**: Protecting 10 WordPress sites with varying security requirements

```bash
# High-traffic public blog (lower difficulty)
sudo ukabu-manager domain add blog.example.com -d 16 -l 5040

# E-commerce site (higher difficulty, longer lockout)
sudo ukabu-manager domain add shop.example.com -d 20 -l 20160

# Corporate site (excuse first timeout for bad connections)
sudo ukabu-manager domain add corporate.example.com -d 18 --excuse-first-timeout

# Generate all configs
sudo ukabu-manager nginx generate-config

# Whitelist office network
sudo ukabu-manager whitelist add 203.0.113.0/24

# Reload nginx
sudo ukabu-manager nginx reload
```

---

## Scenario 2: API Protection

**Setup**: Protecting REST API with IP-based access control

```bash
# Add API domain with high difficulty
sudo ukabu-manager domain add api.example.com -d 22 -l 10080

# Whitelist known API clients
sudo ukabu-manager whitelist add 198.51.100.0/24  # Client A
sudo ukabu-manager whitelist add 192.0.2.42       # Client B

# Block known bad actors
sudo ukabu-manager blacklist add 203.0.113.100 -r "API abuse"
sudo ukabu-manager blacklist add 198.18.0.0/15 -r "Known bot network"

# Generate and reload
sudo ukabu-manager nginx generate-config
sudo ukabu-manager nginx reload

# Monitor API usage
watch -n 5 'sudo ukabu-manager status --strikes'
```

---

## Scenario 3: Secret Rotation Schedule

**Setup**: Quarterly secret rotation for compliance

```bash
# Rotate secrets for all domains
for domain in $(sudo ukabu-manager domain list | grep 'â€¢' | awk '{print $2}'); do
    echo "Rotating secret for $domain..."
    sudo ukabu-manager domain set-secret $domain --rotate
done

# Regenerate configs
sudo ukabu-manager nginx generate-config

# Reload nginx
sudo ukabu-manager nginx reload

# Wait 12 hours for grace period to expire
# Then verify old secrets are cleaned up
sudo ls -la /etc/ukabu/secrets/*.previous.key
```

---

## Scenario 4: Incident Response

**Setup**: Responding to a scraping attack

```bash
# Check active strikes
sudo ukabu-manager status --verbose --strikes

# Block the offending IP immediately
sudo ukabu-manager blacklist add 198.51.100.123 -d 10080 -r "Scraping attack"

# Check current blocks
sudo ukabu-manager blacklist list

# Monitor for continued attacks
tail -f /var/log/ukabu/failed_attempts.log

# After investigation, unblock if false positive
sudo ukabu-manager unblock 198.51.100.123
```

---

## Scenario 5: Gradual Difficulty Increase

**Setup**: Starting with low difficulty and gradually increasing

```bash
# Week 1: Start with easy challenge
sudo ukabu-manager domain add new-site.com -d 14

# Week 2: Increase slightly
sudo ukabu-manager domain set new-site.com -d 16
sudo ukabu-manager nginx generate-config -d new-site.com
sudo ukabu-manager nginx reload

# Week 3: Standard difficulty
sudo ukabu-manager domain set new-site.com -d 18
sudo ukabu-manager nginx generate-config -d new-site.com
sudo ukabu-manager nginx reload

# Week 4: Higher security
sudo ukabu-manager domain set new-site.com -d 20
sudo ukabu-manager nginx generate-config -d new-site.com
sudo ukabu-manager nginx reload

# Monitor impact on legitimate users
sudo ukabu-manager status --verbose
```

---

## Scenario 6: Development vs Production

**Setup**: Different settings for dev and prod domains

```bash
# Development (low difficulty, short lockout)
sudo ukabu-manager domain add dev.example.com -d 12 -l 60 --excuse-first-timeout

# Staging (medium difficulty)
sudo ukabu-manager domain add staging.example.com -d 16 -l 1440

# Production (high difficulty, long lockout)
sudo ukabu-manager domain add www.example.com -d 22 -l 20160

# Whitelist internal network on all
sudo ukabu-manager whitelist add 10.0.0.0/8

# Generate configs
sudo ukabu-manager nginx generate-config

# Reload
sudo ukabu-manager nginx reload
```

---

## Scenario 7: Automated Monitoring Script

**Setup**: Bash script for daily monitoring

```bash
#!/bin/bash
# /usr/local/bin/ukabu-daily-check.sh

echo "UKABU Daily Status Report - $(date)"
echo "=========================================="

# Get JSON status
STATUS=$(sudo ukabu-manager status --json --strikes)

# Check daemon health
DAEMON_STATUS=$(echo $STATUS | jq -r '.daemon.responsive')
if [ "$DAEMON_STATUS" != "true" ]; then
    echo "âŒ ALERT: Daemon not responsive!"
    systemctl status ukabu-trackerd
else
    echo "âœ… Daemon healthy"
    UPTIME=$(echo $STATUS | jq -r '.daemon.uptime')
    echo "   Uptime: $((UPTIME / 3600)) hours"
fi

# Count blocks
BLOCKS=$(echo $STATUS | jq -r '.daemon.active_blocks')
echo "ðŸ“Š Active blocks: $BLOCKS"

# Show strikes
STRIKES=$(echo $STATUS | jq -r '.strikes | length')
if [ "$STRIKES" -gt 0 ]; then
    echo "âš ï¸  IPs with strikes: $STRIKES"
    echo $STATUS | jq -r '.strikes'
fi

# List recent blocks
echo ""
echo "Recent blacklist additions:"
sudo ukabu-manager blacklist list | head -10

# Email if needed
if [ "$DAEMON_STATUS" != "true" ] || [ "$BLOCKS" -gt 100 ]; then
    echo "$STATUS" | mail -s "UKABU WAF Alert" admin@example.com
fi
```

**Cron job** (`crontab -e`):
```
0 8 * * * /usr/local/bin/ukabu-daily-check.sh >> /var/log/ukabu/daily-report.log
```

---

## Scenario 8: Bulk Import from CSV

**Setup**: Import whitelist from CSV file

```bash
# CSV format: ip_address,description
# 192.168.1.0/24,Office Network
# 10.0.0.0/8,Internal Network

#!/bin/bash
# import-whitelist.sh

while IFS=',' read -r ip desc; do
    echo "Adding $ip ($desc)..."
    sudo ukabu-manager whitelist add "$ip"
done < whitelist.csv

# Reload nginx
sudo ukabu-manager nginx reload

echo "Import complete!"
```

---

## Scenario 9: Dry-run Testing

**Setup**: Testing configuration changes before applying

```bash
# Test adding domain without making changes
sudo ukabu-manager --dry-run domain add test.com -d 20

# Test bulk whitelist addition
for ip in 192.168.{1..10}.0/24; do
    sudo ukabu-manager --dry-run whitelist add $ip
done

# Test secret rotation
sudo ukabu-manager --dry-run domain set-secret example.com --rotate

# Review audit log to see what would happen
tail -20 /var/log/ukabu/manager.log

# If satisfied, run without --dry-run
sudo ukabu-manager domain add test.com -d 20
```

---

## Scenario 10: Multi-Environment Management

**Setup**: Ansible playbook for managing UKABU across environments

```yaml
---
# ukabu-setup.yml

- hosts: web_servers
  become: yes
  vars:
    ukabu_domains:
      - name: "{{ inventory_hostname }}"
        difficulty: 18
        lockout: 10080
        excuse_first_timeout: true
    
    office_networks:
      - 203.0.113.0/24
      - 198.51.100.0/24
  
  tasks:
    - name: Add domain to UKABU
      command: >
        ukabu-manager domain add {{ item.name }}
        -d {{ item.difficulty }}
        -l {{ item.lockout }}
        {% if item.excuse_first_timeout %}--excuse-first-timeout{% endif %}
      loop: "{{ ukabu_domains }}"
      register: result
      failed_when: result.rc not in [0, 1]
      changed_when: result.rc == 0
    
    - name: Whitelist office networks
      command: ukabu-manager whitelist add {{ item }}
      loop: "{{ office_networks }}"
      register: result
      failed_when: result.rc not in [0, 1]
      changed_when: result.rc == 0
    
    - name: Generate nginx configuration
      command: ukabu-manager nginx generate-config
      when: result.changed
    
    - name: Reload nginx
      command: ukabu-manager nginx reload
      when: result.changed
    
    - name: Check UKABU status
      command: ukabu-manager status --json
      register: status
      changed_when: false
    
    - name: Display status
      debug:
        var: status.stdout | from_json
```

**Run playbook**:
```bash
ansible-playbook -i inventory ukabu-setup.yml
```

---

## Scenario 11: Backup and Restore

**Setup**: Backing up and restoring UKABU configuration

```bash
#!/bin/bash
# /usr/local/bin/ukabu-backup.sh

BACKUP_DIR="/backup/ukabu/$(date +%Y%m%d-%H%M%S)"
mkdir -p $BACKUP_DIR

echo "Backing up UKABU configuration..."

# Backup configuration files
cp -r /etc/ukabu/config/* $BACKUP_DIR/
cp -r /etc/ukabu/secrets $BACKUP_DIR/
cp -r /etc/ukabu/includes/domains $BACKUP_DIR/

# Backup database
cp /var/lib/ukabu/strikes.db $BACKUP_DIR/

# Export status
sudo ukabu-manager status --json > $BACKUP_DIR/status.json
sudo ukabu-manager domain list > $BACKUP_DIR/domains.txt
sudo ukabu-manager whitelist list > $BACKUP_DIR/whitelist.txt
sudo ukabu-manager blacklist list > $BACKUP_DIR/blacklist.txt

# Create tarball
tar -czf /backup/ukabu-$(date +%Y%m%d-%H%M%S).tar.gz -C $BACKUP_DIR .

echo "Backup complete: $BACKUP_DIR"
```

**Restore**:
```bash
#!/bin/bash
# /usr/local/bin/ukabu-restore.sh

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup-file.tar.gz>"
    exit 1
fi

RESTORE_DIR="/tmp/ukabu-restore-$$"
mkdir -p $RESTORE_DIR

# Extract backup
tar -xzf $BACKUP_FILE -C $RESTORE_DIR

# Restore files
cp -r $RESTORE_DIR/config/* /etc/ukabu/config/
cp -r $RESTORE_DIR/secrets /etc/ukabu/
cp -r $RESTORE_DIR/domains /etc/ukabu/includes/

# Restore database
cp $RESTORE_DIR/strikes.db /var/lib/ukabu/

# Restart services
systemctl restart ukabu-trackerd
sudo ukabu-manager nginx reload

echo "Restore complete!"
```

---

## Scenario 12: Performance Tuning

**Setup**: Optimizing for high-traffic site

```bash
# Start with baseline
sudo ukabu-manager domain add hightraffic.example.com -d 16

# Monitor performance
ab -n 10000 -c 100 https://hightraffic.example.com/

# Adjust based on results
# If too many failures, reduce difficulty
sudo ukabu-manager domain set hightraffic.example.com -d 14

# If too easy, increase difficulty
sudo ukabu-manager domain set hightraffic.example.com -d 18

# Enable first timeout excuse for slow connections
sudo ukabu-manager domain set hightraffic.example.com --excuse-first-timeout

# Regenerate and reload
sudo ukabu-manager nginx generate-config -d hightraffic.example.com
sudo ukabu-manager nginx reload

# Monitor strikes
sudo ukabu-manager status --verbose --strikes
```

---

For more examples and documentation, see:
- [README-PHASE3.md](README-PHASE3.md)
- [QUICKSTART.md](QUICKSTART.md)
- [CHANGELOG-PHASE3.md](CHANGELOG-PHASE3.md)

---

**Copyright (c) 2025 by L2C2 Technologies. All rights reserved.**

For licensing inquiries: Indranil Das Gupta <indradg@l2c2.co.in>
