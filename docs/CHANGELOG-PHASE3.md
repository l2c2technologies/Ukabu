# UKABU WAF - Component C (ukabu-manager) Changelog

**Copyright (c) 2025 by L2C2 Technologies. All rights reserved.**

---

## [1.0.0-component3] - 2025-11-09

### Component C (ukabu-manager): Management CLI & Configuration Tools

**Objective:** Provide comprehensive CLI tools for managing UKABU WAF

### Added

#### Core CLI Tool
- **ukabu-manager** - Main command-line interface
  - Click-based CLI with rich argument parsing
  - Global options: `--verbose`, `--dry-run`
  - Comprehensive help text for all commands
  - Exit code standards (0=success, 1=user error, 2=system error)

#### Python Library Modules
- **utils.py** - Common utilities
  - Configuration path management
  - JSON/line-based file I/O with atomic writes
  - IP and domain validation
  - HMAC secret generation
  - Timestamp utilities (ISO 8601)
  - Audit logging setup
  - Permission checks

- **domain.py** - Domain management
  - Add/remove/list/show domains
  - Update domain settings (difficulty, lockout, cookie duration)
  - HMAC secret management and rotation
  - Exempt path management
  - Restricted path management
  - Idempotent operations

- **ipmanager.py** - IP list management
  - Whitelist management (add/remove/list/flush)
  - Blacklist management (add/remove/list/flush)
  - JSONL format for blacklist with metadata
  - Line-based format for whitelist
  - Idempotent operations

- **nginx.py** - nginx configuration management
  - Jinja2-based config generation
  - Domain-specific nginx configs
  - Configuration testing (`nginx -t`)
  - Safe reload with automatic testing
  - Backup before overwriting
  - Vhost template generation

- **daemon.py** - Daemon communication
  - Unix socket client for ukabu-trackerd
  - JSON protocol implementation
  - Health checks and monitoring
  - Strike count queries
  - Block management (add/remove)
  - Config reload signaling

#### Domain Management Commands
```
ukabu-manager domain add <domain> [OPTIONS]
ukabu-manager domain remove <domain> [--force]
ukabu-manager domain list
ukabu-manager domain show <domain>
ukabu-manager domain set <domain> [OPTIONS]
ukabu-manager domain set-secret <domain> [--rotate] [--manual SECRET]
```

#### IP List Management Commands
```
ukabu-manager whitelist add <ip>
ukabu-manager whitelist remove <ip>
ukabu-manager whitelist list

ukabu-manager blacklist add <ip> [--duration N] [--reason TEXT]
ukabu-manager blacklist remove <ip>
ukabu-manager blacklist list
```

#### nginx Management Commands
```
ukabu-manager nginx generate-config [--domain DOMAIN]
ukabu-manager nginx test
ukabu-manager nginx reload [--force]
```

#### System Commands
```
ukabu-manager unblock <ip>
ukabu-manager status [--verbose] [--json] [--strikes]
```

#### Installation & Configuration
- **install-component3.sh** - Automated installation script
  - Dependency detection (Python 3.10+, pip3)
  - Python package installation (click, jinja2)
  - Library installation to /usr/local/lib/ukabu
  - CLI tool installation to /usr/local/bin
  - Directory structure creation
  - Configuration file initialization
  - Logrotate setup
  - Component A (ukabu-core)/2 detection

- **requirements.txt** - Python dependencies
  - click >= 8.1.0
  - jinja2 >= 3.1.0

#### Documentation
- **README-PHASE3.md** - Comprehensive guide
  - Installation instructions
  - Architecture overview
  - Complete command reference
  - Workflow examples
  - Troubleshooting guide
  - Security considerations
  - Integration examples

- **CHANGELOG-PHASE3.md** - Version history

### Features

#### Idempotency
- All operations are idempotent (safe to run multiple times)
- No-op if resource already exists/deleted
- Consistent exit codes (0 for success, even on no-op)

#### Dry-run Mode
- Global `--dry-run` flag for all commands
- Preview changes without applying them
- Safe testing of operations

#### Audit Logging
- All operations logged to `/var/log/ukabu/manager.log`
- Timestamp, level, action details
- Logrotate configured (daily, 30-day retention)

#### Secret Rotation
- 12-hour grace period for rotated secrets
- Previous secret remains valid during transition
- Automatic cleanup of expired secrets
- Manual or auto-generated secrets

#### Safety Features
- Configuration backup before overwriting
- nginx config testing before reload
- Interactive confirmation for destructive operations
- Rollback capability (backup files preserved)

#### Daemon Integration
- Unix socket communication with ukabu-trackerd
- Real-time strike count queries
- Block management (add/remove IPs)
- Config reload signaling
- Health monitoring

#### Error Handling
- Comprehensive error messages
- Validation before applying changes
- Graceful degradation (continue if daemon unreachable)
- Clear troubleshooting guidance

### Configuration Files

#### Generated
- `/etc/ukabu/includes/domains/<domain>.conf` - Per-domain nginx config
- `/etc/ukabu/secrets/<domain>.current.key` - Current HMAC secret
- `/etc/ukabu/secrets/<domain>.previous.key` - Previous secret (during rotation)

#### Modified
- `/etc/ukabu/config/domains.json` - Domain configuration database
- `/etc/ukabu/config/ip_whitelist.conf` - IP whitelist
- `/etc/ukabu/config/ip_blacklist.conf` - IP blacklist (JSONL format)

### Testing

All commands tested for:
- âœ… Idempotency (run twice, same result)
- âœ… Dry-run mode (no changes made)
- âœ… Error handling (invalid input, missing permissions)
- âœ… Audit logging (all operations logged)
- âœ… Daemon communication (socket protocol)
- âœ… Configuration generation (valid nginx syntax)
- âœ… Secret rotation (grace period works)

### Dependencies

#### System
- Python 3.10+
- pip3
- nginx (with NJS module)
- ukabu-trackerd (Component B (ukabu-monitor))

#### Python Packages
- click >= 8.1.0 (CLI framework)
- jinja2 >= 3.1.0 (template engine)

### Compatibility

- **OS**: Ubuntu 20.04+, Debian 11+, RHEL/CentOS/Rocky/AlmaLinux 8+
- **Python**: 3.10, 3.11, 3.12
- **nginx**: 1.18+

### Security

- Secret files stored with 0600 permissions (root only)
- Audit log tracks all changes
- Configuration validation before applying
- No secrets in command-line arguments (logged by shell history)
- Unix socket communication (not network-exposed)

### Known Limitations

- Requires root privileges for most operations
- nginx must be installed and configured
- Component A (ukabu-core) and Component B (ukabu-monitor) must be installed first
- No web UI (CLI only)

### Breaking Changes

None (initial Component C (ukabu-manager) release)

---

## Roadmap

### Component D (ukabu-extras) (Planned)
- X-Forwarded-For configuration commands
- CDN proxy auto-updater
- Search engine detection management
- ML log extraction tools
- Path management (exempt/restricted)
- Advanced analytics queries

### Phase 5 (Planned)
- Prometheus exporter (ukabu-monitor)
- Grafana dashboards
- Web UI for configuration
- API endpoints
- Automated testing suite

---

**For licensing inquiries:**  
Indranil Das Gupta <indradg@l2c2.co.in>  
L2C2 Technologies
