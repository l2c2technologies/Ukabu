#!/bin/bash
# Copyright (c) 2025 by L2C2 Technologies. All rights reserved.
#
# For licensing inquiries, contact:
# Indranil Das Gupta <indradg@l2c2.co.in>

#
# UKABU WAF - Unified Installer
# Version: 1.0.0
#
# This script intelligently installs UKABU WAF components based on what's
# already installed and what dependencies are available.
#

set -euo pipefail

# ════════════════════════════════════════════════════════════════
# CONFIGURATION
# ════════════════════════════════════════════════════════════════

VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Installation paths
UKABU_ETC="/etc/ukabu"
UKABU_LIB="/usr/local/lib/ukabu"
UKABU_BIN="/usr/local/bin"
UKABU_VAR="/var/lib/ukabu"
UKABU_LOG="/var/log/ukabu"
UKABU_RUN="/var/run/ukabu"

# Tracking what to install
INSTALL_CORE=false
INSTALL_MONITOR=false
INSTALL_MANAGER=false
INSTALL_EXTRAS=false

# ════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ════════════════════════════════════════════════════════════════

print_banner() {
    echo -e "${CYAN}"
    cat << 'EOF'
    ╦ ╦╦╔═╔═╗╔╗ ╦ ╦  ╦ ╦╔═╗╔═╗
    ║ ║╠╩╗╠═╣╠╩╗║ ║  ║║║╠═╣╠╣
    ╚═╝╩ ╩╩ ╩╚═╝╚═╝  ╚╩╝╩ ╩╚

    Collaborative Anti-AI Scraper WAF
    Version: 1.0.0

EOF
    echo -e "${NC}Copyright (c) 2025 by L2C2 Technologies. All rights reserved.${NC}"
    echo ""
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        error "Please run as root (use sudo)"
        exit 1
    fi
}

detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        OS_VERSION=$VERSION_ID
        info "Detected OS: $PRETTY_NAME"
    else
        error "Cannot detect OS. /etc/os-release not found."
        exit 1
    fi
}

# ════════════════════════════════════════════════════════════════
# DEPENDENCY CHECKING
# ════════════════════════════════════════════════════════════════

check_nginx() {
    if command -v nginx &> /dev/null; then
        NGINX_VERSION=$(nginx -v 2>&1 | grep -oP '\d+\.\d+\.\d+')
        success "nginx $NGINX_VERSION found"

        # Check for njs module using system-specific file paths (Debian/Ubuntu)
        if [ -L /etc/nginx/modules-enabled/50-mod-http-js.conf ]; then

            # Double check the binary file is present for robustness
            if [ -f /usr/lib/nginx/modules/ngx_http_js_module.so ]; then
                success "nginx-njs module found (enabled via link and binary present)"
                return 0
            else
                warn "nginx-njs configuration link found, but dynamic file ngx_http_js_module.so is MISSING."
                warn "Reinstall package: sudo apt-get install --reinstall libnginx-mod-http-js"
                return 1
            fi

        else
            warn "nginx-njs module NOT found (configuration link missing)"
            warn "Install with: **sudo apt-get install libnginx-mod-http-js**"
            warn "  (Ensure it's enabled: **sudo ln -s /usr/share/nginx/modules-available/mod-http-js.conf /etc/nginx/modules-enabled/**)"
            return 1
        fi
    else
        warn "nginx not found"
        warn "Install with: **sudo apt-get install nginx libnginx-mod-http-js**"
        return 1
    fi
}

check_go() {
    if command -v go &> /dev/null; then
        GO_VERSION=$(go version | grep -oP '\d+\.\d+\.\d+' | head -1)
        success "Go $GO_VERSION found"
        return 0
    else
        warn "Go not found (required for Component B (ukabu-monitor) - daemon)"
        warn "Install with: **sudo apt update** and then **sudo apt install golang-go**"
        warn "  (This installs the official Ubuntu-packaged version.)"
        warn "  For the latest version, install from: https://go.dev/dl/"
        return 1
    fi
}

check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | grep -oP '\d+\.\d+\.\d+')
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

        if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 10 ]; then
            success "Python $PYTHON_VERSION found"

            # Check for pip3 but don't fail if missing - we'll handle it during installation
            if command -v pip3 &> /dev/null || python3 -m pip --version &> /dev/null 2>&1; then
                success "pip3 found"
            else
                warn "pip3 is missing (only needed for installing new Python packages)"
            fi
            return 0
        else
            warn "Python $PYTHON_VERSION found, but 3.10+ required for Component C (ukabu-manager)"
            return 1
        fi
    else
        warn "Python3 not found (required for Component C (ukabu-manager) - CLI)"
        return 1
    fi
}

check_iptables() {
    if command -v iptables &> /dev/null; then
        success "iptables found"
        return 0
    elif command -v nft &> /dev/null; then
        success "nftables found"
        return 0
    else
        warn "Neither iptables nor nftables found (required for Component B (ukabu-monitor))"
        return 1
    fi
}

check_ipset() {
    if command -v ipset &> /dev/null; then
        success "ipset found"
        return 0
    else
        warn "ipset not found (required for Component B (ukabu-monitor))"
        warn "Install with: apt-get install ipset (Debian/Ubuntu)"
        warn "           or: yum install ipset (RHEL/Rocky)"
        return 1
    fi
}

check_jq() {
    if command -v jq &> /dev/null; then
        success "jq found"
        return 0
    else
        warn "jq not found (optional but recommended for Component A (ukabu-core))"
        warn "Install with: apt-get install jq (Debian/Ubuntu)"
        warn "Without jq, only test.local secrets are auto-generated"
        return 1
    fi
}

# ════════════════════════════════════════════════════════════════
# PHASE DETECTION
# ════════════════════════════════════════════════════════════════

detect_installed_components() {
    echo ""
    info "Detecting installed components..."

    # Check Component A (ukabu-core) (nginx config) - Comprehensive check
    info "Checking Component A (ukabu-core) components..."

    local component1_complete=true
    local component1_status=""

    # Required nginx config files
    local required_configs=(
        "$UKABU_ETC/includes/config.conf"
        "$UKABU_ETC/includes/endpoints.inc"
        "$UKABU_ETC/includes/enforcement.inc"
        "$UKABU_ETC/njs/pow-challenge.js"
        "$UKABU_ETC/config/domains.json"
    )

    for file in "${required_configs[@]}"; do
        if [ ! -f "$file" ]; then
            component1_complete=false
            component1_status="${component1_status}    ✗ Missing: $file\n"
        fi
    done

    # Check if test.local domain exists in config and has its secret
    if [ -f "$UKABU_ETC/config/domains.json" ]; then
        # Check for missing secrets for ALL domains in domains.json
        if command -v jq &> /dev/null; then
            # Use jq if available for robust JSON parsing
            local missing_secrets=$(jq -r '.domains | to_entries[] | .key + "|" + .value.hmac_secret_file' "$UKABU_ETC/config/domains.json" 2>/dev/null | while IFS='|' read -r domain secret_file; do
                if [ ! -f "$secret_file" ]; then
                    echo "$domain:$secret_file"
                fi
            done)
            
            if [ -n "$missing_secrets" ]; then
                component1_complete=false
                while IFS=':' read -r domain secret_file; do
                    component1_status="${component1_status}    ✗ Missing: $secret_file (required by domain '$domain')\n"
                done <<< "$missing_secrets"
            fi
        else
            # Fallback: just check test.local if jq not available
            if grep -q '"test\.local"' "$UKABU_ETC/config/domains.json" 2>/dev/null; then
                if [ ! -f "$UKABU_ETC/secrets/test.local.key" ]; then
                    component1_complete=false
                    component1_status="${component1_status}    ✗ Missing: $UKABU_ETC/secrets/test.local.key (required by test.local)\n"
                    component1_status="${component1_status}    ℹ Install jq for comprehensive secret validation: apt install jq\n"
                fi
            fi
        fi
    fi

    # Required HTML pages
    local required_pages=(
        "$UKABU_ETC/pages/challenge.html"
        "$UKABU_ETC/pages/blocked.html"
    )

    for file in "${required_pages[@]}"; do
        if [ ! -f "$file" ]; then
            component1_complete=false
            component1_status="${component1_status}    ✗ Missing: $file\n"
        fi
    done

    # Determine status
    if [ "$component1_complete" = true ]; then
        success "Component A: ukabu-core (nginx PoW flow) is installed and complete"
        CORE_INSTALLED=true
        INSTALL_CORE=false
    else
        if [ -n "$component1_status" ]; then
            warn "Component A: ukabu-core (nginx PoW flow) is incomplete:"
            echo -e "$component1_status"
            info "Will reinstall/complete Component A (ukabu-core)"
        else
            info "Component A: ukabu-core (nginx PoW flow) not installed"
        fi
        CORE_INSTALLED=false
        INSTALL_CORE=true
    fi

    # Check Component B (ukabu-monitor) (daemon) - Comprehensive check
    info "Checking Component B (ukabu-monitor) components..."

    local component2_complete=true
    local component2_status=""

    # Required files check
    local required_files=(
        "/usr/local/bin/ukabu-trackerd"
        "/usr/local/bin/ukabu-ipset-init.sh"
        "/usr/local/bin/ukabu-unjail.sh"
    )

    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            component2_complete=false
            component2_status="${component2_status}    ✗ Missing: $file\n"
        fi
    done

    # Required services check
    local required_services=(
        "ukabu-trackerd"
        "ukabu-ipset-init"
        "ukabu-unjail.timer"
    )

    for service in "${required_services[@]}"; do
        if ! systemctl list-unit-files | grep -q "$service"; then
            component2_complete=false
            component2_status="${component2_status}    ✗ Missing service: $service\n"
        fi
    done

    # Determine status
    if [ "$component2_complete" = true ]; then
        success "Component B: ukabu-monitor (Go daemon) is installed and complete"
        MONITOR_INSTALLED=true
        INSTALL_MONITOR=false
    else
        if [ -n "$component2_status" ]; then
            warn "Component B: ukabu-monitor (Go daemon) is incomplete:"
            echo -e "$component2_status"
            info "Will reinstall/complete Component B (ukabu-monitor)"
        else
            info "Component B: ukabu-monitor (Go daemon) not installed"
        fi
        MONITOR_INSTALLED=false
        INSTALL_MONITOR=true
    fi

    # Check Component C (ukabu-manager) (CLI) - Comprehensive check
    info "Checking Component C (ukabu-manager) components..."

    local component3_complete=true
    local component3_status=""

    # Required files check
    local required_files=(
        "$UKABU_BIN/ukabu-manager"
        "$UKABU_LIB/__init__.py"
        "$UKABU_LIB/domain.py"
        "$UKABU_LIB/ipmanager.py"
        "$UKABU_LIB/nginx.py"
        "$UKABU_LIB/utils.py"
        "$UKABU_LIB/daemon.py"
    )

    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            component3_complete=false
            component3_status="${component3_status}    ✗ Missing: $file\n"
        fi
    done

    # Check if Python dependencies are installed (critical for functionality)
    if [ "$component3_complete" = true ]; then
        # Check for key Python packages that should be installed
        if ! python3 -c "import click" 2>/dev/null || \
           ! python3 -c "import jinja2" 2>/dev/null; then
            component3_complete=false
            component3_status="${component3_status}    ✗ Python dependencies missing (pip3 may not be installed)\n"
        fi
    fi

    # Determine status
    if [ "$component3_complete" = true ]; then
        success "Component C: ukabu-manager (Python CLI) is installed and complete"
        MANAGER_INSTALLED=true
        INSTALL_MANAGER=false
    else
        if [ -n "$component3_status" ]; then
            warn "Component C: ukabu-manager (Python CLI) is incomplete:"
            echo -e "$component3_status"
            info "Will reinstall/complete Component C (ukabu-manager)"
        else
            info "Component C: ukabu-manager (Python CLI) not installed"
        fi
        MANAGER_INSTALLED=false
        INSTALL_MANAGER=true
    fi

    # Check Component D (ukabu-extras) (advanced features) - Comprehensive check
    info "Checking Component D (ukabu-extras) components..."

    local component4_complete=true
    local component4_status=""

    # Required Python modules
    local required_modules=(
        "$UKABU_LIB/xff.py"
        "$UKABU_LIB/paths.py"
        "$UKABU_LIB/search_engines.py"
        "$UKABU_LIB/ml_extract.py"
    )

    for file in "${required_modules[@]}"; do
        if [ ! -f "$file" ]; then
            component4_complete=false
            component4_status="${component4_status}    ✗ Missing: $file\n"
        fi
    done

    # Required scripts
    local required_scripts=(
        "$UKABU_BIN/ukabu-fetch-cdn-ips.sh"
        "$UKABU_BIN/ukabu-fetch-google-ips.sh"
        "$UKABU_BIN/ukabu-verify-bing.py"
    )

    for file in "${required_scripts[@]}"; do
        if [ ! -f "$file" ]; then
            component4_complete=false
            component4_status="${component4_status}    ✗ Missing: $file\n"
        fi
    done

    # Required services
    local required_services=(
        "ukabu-update-proxies.timer"
        "ukabu-update-search-engines.timer"
    )

    for service in "${required_services[@]}"; do
        if ! systemctl list-unit-files | grep -q "$service"; then
            component4_complete=false
            component4_status="${component4_status}    ✗ Missing service: $service\n"
        fi
    done

    # Determine status
    if [ "$component4_complete" = true ]; then
        success "Component D: ukabu-extras (Advanced features) is installed and complete"
        EXTRAS_INSTALLED=true
        INSTALL_EXTRAS=false
    else
        if [ -n "$component4_status" ]; then
            warn "Component D: ukabu-extras (Advanced features) is incomplete:"
            echo -e "$component4_status"
            info "Will reinstall/complete Component D (ukabu-extras)"
        else
            info "Component D: ukabu-extras (Advanced features) not installed"
        fi
        EXTRAS_INSTALLED=false
        INSTALL_EXTRAS=true
    fi
}

# ════════════════════════════════════════════════════════════════
# INSTALLATION FUNCTIONS
# ════════════════════════════════════════════════════════════════

install_core() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  Component A (ukabu-core): nginx PoW Flow${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"

    # Create directory structure
    info "Creating directory structure..."
    mkdir -p $UKABU_ETC/{includes,njs,pages,config,secrets}
    mkdir -p $UKABU_VAR
    mkdir -p $UKABU_LOG
    mkdir -p $UKABU_RUN

    # Copy nginx configuration files
    info "Installing nginx configuration files..."
    cp -v $SCRIPT_DIR/etc/ukabu/includes/*.inc $UKABU_ETC/includes/
    cp -v $SCRIPT_DIR/etc/ukabu/includes/*.conf $UKABU_ETC/includes/

    # Copy NJS module
    info "Installing NJS module..."
    cp -v $SCRIPT_DIR/etc/ukabu/njs/pow-challenge.js $UKABU_ETC/njs/

    # Copy HTML pages
    info "Installing HTML pages..."
    cp -v $SCRIPT_DIR/etc/ukabu/pages/*.html $UKABU_ETC/pages/

    # Copy configuration examples
    info "Installing configuration files..."
    cp -v $SCRIPT_DIR/etc/ukabu/config/*.conf $UKABU_ETC/config/

    # Install domains.json (includes test.local for verification)
    if [ ! -f "$UKABU_ETC/config/domains.json" ]; then
        cp -v $SCRIPT_DIR/etc/ukabu/config/domains.json $UKABU_ETC/config/
        success "Installed domains.json (includes test.local for verification)"
    else
        warn "domains.json already exists, not overwriting"
        info "Backup saved to: $UKABU_ETC/config/domains.json.installed.backup"
        cp -v $SCRIPT_DIR/etc/ukabu/config/domains.json $UKABU_ETC/config/domains.json.installed.backup
    fi

    # Generate missing HMAC secrets for all domains in domains.json
    if [ -f "$UKABU_ETC/config/domains.json" ]; then
        if command -v jq &> /dev/null; then
            # Use jq to process all domains
            info "Checking HMAC secrets for all domains..."
            
            # Process each domain
            while IFS='|' read -r domain secret_file; do
                if [ -n "$domain" ] && [ -n "$secret_file" ]; then
                    if [ ! -f "$secret_file" ]; then
                        info "Generating HMAC secret for $domain..."
                        SECRET=$(openssl rand -hex 32)
                        
                        # Create directory if it doesn't exist
                        mkdir -p "$(dirname "$secret_file")"
                        
                        cat > "$secret_file" << EOF
# ========================================
# UKABU WAF - Domain HMAC Secret
# Domain: $domain
# Generated: $(date +"%Y-%m-%d %H:%M:%S %Z")
# ========================================
#
# Permissions: 600 (rw-------)
# ========================================

hmac_secret=$SECRET
hmac_secret_old=
rotation_expires=
EOF
                        chmod 600 "$secret_file"
                        success "Generated HMAC secret for $domain"
                    fi
                fi
            done < <(jq -r '.domains | to_entries[] | .key + "|" + .value.hmac_secret_file' "$UKABU_ETC/config/domains.json" 2>/dev/null)
        else
            # Fallback: just handle test.local if jq not available
            if grep -q '"test\.local"' "$UKABU_ETC/config/domains.json" 2>/dev/null; then
                if [ ! -f "$UKABU_ETC/secrets/test.local.key" ]; then
                    info "Generating test.local HMAC secret..."
                    TEST_SECRET=$(openssl rand -hex 32)
                    cat > "$UKABU_ETC/secrets/test.local.key" << EOF
# ========================================
# UKABU WAF - Test Domain HMAC Secret
# Domain: test.local
# Generated: $(date +"%Y-%m-%d %H:%M:%S %Z")
# ========================================
#
# WARNING: This is for TESTING ONLY
# Remove test.local domain before production use
#
# Permissions: 600 (rw-------)
# ========================================

hmac_secret=$TEST_SECRET
hmac_secret_old=
rotation_expires=
EOF
                    chmod 600 "$UKABU_ETC/secrets/test.local.key"
                    success "Generated test.local HMAC secret"
                fi
                
                warn "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                warn "  Note: jq not installed"
                warn "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                echo ""
                echo "  For automatic secret generation for all domains:"
                echo "    sudo apt-get install jq"
                echo ""
                echo "  Without jq, only test.local secrets are auto-generated."
                echo "  For other domains, use: ukabu-manager domain set-secret <domain>"
                echo ""
            fi
        fi
    fi

    # Copy secret example (but don't overwrite existing)
    if [ ! -f "$UKABU_ETC/secrets/example.com.key" ]; then
        cp -v $SCRIPT_DIR/etc/ukabu/secrets/example_com.key $UKABU_ETC/secrets/example.com.key
    fi

    # Set permissions
    info "Setting permissions..."
    chmod 755 $UKABU_ETC/{includes,njs,pages,config}
    chmod 700 $UKABU_ETC/secrets
    chmod 644 $UKABU_ETC/includes/*
    chmod 644 $UKABU_ETC/njs/*
    chmod 644 $UKABU_ETC/pages/*
    chmod 644 $UKABU_ETC/config/*.conf
    chmod 644 $UKABU_ETC/config/domains.json
    chmod 600 $UKABU_ETC/secrets/*.key

    # Set ownership
    chown -R root:root $UKABU_ETC

    # Create log directory with proper permissions
    chown root:root $UKABU_LOG
    chmod 755 $UKABU_LOG

    success "Component A (ukabu-core) installation complete!"

    echo ""
    warn "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    warn "  IMPORTANT: Test Domain Installed"
    warn "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "  A test domain (test.local) has been configured to verify installation."
    echo "  The ukabu-trackerd daemon should start successfully."
    echo ""
    warn "  ⚠️  BEFORE PRODUCTION USE:"
    echo "     1. Remove or replace 'test.local' in $UKABU_ETC/config/domains.json"
    echo "     2. Add your actual domain(s)"
    echo "     3. Generate HMAC secrets for your domains"
    echo ""
    echo "  📖 Read the configuration guide:"
    echo "     $SCRIPT_DIR/docs/DOMAINS-CONFIGURATION.md"
    echo ""
    echo "  ⚡ Quick Start (CLI method - recommended):"
    echo "     # Remove test domain"
    echo "     ukabu-manager domain remove test.local"
    echo ""
    echo "     # Add your domain"
    echo "     ukabu-manager domain add yourdomain.com --difficulty 18"
    echo "     ukabu-manager domain set-secret yourdomain.com"
    echo "     ukabu-manager nginx generate-config"
    echo "     nginx -t && systemctl reload nginx"
    echo ""
    echo "  📝 Manual Configuration:"
    echo "     1. Edit: $UKABU_ETC/config/domains.json"
    echo "     2. Remove 'test.local' from 'domains' section"
    echo "     3. Add your domain(s) - see DOMAINS-CONFIGURATION.md for examples"
    echo "     4. Generate HMAC secret: openssl rand -hex 32 > /etc/ukabu/secrets/yourdomain.com.key"
    echo "     5. Set permissions: chmod 600 /etc/ukabu/secrets/yourdomain.com.key"
    echo "     6. Configure nginx vhost (see examples/ directory)"
    echo "     7. Test: nginx -t && systemctl reload nginx"
    echo ""
}

install_monitor() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  Component B (ukabu-monitor): Go Daemon (Strike Tracking)${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"

    # Navigate to go-daemon directory
    cd $SCRIPT_DIR/go-daemon

    # Check if Go files need to be reorganized into pkg/ structure
    info "Checking Go project structure..."

    if [ -f "config.go" ] || [ -f "firewall.go" ]; then
        info "Reorganizing Go files into pkg/ structure..."

        # Create pkg directory structure
        mkdir -p pkg/{config,ipset,metrics,socket,strikes}

        # Move files to their respective packages (only if they exist in root)
        [ -f "config.go" ] && mv config.go pkg/config/ && info "  → Moved config.go to pkg/config/"
        [ -f "firewall.go" ] && mv firewall.go pkg/ipset/ && info "  → Moved firewall.go to pkg/ipset/"
        [ -f "manager.go" ] && mv manager.go pkg/ipset/ && info "  → Moved manager.go to pkg/ipset/"
        [ -f "prometheus.go" ] && mv prometheus.go pkg/metrics/ && info "  → Moved prometheus.go to pkg/metrics/"
        [ -f "server.go" ] && mv server.go pkg/socket/ && info "  → Moved server.go to pkg/socket/"
        [ -f "tracker.go" ] && mv tracker.go pkg/strikes/ && info "  → Moved tracker.go to pkg/strikes/"

        success "Go project structure reorganized"
    else
        success "Go project structure is already correct"
    fi

    # Download dependencies and generate go.sum if missing
    if [ ! -f "go.sum" ]; then
        info "Downloading Go dependencies..."
        go mod download || {
            error "Failed to download Go dependencies"
            exit 1
        }
        go mod tidy || {
            error "Failed to tidy go.mod"
            exit 1
        }
        success "Go dependencies ready"
    else
        info "Go dependencies already present"
    fi

    # Build Go daemon
    info "Building ukabu-trackerd..."
    make clean || true
    make build || {
        error "Failed to build ukabu-trackerd"
        error "Check build logs above for details"
        exit 1
    }

    # Install binary
    info "Installing daemon binary..."
    make install || {
        error "Failed to install ukabu-trackerd"
        exit 1
    }

    # Return to script directory
    cd $SCRIPT_DIR

    # Install scripts
    info "Installing Component B (ukabu-monitor) scripts..."

    local scripts_missing=false

    if [ -f "$SCRIPT_DIR/scripts/ukabu-ipset-init.sh" ]; then
        cp -v $SCRIPT_DIR/scripts/ukabu-ipset-init.sh $UKABU_BIN/
        chmod 755 $UKABU_BIN/ukabu-ipset-init.sh
        success "Installed ukabu-ipset-init.sh"
    else
        error "Missing required script: scripts/ukabu-ipset-init.sh"
        scripts_missing=true
    fi

    if [ -f "$SCRIPT_DIR/scripts/ukabu-unjail.sh" ]; then
        cp -v $SCRIPT_DIR/scripts/ukabu-unjail.sh $UKABU_BIN/
        chmod 755 $UKABU_BIN/ukabu-unjail.sh
        success "Installed ukabu-unjail.sh"
    else
        error "Missing required script: scripts/ukabu-unjail.sh"
        scripts_missing=true
    fi

    if [ "$scripts_missing" = true ]; then
        error "Component B (ukabu-monitor) installation incomplete - missing required scripts"
        error "Please add the missing scripts to $SCRIPT_DIR/scripts/ and run again"
        echo ""
        echo "Required scripts:"
        echo "  - scripts/ukabu-ipset-init.sh"
        echo "  - scripts/ukabu-unjail.sh"
        echo ""
        echo "Download them from the UKABU repository or documentation"
        exit 1
    fi

    # Install systemd units
    info "Installing systemd units..."
    cp -v $SCRIPT_DIR/systemd/ukabu-trackerd.service /etc/systemd/system/
    cp -v $SCRIPT_DIR/systemd/ukabu-ipset-init.service /etc/systemd/system/
    cp -v $SCRIPT_DIR/systemd/ukabu-unjail.service /etc/systemd/system/
    cp -v $SCRIPT_DIR/systemd/ukabu-unjail.timer /etc/systemd/system/

    # Create runtime directory
    mkdir -p $UKABU_RUN
    chmod 755 $UKABU_RUN

    # Reload systemd
    systemctl daemon-reload

    # Enable and start ipset init
    info "Initializing ipsets..."
    systemctl enable ukabu-ipset-init
    systemctl start ukabu-ipset-init

    # Enable and start daemon
    info "Starting ukabu-trackerd..."
    systemctl enable ukabu-trackerd
    systemctl start ukabu-trackerd

    # Enable unjail timer
    systemctl enable ukabu-unjail.timer
    systemctl start ukabu-unjail.timer

    # Check status
    if systemctl is-active --quiet ukabu-trackerd; then
        success "Component B (ukabu-monitor) installation complete! Daemon is running."
        info "Check status: systemctl status ukabu-trackerd"
        info "View metrics: curl http://localhost:9090/metrics"
    else
        warn "Daemon installation complete, but service failed to start"
        warn "Check logs with: journalctl -u ukabu-trackerd -xe"
        error "Daemon failed to start - please check logs"
        exit 1
    fi
}

install_manager() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  Component C (ukabu-manager): Python CLI (Management Tools)${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"

    # Determine pip command to use
    PIP_CMD=""
    PIP_AVAILABLE=false
    
    if command -v pip3 &> /dev/null; then
        PIP_CMD="pip3"
        PIP_AVAILABLE=true
    elif python3 -m pip --version &> /dev/null 2>&1; then
        PIP_CMD="python3 -m pip"
        PIP_AVAILABLE=true
        info "Using 'python3 -m pip' (pip3 command not found)"
    else
        warn "Neither pip3 nor 'python3 -m pip' is available"
        echo ""
        echo "Component C (ukabu-manager) requires pip3 to install Python dependencies."
        echo ""
        read -p "Would you like to install pip3 now? [Y/n] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
            info "Installing pip3..."
            
            # Quiet installation - only show errors
            if apt-get update -qq > /dev/null 2>&1 && \
               apt-get install -y python3-pip > /dev/null 2>&1; then
                
                # Re-check after installation
                if command -v pip3 &> /dev/null; then
                    PIP_CMD="pip3"
                    PIP_AVAILABLE=true
                    success "pip3 installed successfully"
                elif python3 -m pip --version &> /dev/null 2>&1; then
                    PIP_CMD="python3 -m pip"
                    PIP_AVAILABLE=true
                    success "pip3 installed successfully"
                else
                    error "Failed to verify pip3 installation"
                    warn "Continuing without Python dependencies - some features may not work"
                fi
            else
                error "Failed to install pip3"
                warn "Continuing without Python dependencies - some features may not work"
            fi
        else
            warn "Skipping pip3 installation"
            warn "Continuing without Python dependencies - some features may not work"
        fi
    fi

    # Install Python dependencies if pip is available
    if [ "$PIP_AVAILABLE" = true ] && [ -f "$SCRIPT_DIR/requirements.txt" ]; then
        info "Installing Python dependencies..."
        
        # Try with --break-system-packages first (for newer systems), quietly
        if $PIP_CMD install -r $SCRIPT_DIR/requirements.txt --break-system-packages -q > /dev/null 2>&1; then
            success "Python dependencies installed"
        elif $PIP_CMD install -r $SCRIPT_DIR/requirements.txt -q > /dev/null 2>&1; then
            success "Python dependencies installed"
        else
            warn "Some Python dependencies may have failed to install"
            warn "You can install manually: $PIP_CMD install -r $SCRIPT_DIR/requirements.txt"
        fi
    elif [ "$PIP_AVAILABLE" = false ]; then
        warn "Skipping Python dependencies (pip3 not available)"
    fi

    # Install Python libraries
    info "Installing Python libraries..."
    mkdir -p $UKABU_LIB
    cp -v $SCRIPT_DIR/lib/ukabu/*.py $UKABU_LIB/
    chmod 644 $UKABU_LIB/*.py

    # Install CLI tool
    info "Installing ukabu-manager CLI..."
    cp -v $SCRIPT_DIR/bin/ukabu-manager $UKABU_BIN/
    chmod 755 $UKABU_BIN/ukabu-manager

    # Create config backup directory
    mkdir -p $UKABU_ETC/config/.backups

    success "Component C (ukabu-manager) installation complete!"

    if [ "$PIP_AVAILABLE" = false ]; then
        echo ""
        warn "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        warn "  Python dependencies were not installed"
        warn "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        echo "  To install them manually later:"
        echo "  1. Install pip3: sudo apt-get install python3-pip"
        echo "  2. Install dependencies: pip3 install -r $SCRIPT_DIR/requirements.txt --break-system-packages"
        echo ""
    fi

    echo ""
    info "Test with: ukabu-manager --help"
}

install_extras() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  Component D (ukabu-extras): Advanced Features${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"

    # Install Component D (ukabu-extras) Python modules (already in lib/ukabu from Component C (ukabu-manager))
    # Just verify they exist
    if [ ! -f "$UKABU_LIB/xff.py" ]; then
        cp -v $SCRIPT_DIR/lib/ukabu/xff.py $UKABU_LIB/
        cp -v $SCRIPT_DIR/lib/ukabu/paths.py $UKABU_LIB/
        cp -v $SCRIPT_DIR/lib/ukabu/ml_extract.py $UKABU_LIB/
        cp -v $SCRIPT_DIR/lib/ukabu/search_engines.py $UKABU_LIB/
    fi

    # Install scripts
    info "Installing scripts..."
    cp -v $SCRIPT_DIR/scripts/ukabu-fetch-cdn-ips.sh $UKABU_BIN/
    cp -v $SCRIPT_DIR/scripts/ukabu-fetch-google-ips.sh $UKABU_BIN/
    cp -v $SCRIPT_DIR/scripts/ukabu-verify-bing.py $UKABU_BIN/
    chmod 755 $UKABU_BIN/ukabu-fetch-*.sh
    chmod 755 $UKABU_BIN/ukabu-verify-*.py

    # Install systemd timers
    info "Installing systemd timers..."
    cp -v $SCRIPT_DIR/systemd/ukabu-update-proxies.service /etc/systemd/system/
    cp -v $SCRIPT_DIR/systemd/ukabu-update-proxies.timer /etc/systemd/system/
    cp -v $SCRIPT_DIR/systemd/ukabu-update-search-engines.service /etc/systemd/system/
    cp -v $SCRIPT_DIR/systemd/ukabu-update-search-engines.timer /etc/systemd/system/

    # Reload systemd
    systemctl daemon-reload

    # Enable and start timers
    info "Enabling systemd timers..."
    systemctl enable ukabu-update-proxies.timer
    systemctl start ukabu-update-proxies.timer
    systemctl enable ukabu-update-search-engines.timer
    systemctl start ukabu-update-search-engines.timer

    # Run initial updates
    info "Running initial CDN/search engine IP updates..."
    $UKABU_BIN/ukabu-fetch-cdn-ips.sh || warn "CDN IP fetch failed (may need curl/jq)"
    $UKABU_BIN/ukabu-fetch-google-ips.sh || warn "Google IP fetch failed (may need curl/jq)"

    success "Component D (ukabu-extras) installation complete!"
}

# ════════════════════════════════════════════════════════════════
# MAIN INSTALLATION LOGIC
# ════════════════════════════════════════════════════════════════

main() {
    print_banner
    check_root
    detect_os

    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  Checking Dependencies${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"

    # Check dependencies
    NGINX_OK=false
    GO_OK=false
    PYTHON_OK=false
    IPTABLES_OK=false
    IPSET_OK=false
    JQ_OK=false

    check_nginx && NGINX_OK=true || true
    check_go && GO_OK=true || true
    check_python && PYTHON_OK=true || true
    check_iptables && IPTABLES_OK=true || true
    check_ipset && IPSET_OK=true || true
    check_jq && JQ_OK=true || true

    # Detect what's already installed
    detect_installed_components

    # Determine what can be installed
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  Installation Plan${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"

    # Component A (ukabu-core): Requires nginx with njs
    if [ "$INSTALL_CORE" = true ]; then
        if [ "$NGINX_OK" = true ]; then
            info "Component A: ukabu-core (nginx PoW flow) - Will install"
        else
            warn "Component A: ukabu-core (nginx PoW flow) - Cannot install (nginx/njs missing)"
            INSTALL_CORE=false
        fi
    else
        success "Component A: ukabu-core (nginx PoW flow) - Already installed"
    fi

    # Component B (ukabu-monitor): Requires Go, iptables/nftables, ipset
    if [ "$INSTALL_MONITOR" = true ]; then
        if [ "$GO_OK" = true ] && [ "$IPTABLES_OK" = true ] && [ "$IPSET_OK" = true ]; then
            info "Component B: ukabu-monitor (Go daemon) - Will install"
        else
            warn "Component B: ukabu-monitor (Go daemon) - Cannot install (missing: Go=$GO_OK, iptables=$IPTABLES_OK, ipset=$IPSET_OK)"
            INSTALL_MONITOR=false
        fi
    else
        success "Component B: ukabu-monitor (Go daemon) - Already installed"
    fi

    # Component C (ukabu-manager): Requires Python 3.10+
    if [ "$INSTALL_MANAGER" = true ]; then
        if [ "$PYTHON_OK" = true ]; then
            info "Component C: ukabu-manager (Python CLI) - Will install"
        else
            warn "Component C: ukabu-manager (Python CLI) - Cannot install (Python 3.10+ missing)"
            INSTALL_MANAGER=false
        fi
    else
        success "Component C: ukabu-manager (Python CLI) - Already installed"
    fi

    # Component D (ukabu-extras): Requires Component C (ukabu-manager)
    if [ "$INSTALL_EXTRAS" = true ]; then
        if [ "$MANAGER_INSTALLED" = true ] || [ "$INSTALL_MANAGER" = true ]; then
            info "Component D: ukabu-extras (Advanced features) - Will install"
        else
            warn "Component D: ukabu-extras (Advanced features) - Cannot install (Component C (ukabu-manager) required)"
            INSTALL_EXTRAS=false
        fi
    else
        success "Component D: ukabu-extras (Advanced features) - Already installed"
    fi

    # Check if anything to install
    SOMETHING_INSTALLED=false
    SOMETHING_BLOCKED=false
    
    if [ "$INSTALL_CORE" = true ] || [ "$INSTALL_MONITOR" = true ] || \
       [ "$INSTALL_MANAGER" = true ] || [ "$INSTALL_EXTRAS" = true ]; then
        SOMETHING_INSTALLED=true
    fi
    
    # Check if any phase needs installation but is blocked by dependencies
    if [ "$CORE_INSTALLED" = false ] && [ "$INSTALL_CORE" = false ] && [ "$NGINX_OK" = false ]; then
        SOMETHING_BLOCKED=true
    fi
    if [ "$MONITOR_INSTALLED" = false ] && [ "$INSTALL_MONITOR" = false ] && \
       ([ "$GO_OK" = false ] || [ "$IPTABLES_OK" = false ] || [ "$IPSET_OK" = false ]); then
        SOMETHING_BLOCKED=true
    fi
    if [ "$MANAGER_INSTALLED" = false ] && [ "$INSTALL_MANAGER" = false ] && [ "$PYTHON_OK" = false ]; then
        SOMETHING_BLOCKED=true
    fi
    if [ "$EXTRAS_INSTALLED" = false ] && [ "$INSTALL_EXTRAS" = false ] && \
       [ "$MANAGER_INSTALLED" = false ] && [ "$INSTALL_MANAGER" = false ]; then
        SOMETHING_BLOCKED=true
    fi
    
    if [ "$SOMETHING_INSTALLED" = false ] && [ "$SOMETHING_BLOCKED" = false ]; then
        echo ""
        success "All components are already installed!"
        echo ""
        info "To reinstall or upgrade, manually remove components and run again."
        exit 0
    fi
    
    if [ "$SOMETHING_INSTALLED" = false ] && [ "$SOMETHING_BLOCKED" = true ]; then
        echo ""
        error "Some components need installation but dependencies are missing!"
        echo ""
        error "Please install the missing dependencies listed above and run again."
        echo ""
        info "Quick install commands:"
        [ "$NGINX_OK" = false ] && echo "  sudo apt-get install nginx libnginx-mod-http-js"
        [ "$GO_OK" = false ] && echo "  sudo apt-get install golang-go"
        [ "$PYTHON_OK" = false ] && echo "  sudo apt-get install python3 python3-pip"
        [ "$IPSET_OK" = false ] && echo "  sudo apt-get install ipset"
        exit 1
    fi

    # Confirm installation
    echo ""
    read -p "Proceed with installation? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        warn "Installation cancelled"
        exit 0
    fi

    # Perform installations
    [ "$INSTALL_CORE" = true ] && install_core
    [ "$INSTALL_MONITOR" = true ] && install_monitor
    [ "$INSTALL_MANAGER" = true ] && install_manager
    [ "$INSTALL_EXTRAS" = true ] && install_extras

    # Final summary
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  Installation Complete!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
    echo ""

    if [ "$INSTALL_CORE" = true ]; then
        info "Component A (ukabu-core) installed: nginx PoW flow"
        echo "  - Config: $UKABU_ETC/includes/"
        echo "  - NJS: $UKABU_ETC/njs/"
        echo "  - Pages: $UKABU_ETC/pages/"
    fi

    if [ "$INSTALL_MONITOR" = true ]; then
        info "Component B (ukabu-monitor) installed: Go daemon"
        echo "  - Binary: /usr/local/bin/ukabu-trackerd"
        echo "  - Status: systemctl status ukabu-trackerd"
        echo "  - Logs: journalctl -u ukabu-trackerd -f"
    fi

    if [ "$INSTALL_MANAGER" = true ]; then
        info "Component C (ukabu-manager) installed: Python CLI"
        echo "  - CLI: ukabu-manager --help"
        echo "  - Library: $UKABU_LIB/"
    fi

    if [ "$INSTALL_EXTRAS" = true ]; then
        info "Component D (ukabu-extras) installed: Advanced features"
        echo "  - Scripts: $UKABU_BIN/ukabu-fetch-*"
        echo "  - Timers: systemctl list-timers | grep ukabu"
    fi

    echo ""
    info "Documentation:"
    echo "  • Configuration Guide: $SCRIPT_DIR/docs/DOMAINS-CONFIGURATION.md"
    echo "  • Full Documentation: $SCRIPT_DIR/docs/"
    echo "  • Examples: $SCRIPT_DIR/examples/"

    echo ""
    warn "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    warn "  IMPORTANT: Remove Test Domain Before Production"
    warn "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "  ⚠️  Test domain 'test.local' is configured for verification only."
    echo "     Remove it and add your actual domains before production use."
    echo ""
    echo "  Next Steps:"
    echo "  1. 📖 READ: $SCRIPT_DIR/docs/DOMAINS-CONFIGURATION.md"
    echo "  2. Remove test.local from $UKABU_ETC/config/domains.json"
    echo "  3. Add your actual domain(s)"
    echo "  4. Generate HMAC secrets for your domains"
    echo "  5. Configure nginx vhost (see examples/)"
    echo "  6. Test and reload: nginx -t && systemctl reload nginx"

    if [ "$INSTALL_MANAGER" = true ] || [ "$MANAGER_INSTALLED" = true ]; then
        echo ""
        info "💡 Quick start with ukabu-manager CLI:"
        echo "  ukabu-manager domain remove test.local"
        echo "  ukabu-manager domain add yourdomain.com --difficulty 18"
        echo "  ukabu-manager domain set-secret yourdomain.com"
        echo "  ukabu-manager nginx generate-config"
        echo "  ukabu-manager status"
    fi

    echo ""
    info "For complete documentation, see: $SCRIPT_DIR/docs/DOMAINS-CONFIGURATION.md"
}

# Run main installation
main "$@"
