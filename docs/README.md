# UKABU WAF - Component C (ukabu-manager): Management CLI

**Copyright (c) 2025 by L2C2 Technologies. All rights reserved.**

For licensing inquiries: **Indranil Das Gupta** <indradg@l2c2.co.in>

---

## What is Component C (ukabu-manager)?

Component C (ukabu-manager) provides a comprehensive **Python-based CLI tool** (`ukabu-manager`) for managing the UKABU WAF system. It builds on Component A: ukabu-core (nginx PoW flow) and Component B (ukabu-monitor) (strike tracking daemon) to deliver a complete management solution.

### Key Features

âœ… **Domain Management** - Add, remove, and configure protected domains  
âœ… **IP List Management** - Whitelist and blacklist with full CRUD operations  
âœ… **nginx Integration** - Generate configurations and reload safely  
âœ… **Daemon Communication** - Real-time queries and commands via Unix socket  
âœ… **Secret Rotation** - HMAC secret management with 12-hour grace period  
âœ… **Idempotent Operations** - Safe to run multiple times  
âœ… **Dry-run Mode** - Preview changes before applying  
âœ… **Audit Logging** - Track all operations  

---

## Quick Start

```bash
# 1. Install Component C (ukabu-manager)
sudo bash install-component3.sh

# 2. Add your domain
sudo ukabu-manager domain add example.com

# 3. Generate nginx config
sudo ukabu-manager nginx generate-config

# 4. Reload nginx
sudo ukabu-manager nginx reload

# 5. Check status
sudo ukabu-manager status
```

---

## What's Included

### CLI Tool
- **ukabu-manager** - Main command-line interface with 20+ commands

### Python Library
- **domain.py** - Domain CRUD operations
- **ipmanager.py** - IP whitelist/blacklist management
- **nginx.py** - Configuration generation and testing
- **daemon.py** - Unix socket communication
- **utils.py** - Common utilities

### Documentation
- **[README-PHASE3.md](docs/README-PHASE3.md)** - Complete guide (70+ pages)
- **[QUICKSTART.md](docs/QUICKSTART.md)** - 5-minute setup
- **[EXAMPLES.md](docs/EXAMPLES.md)** - 12 practical scenarios
- **[CHANGELOG-PHASE3.md](docs/CHANGELOG-PHASE3.md)** - Version history

### Installation
- **install-component3.sh** - Automated installer
- **requirements.txt** - Python dependencies

---

## Command Categories

### Domain Management
```bash
ukabu-manager domain add <domain>
ukabu-manager domain remove <domain>
ukabu-manager domain list
ukabu-manager domain show <domain>
ukabu-manager domain set <domain> [OPTIONS]
ukabu-manager domain set-secret <domain> --rotate
```

### IP Management
```bash
ukabu-manager whitelist add <ip>
ukabu-manager whitelist remove <ip>
ukabu-manager whitelist list

ukabu-manager blacklist add <ip> [--duration N]
ukabu-manager blacklist remove <ip>
ukabu-manager blacklist list
```

### nginx Management
```bash
ukabu-manager nginx generate-config
ukabu-manager nginx test
ukabu-manager nginx reload
```

### System
```bash
ukabu-manager unblock <ip>
ukabu-manager status [--verbose] [--json] [--strikes]
```

---

## Requirements

- **Component A (ukabu-core) & 2**: Must be installed first
- **Python**: 3.10 or newer
- **pip3**: For installing dependencies
- **Root**: Required for most operations
- **nginx**: With NJS module

---

## Architecture

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                     ukabu-manager                       â”‚
â”‚                   (CLI Interface)                       â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
             â”‚
             â”œâ”€â†’ Domain Manager    â”€â†’ domains.json
             â”œâ”€â†’ IP Manager        â”€â†’ ip_whitelist.conf
             â”‚                     â”€â†’ ip_blacklist.conf
             â”œâ”€â†’ nginx Manager     â”€â†’ /etc/nginx/includes/
             â”‚                     
             â””â”€â†’ Daemon Client     â”€â†’ ukabu-trackerd
                                       (Unix socket)
```

---

## Installation

### Prerequisites Check

```bash
# Check Python version
python3 --version  # Should be 3.10+

# Check if Component A (ukabu-core)/2 installed
ls -la /etc/ukabu/includes/config.conf
systemctl status ukabu-trackerd
```

### Install

```bash
tar -xzf ukabu-component3.tar.gz
cd ukabu-component3
sudo bash install-component3.sh
```

The installer will:
1. Verify dependencies
2. Install Python packages
3. Install library and CLI tool
4. Create directory structure
5. Initialize configuration files
6. Set up logrotate

---

## Examples

### Basic Setup
```bash
# Add domain with custom difficulty
sudo ukabu-manager domain add example.com -d 20

# Whitelist office network
sudo ukabu-manager whitelist add 203.0.113.0/24

# Generate and reload
sudo ukabu-manager nginx generate-config
sudo ukabu-manager nginx reload
```

### Security Operations
```bash
# Block malicious IP permanently
sudo ukabu-manager blacklist add 198.51.100.42 -r "Scraper bot"

# Temporary block (24 hours)
sudo ukabu-manager blacklist add 192.0.2.100 -d 1440

# Unblock after investigation
sudo ukabu-manager unblock 198.51.100.42
```

### Maintenance
```bash
# Rotate secret with grace period
sudo ukabu-manager domain set-secret example.com --rotate

# Check system status
sudo ukabu-manager status --verbose --strikes

# Dry-run before applying
sudo ukabu-manager --dry-run domain add new-site.com
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [README-PHASE3.md](docs/README-PHASE3.md) | Complete reference guide |
| [QUICKSTART.md](docs/QUICKSTART.md) | 5-minute setup guide |
| [EXAMPLES.md](docs/EXAMPLES.md) | 12 practical scenarios |
| [CHANGELOG-PHASE3.md](docs/CHANGELOG-PHASE3.md) | Version history |

---

## Key Features Deep Dive

### Idempotency

All commands are **idempotent** - safe to run multiple times:

```bash
# Running twice produces same result (no error)
sudo ukabu-manager domain add example.com  # Success
sudo ukabu-manager domain add example.com  # No-op, exit 0
```

### Dry-run Mode

Preview changes without applying:

```bash
sudo ukabu-manager --dry-run domain add test.com
sudo ukabu-manager --dry-run whitelist add 1.2.3.4
```

### Audit Logging

All operations logged to `/var/log/ukabu/manager.log`:

```
2025-11-09 12:00:15 [INFO] Added domain: example.com
2025-11-09 12:05:42 [INFO] Added 192.168.1.100 to whitelist
2025-11-09 12:10:33 [INFO] Rotated secret for domain: example.com
```

### Secret Rotation

HMAC secrets can be rotated with a **12-hour grace period**:

```bash
sudo ukabu-manager domain set-secret example.com --rotate
# Old secret remains valid for 12 hours
# Prevents token invalidation during rotation
```

---

## Troubleshooting

### Common Issues

**Command not found**:
```bash
# Check PATH
which ukabu-manager

# Or use full path
/usr/local/bin/ukabu-manager status
```

**Permission denied**:
```bash
# Most commands require root
sudo ukabu-manager domain add example.com
```

**Daemon not responsive**:
```bash
# Check daemon
systemctl status ukabu-trackerd

# Restart if needed
sudo systemctl restart ukabu-trackerd
```

---

## Support

For licensing inquiries and support:

**Indranil Das Gupta**  
Email: indradg@l2c2.co.in  
Organization: L2C2 Technologies

---

## What's Next?

**Component D (ukabu-extras)** will add:
- X-Forwarded-For configuration
- CDN proxy auto-updater
- Search engine detection
- ML log extraction tools
- Advanced analytics

**Phase 5** will add:
- Prometheus exporter
- Grafana dashboards
- Web UI
- API endpoints
- Complete documentation

---

## License

**Copyright (c) 2025 by L2C2 Technologies. All rights reserved.**

This software is proprietary. For licensing inquiries, contact:  
**Indranil Das Gupta** <indradg@l2c2.co.in>
