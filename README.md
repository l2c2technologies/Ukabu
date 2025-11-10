# UKABU WAF v1.0.0 - Complete Installation Package

**Copyright © 2025 L2C2 Technologies. All rights reserved.**

For licensing inquiries, contact:
- **Indranil Das Gupta**
- Email: indradg@l2c2.co.in
- Organization: L2C2 Technologies

---

## What is UKABU?

UKABU is a production-ready Web Application Firewall (WAF) designed to protect multi-tenant web applications from AI scrapers and automated bots using **proof-of-work (PoW) challenges** combined with **intelligent strike tracking** and **kernel-level IP blocking**.

### Key Features

- ✅ **Browser-based PoW challenges** (SHA-256) - Blocks AI scrapers that don't execute JavaScript
- ✅ **Two-layer defense** - Kernel-level blocking + application logic
- ✅ **Intelligent strike tracking** - 3-strike automatic blocking
- ✅ **Multi-tenancy support** - Per-domain configuration
- ✅ **Search engine friendly** - Auto-whitelists verified Google/Bing
- ✅ **CDN compatible** - Optional X-Forwarded-For handling
- ✅ **Comprehensive management** - CLI tools for easy administration
- ✅ **Production ready** - Prometheus metrics, structured logging

---

## Quick Start (5 Minutes)

```bash
# 1. Extract tarball
tar -xzf ukabu-1.0.0.tar.gz
cd ukabu-1.0.0

# 2. Run unified installer (detects dependencies and installs automatically)
sudo bash install.sh

# 3. Configure your domain
sudo nano /etc/ukabu/config/domains.json

# 4. Generate HMAC secret
openssl rand -hex 32 | sudo tee /etc/ukabu/secrets/yourdomain.com.key
sudo chmod 600 /etc/ukabu/secrets/yourdomain.com.key

# 5. Configure nginx vhost (see examples/ directory)
sudo cp examples/example-vhost.conf /etc/nginx/sites-available/yourdomain.com
sudo nano /etc/nginx/sites-available/yourdomain.com
sudo ln -s /etc/nginx/sites-available/yourdomain.com /etc/nginx/sites-enabled/

# 6. Test and reload
sudo nginx -t
sudo systemctl reload nginx

# Done! Your site is now protected by UKABU.
```

---

## System Requirements

### Hardware
- **CPU:** 2+ cores (4+ recommended for high traffic)
- **RAM:** 2GB minimum (4GB+ recommended)
- **Disk:** 10GB minimum (20GB+ for logs)
- **Network:** 1Gbps interface

### Software
- **OS:** Ubuntu 20.04+ / Debian 11+ / RHEL 8+ / Rocky Linux 8+
- **nginx:** 1.18+ with **nginx-module-njs** (REQUIRED)
- **Go:** 1.19+ (for Component B (ukabu-monitor) - daemon)
- **Python:** 3.10+ (for Component C (ukabu-manager) - CLI)
- **iptables** OR **nftables** (for Component B (ukabu-monitor))
- **ipset:** Latest version (for Component B (ukabu-monitor))

### Install Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y nginx nginx-module-njs python3 python3-pip \
    iptables ipset build-essential curl jq
```

**RHEL/Rocky/Alma:**
```bash
sudo yum install -y nginx nginx-module-njs python3 python3-pip \
    iptables ipset gcc make curl jq
```

**Go (if not installed):**
```bash
wget https://go.dev/dl/go1.21.0.linux-amd64.tar.gz
sudo tar -C /usr/local -xzf go1.21.0.linux-amd64.tar.gz
echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc
source ~/.bashrc
```

---

## What's Included

This complete package includes all 4 phases of UKABU:

### Component A (ukabu-core): nginx PoW Flow ✅
- nginx configuration files (includes, endpoints, enforcement)
- NJS module for PoW challenges
- HTML challenge pages (with browser detection)
- Configuration examples

**Files:** `etc/ukabu/`, `examples/`

### Component B (ukabu-monitor): Go Daemon (Strike Tracking) ✅
- Real-time strike tracking daemon
- SQLite persistence
- ipset/iptables integration
- Automatic IP blocking
- Prometheus metrics exporter

**Files:** `go-daemon/`, `systemd/ukabu-trackerd.*`, `systemd/ukabu-ipset-init.*`, `systemd/ukabu-unjail.*`

### Component C (ukabu-manager): Python CLI (Management Tools) ✅
- Comprehensive CLI: `ukabu-manager`
- Domain management
- IP list management (whitelist/blacklist)
- nginx configuration generation
- System status and monitoring

**Files:** `lib/ukabu/`, `bin/ukabu-manager`

### Component D (ukabu-extras): Advanced Features ✅
- X-Forwarded-For (XFF) handling
- CDN proxy auto-updater (Cloudflare, AWS, Google, DigitalOcean)
- Search engine detection (Google, Bing)
- Path management (exempt/restricted)
- ML log extraction

**Files:** `scripts/`, `systemd/ukabu-update-*.*`

---

## Installation Components

The unified installer (`install.sh`) automatically detects:
1. What dependencies are available
2. What components are already installed
3. What can be installed

It will install only what's missing and possible based on dependencies.

### Manual Component Installation

If you prefer to install phases manually:

```bash
# Component A (ukabu-core) only (nginx PoW)
sudo bash install.sh  # Will install Component A (ukabu-core) if nginx+njs available

# Component B (ukabu-monitor) only (Go daemon)
cd go-daemon
make build
sudo make install
sudo cp ../systemd/ukabu-*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ukabu-trackerd

# Component C (ukabu-manager) only (Python CLI)
sudo pip3 install -r requirements.txt
sudo cp -r lib/ukabu /usr/local/lib/
sudo cp bin/ukabu-manager /usr/local/bin/
sudo chmod 755 /usr/local/bin/ukabu-manager

# Component D (ukabu-extras) only (Advanced)
sudo cp scripts/* /usr/local/bin/
sudo cp systemd/ukabu-update-*.* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ukabu-update-proxies.timer
sudo systemctl enable --now ukabu-update-search-engines.timer
```

---

## Directory Structure

```
ukabu-1.0.0/
├── install.sh                  # Unified installer (run this!)
├── LICENSE                     # Copyright and licensing
├── requirements.txt            # Python dependencies
│
├── etc/ukabu/                  # Configuration files
│   ├── includes/               # nginx includes
│   │   ├── config.conf         # Variables and maps
│   │   ├── endpoints.inc       # PoW endpoints
│   │   └── enforcement.inc     # Access control logic
│   ├── njs/                    # NJS modules
│   │   └── pow-challenge.js    # PoW challenge logic
│   ├── pages/                  # HTML pages
│   │   ├── challenge.html      # PoW challenge page
│   │   ├── blocked.html        # Blocked IP page
│   │   └── nojs-*.html         # No-JS help pages
│   ├── config/                 # Configuration examples
│   │   ├── domains.json        # Domain configuration
│   │   ├── ip_whitelist.conf   # IP whitelist
│   │   ├── ip_blacklist.conf   # IP blacklist
│   │   ├── path_whitelist.conf # Path whitelist
│   │   └── path_blacklist.conf # Path blacklist
│   └── secrets/                # HMAC secrets
│       └── example.com.key     # Example secret file
│
├── lib/ukabu/                  # Python library
│   ├── __init__.py
│   ├── utils.py                # Common utilities
│   ├── domain.py               # Domain management
│   ├── ipmanager.py            # IP list management
│   ├── nginx.py                # nginx config generation
│   ├── daemon.py               # Daemon communication
│   ├── xff.py                  # XFF handling (Component D (ukabu-extras))
│   ├── paths.py                # Path management (Component D (ukabu-extras))
│   ├── ml_extract.py           # ML extraction (Component D (ukabu-extras))
│   └── search_engines.py       # Search engine detection (Component D (ukabu-extras))
│
├── bin/                        # CLI tools
│   └── ukabu-manager           # Main management CLI
│
├── go-daemon/                  # Go daemon sources
│   ├── main.go                 # Entry point
│   ├── tracker.go              # Strike tracking
│   ├── firewall.go             # Firewall abstraction
│   ├── manager.go              # ipset management
│   ├── server.go               # Unix socket server
│   ├── prometheus.go           # Metrics exporter
│   ├── config.go               # Configuration
│   ├── go.mod                  # Go module
│   └── Makefile                # Build automation
│
├── systemd/                    # systemd units
│   ├── ukabu-trackerd.service  # Main daemon
│   ├── ukabu-ipset-init.service# ipset initialization
│   ├── ukabu-unjail.service    # Automatic unjailing
│   ├── ukabu-unjail.timer      # Unjail timer
│   ├── ukabu-update-proxies.service    # CDN updater
│   ├── ukabu-update-proxies.timer
│   ├── ukabu-update-search-engines.service
│   └── ukabu-update-search-engines.timer
│
├── scripts/                    # Utility scripts
│   ├── ukabu-fetch-cdn-ips.sh  # CDN IP fetcher
│   ├── ukabu-fetch-google-ips.sh # Google IP fetcher
│   └── ukabu-verify-bing.py    # Bing verifier
│
├── examples/                   # Configuration examples
│   ├── example-vhost.conf      # Example nginx vhost
│   ├── nginx-http-block-example.conf
│   └── component4-examples.conf
│
└── docs/                       # Documentation
    ├── README.md               # Main README
    ├── README-PHASE1.md        # Component A (ukabu-core) guide
    ├── README-PHASE2.md        # Component B (ukabu-monitor) guide
    ├── README-PHASE3.md        # Component C (ukabu-manager) guide
    ├── README-PHASE4.md        # Component D (ukabu-extras) guide
    ├── QUICKSTART.md           # Quick start guide
    ├── QUICKSTART-PHASE4.md    # Component D (ukabu-extras) quick start
    ├── TESTING.md              # Testing guide
    ├── EXAMPLES.md             # Configuration examples
    ├── DECISIONS-UPDATED.md    # Architectural decisions
    ├── CHANGELOG.md            # Version history
    ├── CHANGELOG-PHASE3.md     # Component C (ukabu-manager) changelog
    ├── CHANGELOG-PHASE4.md     # Component D (ukabu-extras) changelog
    ├── UKABU-ARCHITECTURE-REVIEW.md  # Architecture review
    ├── UKABU-DEPLOYMENT-GUIDE.md     # Deployment guide
    └── UKABU-EXECUTIVE-SUMMARY.md    # Executive summary
```

---

## Quick Reference

### Management Commands

```bash
# Domain management
ukabu-manager domain add example.com --difficulty 18
ukabu-manager domain set-secret example.com --rotate
ukabu-manager domain list

# IP management
ukabu-manager whitelist add 192.168.1.0/24
ukabu-manager blacklist add 1.2.3.4 --duration 10080
ukabu-manager blacklist list

# Path management (Component D (ukabu-extras))
ukabu-manager paths add-exempt example.com /static/*
ukabu-manager paths add-restricted example.com /admin/* 192.168.1.0/24

# XFF management (Component D (ukabu-extras))
ukabu-manager xff enable example.com --sources cloudflare,aws

# System status
ukabu-manager status
ukabu-manager status --strikes

# nginx management
ukabu-manager nginx generate-config
ukabu-manager nginx test
ukabu-manager nginx reload
```

### Service Management

```bash
# Check daemon status
sudo systemctl status ukabu-trackerd

# View daemon logs
sudo journalctl -u ukabu-trackerd -f

# Restart daemon
sudo systemctl restart ukabu-trackerd

# Check ipsets
sudo ipset list | grep ukabu

# Check timers
sudo systemctl list-timers | grep ukabu
```

---

## Documentation

All comprehensive documentation is in the `docs/` directory:

- **README.md** - Main project overview
- **QUICKSTART.md** - 5-minute quick start
- **README-PHASE1.md** - Component A (ukabu-core) installation (30 min)
- **README-PHASE2.md** - Component B (ukabu-monitor) installation (20 min)
- **README-PHASE3.md** - Component C (ukabu-manager) installation (15 min)
- **README-PHASE4.md** - Component D (ukabu-extras) installation (20 min)
- **TESTING.md** - Comprehensive testing guide
- **EXAMPLES.md** - Configuration examples
- **DECISIONS-UPDATED.md** - Architectural decisions (77KB)
- **UKABU-ARCHITECTURE-REVIEW.md** - Complete technical review
- **UKABU-DEPLOYMENT-GUIDE.md** - Production deployment guide
- **UKABU-EXECUTIVE-SUMMARY.md** - Executive summary

---

## Troubleshooting

### nginx won't start
```bash
sudo nginx -t  # Check configuration
sudo tail -50 /var/log/nginx/error.log  # Check logs
```

### Daemon not running
```bash
sudo systemctl status ukabu-trackerd
sudo journalctl -u ukabu-trackerd -n 100
```

### IPs not being blocked
```bash
# Check ipsets exist
sudo ipset list | grep ukabu

# Check daemon socket
sudo ls -la /var/run/ukabu/tracker.sock

# Check strike database
sudo ls -la /var/lib/ukabu/strikes.db
```

### High false positive rate
```bash
# Lower difficulty
sudo ukabu-manager domain set example.com --difficulty 16

# Increase cookie duration
sudo ukabu-manager domain set example.com --cookie-duration 1209600  # 14 days

# Whitelist known IPs
sudo ukabu-manager whitelist add YOUR_IP
```

See `docs/UKABU-DEPLOYMENT-GUIDE.md` for complete troubleshooting guide.

---

## Security Hardening (Critical!)

Before production deployment, implement these security measures:

### 1. Add Rate Limiting (HIGH PRIORITY)
```nginx
# In nginx http block
limit_req_zone $binary_remote_addr zone=pow_challenge:10m rate=10r/m;
limit_req_zone $binary_remote_addr zone=pow_validate:10m rate=20r/m;
```

### 2. Set File Permissions (CRITICAL)
```bash
sudo chmod 600 /etc/ukabu/secrets/*.key
sudo chown root:root /etc/ukabu/secrets/*.key
```

### 3. Configure Firewall
```bash
# Only allow necessary ports
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT
sudo iptables -A INPUT -j DROP
```

See `docs/UKABU-DEPLOYMENT-GUIDE.md` for complete hardening checklist.

---

## Support & Resources

### Documentation
- Complete documentation in `docs/` directory
- Component-specific guides for each component
- Architecture review and deployment guides

### Contact
- **L2C2 Technologies**
- Email: indradg@l2c2.co.in
- Licensing inquiries: indradg@l2c2.co.in

### Project Information
- **Version:** 1.0.0
- **License:** Copyright © 2025 L2C2 Technologies. All rights reserved.
- **Total Files:** 69+
- **Total Size:** ~1MB (compressed)
- **Documentation:** 30% of codebase

---

## License

Copyright © 2025 by L2C2 Technologies. All rights reserved.

For licensing requirements and inquiries, contact:
- **Indranil Das Gupta**
- Email: indradg@l2c2.co.in

See LICENSE file for complete terms.

---

## Acknowledgments

- nginx-njs examples and documentation
- ipset/iptables community
- Cloudflare for IP range API
- Google for bot verification API
- Open source security community

---

**Get Started:** `sudo bash install.sh`

**Questions?** See `docs/` directory or contact indradg@l2c2.co.in
