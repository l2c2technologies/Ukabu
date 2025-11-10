# UKABU WAF - Component C (ukabu-manager): Management CLI

**Copyright (c) 2025 by L2C2 Technologies. All rights reserved.**

For licensing inquiries: Indranil Das Gupta <indradg@l2c2.co.in>

---

## Overview

Component C (ukabu-manager) delivers a comprehensive Python-based CLI tool (`ukabu-manager`) for managing all aspects of the UKABU WAF system. This tool provides idempotent operations, dry-run mode, audit logging, and seamless integration with the Component B (ukabu-monitor) daemon.

### Key Features

âœ… **Domain Management** - Add, remove, configure protected domains  
âœ… **IP Lists** - Manage whitelist and blacklist  
âœ… **nginx Integration** - Generate and reload configurations  
âœ… **Daemon Communication** - Unix socket interface to ukabu-trackerd  
âœ… **Secret Rotation** - HMAC secret management with 12-hour grace period  
âœ… **Idempotent Operations** - Safe to run multiple times  
âœ… **Dry-run Mode** - Preview changes before applying  
âœ… **Audit Logging** - All operations logged to `/var/log/ukabu/manager.log`  

---

## Installation

### Prerequisites

- Component A (ukabu-core) and Component B (ukabu-monitor) must be installed
- Python 3.10+ 
- pip3
- Root privileges

### Install Component C (ukabu-manager)

```bash
# Extract tarball
tar -xzf ukabu-component3.tar.gz
cd ukabu-component3

# Run installation script
sudo bash install-component3.sh
```

The installer will:
1. Check dependencies (Python 3.10+, pip3)
2. Install Python packages (click, jinja2)
3. Install UKABU library to `/usr/local/lib/ukabu`
4. Install CLI tool to `/usr/local/bin/ukabu-manager`
5. Create required directories
6. Initialize configuration files
7. Set up logrotate

---

## Architecture

### File Structure

```
/usr/local/bin/
  â””â”€â”€ ukabu-manager                 # Main CLI entry point

/usr/local/lib/ukabu/
  â”œâ”€â”€ __init__.py                   # Package initialization
  â”œâ”€â”€ utils.py                      # Common utilities
  â”œâ”€â”€ domain.py                     # Domain management
  â”œâ”€â”€ ipmanager.py                  # IP whitelist/blacklist
  â”œâ”€â”€ nginx.py                      # nginx config generation
  â””â”€â”€ daemon.py                     # Unix socket client

/etc/ukabu/
  â”œâ”€â”€ config/
  â”‚   â”œâ”€â”€ domains.json              # Domain configuration
  â”‚   â”œâ”€â”€ ip_whitelist.conf         # IP whitelist (line-based)
  â”‚   â”œâ”€â”€ ip_blacklist.conf         # IP blacklist (JSONL)
  â”‚   â”œâ”€â”€ path_whitelist.conf       # Global path exemptions
  â”‚   â””â”€â”€ path_blacklist.conf       # Global path blocks
  â”œâ”€â”€ secrets/
  â”‚   â”œâ”€â”€ example.com.current.key   # Current HMAC secret
  â”‚   â””â”€â”€ example.com.previous.key  # Previous secret (rotation)
  â””â”€â”€ includes/
      â””â”€â”€ domains/
          â””â”€â”€ example.com.conf      # Generated nginx config

/var/log/ukabu/
  â”œâ”€â”€ manager.log                   # Audit log (all operations)
  â”œâ”€â”€ trackerd.log                  # Daemon log
  â””â”€â”€ failed_attempts.log           # Strike tracking

/var/lib/ukabu/
  â””â”€â”€ strikes.db                    # SQLite database
```

---

## Command Reference

### Global Options

```bash
ukabu-manager [OPTIONS] COMMAND

Options:
  -v, --verbose     Enable verbose logging
  --dry-run         Show what would be done without making changes
  --help            Show help message
```

### Domain Management

#### Add Domain

```bash
sudo ukabu-manager domain add <DOMAIN> [OPTIONS]

Options:
  -d, --difficulty INT         PoW difficulty in bits (default: 18)
  -l, --lockout INT            Lockout period in minutes (default: 10080)
  -c, --cookie-duration INT    Cookie validity in seconds (default: 604800)
  --excuse-first-timeout       Excuse first timeout failure
  --secret TEXT                Manual HMAC secret (auto-generated if not provided)

Examples:
  # Basic domain with defaults
  sudo ukabu-manager domain add example.com

  # High-security domain
  sudo ukabu-manager domain add secure.example.com -d 22 -l 20160 --excuse-first-timeout

  # Custom secret
  sudo ukabu-manager domain add api.example.com --secret "your-64-byte-hex-secret"
```

**Idempotency**: Running `domain add` for an existing domain does nothing (exit code 0).

#### Remove Domain

```bash
sudo ukabu-manager domain remove <DOMAIN> [OPTIONS]

Options:
  -f, --force      Skip confirmation prompt

Examples:
  # Interactive removal (prompts for confirmation)
  sudo ukabu-manager domain remove example.com

  # Force removal without prompt
  sudo ukabu-manager domain remove example.com --force
```

**Safety**: Backs up nginx config and secret files before removal.

#### List Domains

```bash
sudo ukabu-manager domain list

Output:
  Protected domains (2):
    â€¢ example.com
    â€¢ api.example.com
```

#### Show Domain Details

```bash
sudo ukabu-manager domain show <DOMAIN>

Example:
  sudo ukabu-manager domain show example.com

Output:
  Domain: example.com
  â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  PoW Difficulty:       20 bits
  Cookie Duration:      604800 seconds
  Lockout Period:       10080 minutes
  Excuse First Timeout: False
  Secret File:          /etc/ukabu/secrets/example.com.current.key
  Created:              2025-11-09T12:00:00Z
  Updated:              2025-11-09T14:30:00Z

  Exempt Paths (2):
    â€¢ /health
    â€¢ /static/*

  Restricted Paths (1):
    â€¢ /admin/*
        10.0.0.0/8
        192.168.1.100
```

#### Update Domain Settings

```bash
sudo ukabu-manager domain set <DOMAIN> [OPTIONS]

Options:
  -d, --difficulty INT         New PoW difficulty
  -l, --lockout INT            New lockout period
  -c, --cookie-duration INT    New cookie duration
  --excuse-first-timeout       Enable first timeout excuse
  --no-excuse-first-timeout    Disable first timeout excuse

Examples:
  # Increase difficulty
  sudo ukabu-manager domain set example.com -d 20

  # Enable first timeout excuse
  sudo ukabu-manager domain set example.com --excuse-first-timeout

  # Multiple settings
  sudo ukabu-manager domain set example.com -d 22 -l 20160
```

**Effect**: Regenerates nginx config and notifies daemon to reload configuration.

#### Set/Rotate Secret

```bash
sudo ukabu-manager domain set-secret <DOMAIN> [OPTIONS]

Options:
  --rotate          Rotate secret (keep old one valid for 12 hours)
  --manual TEXT     Use manual secret instead of auto-generating

Examples:
  # Rotate secret with auto-generated new secret
  sudo ukabu-manager domain set-secret example.com --rotate

  # Set manual secret (direct replacement)
  sudo ukabu-manager domain set-secret example.com --manual "your-new-secret"
```

**Secret Rotation**: When using `--rotate`, the current secret becomes `previous` and remains valid for 12 hours, preventing token invalidation. After 12 hours, the previous secret is automatically cleaned up.

---

### IP Whitelist Management

#### Add to Whitelist

```bash
sudo ukabu-manager whitelist add <IP_ADDRESS>

Examples:
  # Single IP
  sudo ukabu-manager whitelist add 192.168.1.100

  # CIDR range
  sudo ukabu-manager whitelist add 10.0.0.0/8
```

**Idempotency**: Adding an already-whitelisted IP does nothing (exit code 0).

#### Remove from Whitelist

```bash
sudo ukabu-manager whitelist remove <IP_ADDRESS>

Example:
  sudo ukabu-manager whitelist remove 192.168.1.100
```

#### List Whitelist

```bash
sudo ukabu-manager whitelist list

Output:
  Whitelisted IPs (3):
    â€¢ 192.168.1.100
    â€¢ 10.0.0.0/8
    â€¢ 172.16.0.0/12
```

---

### IP Blacklist Management

#### Add to Blacklist

```bash
sudo ukabu-manager blacklist add <IP_ADDRESS> [OPTIONS]

Options:
  -d, --duration INT    Lockout duration in minutes (0 for permanent)
  -r, --reason TEXT     Reason for blacklisting

Examples:
  # Permanent block
  sudo ukabu-manager blacklist add 1.2.3.4

  # Temporary block (7 days)
  sudo ukabu-manager blacklist add 5.6.7.8 -d 10080 -r "Aggressive scraping"

  # Temporary block (1 hour)
  sudo ukabu-manager blacklist add 9.10.11.12 -d 60 -r "Failed PoW attempts"
```

**Effect**: Adds to blacklist file AND notifies daemon to add to ipset immediately.

#### Remove from Blacklist

```bash
sudo ukabu-manager blacklist remove <IP_ADDRESS>

Example:
  sudo ukabu-manager blacklist remove 1.2.3.4
```

**Effect**: Removes from blacklist file AND notifies daemon to remove from ipset.

#### List Blacklist

```bash
sudo ukabu-manager blacklist list

Output:
  Blacklisted IPs (2):
    â€¢ 1.2.3.4 (PERMANENT)
        Reason: Malicious bot
        Added: 2025-11-09T10:00:00Z
    â€¢ 5.6.7.8 (10080 min)
        Reason: Aggressive scraping
        Added: 2025-11-09T12:30:00Z
```

---

### nginx Configuration Management

#### Generate Configuration

```bash
sudo ukabu-manager nginx generate-config [OPTIONS]

Options:
  -d, --domain TEXT    Generate for specific domain (all if not specified)

Examples:
  # Generate for all domains
  sudo ukabu-manager nginx generate-config

  # Generate for specific domain
  sudo ukabu-manager nginx generate-config -d example.com
```

**Output**: Creates `/etc/ukabu/includes/domains/<domain>.conf` for each domain.

**Backup**: Automatically backs up existing config files before overwriting.

#### Test Configuration

```bash
sudo ukabu-manager nginx test

Output:
  âœ“ nginx configuration is valid
```

**Effect**: Runs `nginx -t` to validate configuration syntax.

#### Reload nginx

```bash
sudo ukabu-manager nginx reload [OPTIONS]

Options:
  -f, --force      Skip configuration test

Examples:
  # Safe reload (tests config first)
  sudo ukabu-manager nginx reload

  # Force reload (skip test)
  sudo ukabu-manager nginx reload --force
```

**Safety**: Tests configuration before reloading unless `--force` is used.

---

### Unblock IP

```bash
sudo ukabu-manager unblock <IP_ADDRESS>

Example:
  sudo ukabu-manager unblock 1.2.3.4
```

**Effect**: 
1. Flushes strike count via daemon
2. Removes from blacklist file
3. Removes from ipset (if present)

---

### System Status

```bash
sudo ukabu-manager status [OPTIONS]

Options:
  -v, --verbose    Show detailed status
  --json           Output as JSON
  --strikes        Include strike counts

Examples:
  # Basic status
  sudo ukabu-manager status

  # Detailed status with strikes
  sudo ukabu-manager status --verbose --strikes

  # JSON output for automation
  sudo ukabu-manager status --json
```

**Sample Output**:

```
UKABU WAF Status
â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

ðŸ”§ Daemon Status
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
âœ“ Status: Running
  Uptime: 24.5 hours
  Memory: 45.2 MB
  Total strikes: 142
  Active blocks: 8

ðŸ“‹ Protected Domains
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  Count: 3
  â€¢ example.com
  â€¢ api.example.com
  â€¢ secure.example.com

ðŸ›¡ï¸  IP Lists
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  Whitelist: 5 IPs
  Blacklist: 8 IPs

âš ï¸  Active Strikes
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  â€¢ 1.2.3.4: 2 strike(s)
  â€¢ 5.6.7.8: 1 strike(s)
```

---

## Workflows

### Initial Setup

```bash
# 1. Add your first domain
sudo ukabu-manager domain add example.com -d 18 -l 10080

# 2. Add trusted IPs to whitelist
sudo ukabu-manager whitelist add 192.168.1.0/24
sudo ukabu-manager whitelist add 10.0.0.0/8

# 3. Generate nginx configuration
sudo ukabu-manager nginx generate-config

# 4. Include UKABU in your vhost config
# Edit /etc/nginx/sites-available/example.com and add:
#   include /etc/ukabu/includes/domains/example.com.conf;

# 5. Test and reload nginx
sudo ukabu-manager nginx test
sudo ukabu-manager nginx reload

# 6. Check status
sudo ukabu-manager status --verbose
```

### Adding a New Domain

```bash
# 1. Add domain with custom settings
sudo ukabu-manager domain add new-site.com -d 20 --excuse-first-timeout

# 2. Generate nginx config
sudo ukabu-manager nginx generate-config -d new-site.com

# 3. Include in vhost
# Add to /etc/nginx/sites-available/new-site.com:
#   include /etc/ukabu/includes/domains/new-site.com.conf;

# 4. Reload nginx
sudo ukabu-manager nginx reload
```

### Secret Rotation

```bash
# Rotate secret for domain (12-hour grace period)
sudo ukabu-manager domain set-secret example.com --rotate

# Reload nginx to use new secret
sudo ukabu-manager nginx reload

# Wait 12+ hours for automatic cleanup of old secret
# Or manually verify cleanup:
ls -la /etc/ukabu/secrets/example.com.*.key
```

### Unblocking an IP

```bash
# Check current status
sudo ukabu-manager status --strikes

# Unblock IP (flushes strikes and removes from ipset)
sudo ukabu-manager unblock 1.2.3.4

# Verify
sudo ukabu-manager status --strikes
```

### Dry-run Mode

```bash
# Preview what would happen without making changes
sudo ukabu-manager --dry-run domain add test.com
sudo ukabu-manager --dry-run whitelist add 1.2.3.4
sudo ukabu-manager --dry-run nginx generate-config
```

---

## Idempotency

All `ukabu-manager` commands are **idempotent** - safe to run multiple times:

| Command | Behavior on Re-run |
|---------|-------------------|
| `domain add` | No-op if domain exists (exit 0) |
| `whitelist add` | No-op if IP already whitelisted (exit 0) |
| `blacklist add` | No-op if IP already blacklisted (exit 0) |
| `domain set` | Updates only changed values |
| `nginx generate-config` | Overwrites config (with backup) |
| `unblock` | Safe even if IP not blocked |

**Exit codes**:
- `0` = Success (including no-op idempotent operations)
- `1` = User error (invalid input, missing args)
- `2` = System error (file permissions, daemon unreachable)

---

## Daemon Communication

`ukabu-manager` communicates with `ukabu-trackerd` via Unix socket (`/var/run/ukabu-trackerd.sock`) for:

- **Config reload**: Notify daemon of configuration changes
- **Strike queries**: Get current strike counts for IPs
- **Block management**: Add/remove IPs from ipset
- **Health checks**: Monitor daemon uptime, memory, responsiveness

**Protocol**: JSON over Unix socket

**Example exchange**:
```json
Request:  {"action": "strikes", "ip": "1.2.3.4"}
Response: {"status": "ok", "data": {"1.2.3.4": 2}}
```

---

## Error Handling & Rollback

### Configuration Validation

Before applying changes, `ukabu-manager` validates:
1. Domain name format
2. IP address/CIDR syntax
3. nginx configuration syntax
4. File permissions

### Rollback on Failure

If `nginx reload` fails:
1. Previous config is still active (no downtime)
2. Backup files available in `.bak` files
3. Error message shows what failed

**Manual rollback**:
```bash
# Restore from backup
sudo cp /etc/ukabu/includes/domains/example.com.conf.bak \
        /etc/ukabu/includes/domains/example.com.conf

# Test and reload
sudo ukabu-manager nginx test
sudo ukabu-manager nginx reload
```

---

## Audit Logging

All operations are logged to `/var/log/ukabu/manager.log`:

```
2025-11-09 12:00:15 [INFO] Added domain: example.com
2025-11-09 12:00:16 [INFO] Saved configuration to /etc/ukabu/config/domains.json
2025-11-09 12:00:16 [INFO] Saved current secret for example.com
2025-11-09 12:00:17 [INFO] Saved nginx config for example.com to /etc/ukabu/includes/domains/example.com.conf
2025-11-09 12:05:42 [INFO] Added 192.168.1.100 to whitelist
2025-11-09 12:10:33 [INFO] Rotated secret for domain: example.com
2025-11-09 12:10:33 [INFO] Old secret will remain valid for 12 hours
```

**Logrotate**: Configured to rotate daily, keep 30 days.

---

## Troubleshooting

### Command Not Found

```bash
# Check if installed
which ukabu-manager

# If not found, ensure PATH includes /usr/local/bin
export PATH=/usr/local/bin:$PATH

# Or reinstall
cd ukabu-component3
sudo bash install-component3.sh
```

### Permission Denied

```bash
# Most commands require root
sudo ukabu-manager domain add example.com

# Or use sudo for audit logging
sudo -E ukabu-manager status
```

### Daemon Not Responsive

```bash
# Check if daemon is running
systemctl status ukabu-trackerd

# Restart daemon
sudo systemctl restart ukabu-trackerd

# Check socket
ls -la /var/run/ukabu-trackerd.sock
```

### nginx Reload Fails

```bash
# Test configuration
sudo ukabu-manager nginx test

# Check nginx error log
sudo tail -f /var/log/nginx/error.log

# Validate UKABU includes exist
ls -la /etc/ukabu/includes/
```

### Invalid Configuration

```bash
# Validate domains.json syntax
sudo python3 -m json.tool /etc/ukabu/config/domains.json

# Check secret files
sudo ls -la /etc/ukabu/secrets/

# Regenerate configs
sudo ukabu-manager nginx generate-config
```

---

## Security Considerations

### Secret Files

- Stored in `/etc/ukabu/secrets/` with **0600** permissions (root only)
- **64-byte** cryptographically secure random secrets
- **Rotation**: Previous secret valid for 12 hours during rotation
- **Backup**: Excluded from standard backups (sensitive data)

### Audit Logging

- All operations logged with timestamp, user, action
- Log file at `/var/log/ukabu/manager.log` (root readable)
- Logrotate prevents unbounded growth
- Review logs regularly for unauthorized changes

### Daemon Socket

- Unix socket at `/var/run/ukabu-trackerd.sock`
- Only root can connect
- JSON protocol (not web-accessible)

---

## Integration with Existing Systems

### Configuration Management (Ansible/Puppet)

```yaml
# Ansible example
- name: Add domain to UKABU
  command: ukabu-manager domain add {{ domain_name }}
  register: result
  failed_when: result.rc not in [0, 1]  # 0=success, 1=already exists

- name: Generate nginx config
  command: ukabu-manager nginx generate-config -d {{ domain_name }}
  when: result.changed

- name: Reload nginx
  command: ukabu-manager nginx reload
  when: result.changed
```

### Monitoring Integration

```bash
# Export status as JSON for monitoring
ukabu-manager status --json > /var/www/html/ukabu-status.json

# Check daemon health in Nagios/Zabbix
STATUS=$(ukabu-manager status --json | jq -r '.daemon.responsive')
if [ "$STATUS" != "true" ]; then
    echo "CRITICAL: UKABU daemon not responsive"
    exit 2
fi
```

---

## Next Phase

**Component D (ukabu-extras)** will add:
- X-Forwarded-For handling
- CDN proxy auto-updater
- Search engine detection
- ML log extraction tools
- Path management commands
- Advanced analytics

---

## License

**Copyright (c) 2025 by L2C2 Technologies. All rights reserved.**

For licensing inquiries:  
Indranil Das Gupta <indradg@l2c2.co.in>  
L2C2 Technologies
