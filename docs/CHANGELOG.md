# UKABU WAF - Changelog

**Copyright (c) 2025 by L2C2 Technologies. All rights reserved.**

---

## [1.0.0-component1] - 2025-11-09

### Component A (ukabu-core): nginx PoW Flow Working

**Objective:** Get a working Proof-of-Work challenge that a browser can complete

### Added

#### Core Components
- **nginx Configuration Files**
  - `config.conf` - Variables and maps for domain protection, IP/path whitelisting
  - `endpoints.inc` - PoW endpoint definitions (/ukabu_verify, /ukabu_challenge, /ukabu_validate, /ukabu_help, /ukabu_blocked)
  - `enforcement.inc` - Priority-based access control logic

#### NJS Module
- `pow-challenge.js` - Challenge generation and validation
  - SHA-256 proof-of-work implementation
  - HMAC signing and verification
  - Token generation and validation
  - Secret rotation support (12-hour grace period)
  - Daemon communication stubs (Component B (ukabu-monitor))

#### HTML Pages
- `challenge.html` - Interactive PoW challenge with progress tracking
- `blocked.html` - Blocked IP information page
- `nojs-chrome.html` - No-JS help (Chrome)
- `nojs-firefox.html` - No-JS help (Firefox)
- `nojs-edge.html` - No-JS help (Edge)
- `nojs-safari.html` - No-JS help (Safari)
- `nojs-generic.html` - No-JS help (generic/text browsers)

#### Configuration Examples
- `domains.json` - Domain-specific configuration
- `ip_whitelist.conf` - IP whitelist
- `ip_blacklist.conf` - IP blacklist (Component B (ukabu-monitor) structure)
- `path_whitelist.conf` - Global path exemptions
- `path_blacklist.conf` - Global path blocks
- HMAC secret file examples

#### Examples
- `example-vhost.conf` - Complete vhost example
- `nginx-http-block-example.conf` - HTTP block configuration

#### Documentation
- `README-PHASE1.md` - Installation and setup guide
- `TESTING.md` - Comprehensive testing guide
- `install.sh` - Automated installation script

### Features Implemented

âœ… **PoW Challenge System**
- Browser-based SHA-256 proof-of-work
- Configurable difficulty (12-24 bits)
- 5-minute challenge timeout
- Visual progress tracking

âœ… **Token Management**
- HMAC-signed tokens
- IP-bound authentication
- Configurable expiration (default: 7 days)
- HttpOnly, Secure, SameSite cookies

âœ… **Access Control**
- IP whitelist (bypass all challenges)
- Path whitelist (exempt static assets)
- Path blacklist (block attack vectors)
- Restricted paths (IP-based access)
- Browser detection

âœ… **Security**
- HMAC signature verification
- Challenge replay protection
- Secret rotation support
- Non-browser blocking

âœ… **Multi-Tenancy**
- Per-domain configuration
- Independent HMAC secrets
- Custom difficulty levels
- Domain-specific path rules

### Component A (ukabu-core) Status Codes

| Code | Meaning | Implemented |
|------|---------|-------------|
| 001 | IP Blacklisted | âŒ Component B (ukabu-monitor) |
| 002 | Path Blacklisted | âœ… Yes |
| 100 | Path Whitelisted | âœ… Yes |
| 101 | IP Whitelisted | âœ… Yes |
| 102 | Search Engine | âŒ Component D (ukabu-extras) |
| 103 | Valid PoW Token | âœ… Yes |
| 104 | Domain Not Protected | âœ… Yes |
| 200 | Browser Redirected | âœ… Yes |
| 201 | Non-Browser Blocked | âœ… Yes |

### Known Limitations

âŒ **Not Implemented in Component A (ukabu-core):**
- Strike tracking and automatic blocking (Component B (ukabu-monitor))
- ipset/iptables integration (Component B (ukabu-monitor))
- Daemon (ukabu-trackerd) (Component B (ukabu-monitor))
- CLI tools (ukabu-manager) (Component C (ukabu-manager))
- Search engine detection (Component D (ukabu-extras))
- X-Forwarded-For/CDN handling (Component D (ukabu-extras))
- ML logging and extraction (Component D (ukabu-extras))
- Monitoring and metrics (Phase 5)

### Testing

All core flows tested and working:
- âœ… Challenge generation and solving
- âœ… Token validation and persistence
- âœ… Path-based access control
- âœ… IP-based access control
- âœ… Browser detection
- âœ… No-JS fallback pages
- âœ… Multi-domain support
- âœ… Different difficulty levels

### Breaking Changes

None (initial release)

### Security Notes

- HMAC secrets must be cryptographically secure (48+ bytes recommended)
- Secret files must have 600 permissions
- Tokens are IP-bound for additional security
- Challenge timeout prevents replay attacks

---

## Roadmap

### Component B (ukabu-monitor) (Planned)
- Go daemon (ukabu-trackerd)
- Strike tracking and automatic blocking
- ipset/iptables integration
- SQLite persistence
- Unix socket communication
- Optional first timeout excuse

### Component C (ukabu-manager) (Planned)
- Python CLI (ukabu-manager)
- Domain CRUD operations
- IP/path list management
- nginx config generation
- Secret rotation automation
- Installation wizard

### Component D (ukabu-extras) (Planned)
- Search engine detection (Google, Bing)
- X-Forwarded-For handling
- CDN proxy auto-update
- ML log extraction
- Advanced analytics

### Phase 5 (Planned)
- Prometheus exporter (ukabu-monitor)
- Grafana dashboards
- Complete documentation
- Performance optimization
- Production hardening

---

**For licensing inquiries:**  
Indranil Das Gupta <indradg@l2c2.co.in>  
L2C2 Technologies
