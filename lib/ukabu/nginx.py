#!/usr/bin/env python3
# Copyright (c) 2025 by L2C2 Technologies. All rights reserved.
# 
# For licensing inquiries, contact:
# Indranil Das Gupta <indradg@l2c2.co.in>

"""
nginx configuration generation and management for UKABU WAF
"""

import subprocess
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from jinja2 import Template

from .utils import (
    DOMAINS_CONFIG, UKABU_INCLUDES_DIR,
    load_json_file
)


class NginxManager:
    """Manager for nginx configuration generation and testing"""
    
    def __init__(self, dry_run: bool = False):
        """
        Initialize nginx manager
        
        Args:
            dry_run: If True, don't actually modify files or reload nginx
        """
        self.dry_run = dry_run
        self.logger = logging.getLogger('ukabu-manager.nginx')
        self.includes_dir = UKABU_INCLUDES_DIR / "domains"
        self.config_path = DOMAINS_CONFIG
    
    def _load_domains_config(self) -> Dict[str, Any]:
        """Load domains configuration"""
        return load_json_file(self.config_path, default={'domains': {}})
    
    def test_config(self) -> bool:
        """
        Test nginx configuration syntax
        
        Returns:
            True if config is valid
        
        Raises:
            RuntimeError: If config test fails
        """
        try:
            result = subprocess.run(
                ['nginx', '-t'],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                self.logger.info("nginx configuration test passed")
                return True
            else:
                error_msg = result.stderr or result.stdout
                raise RuntimeError(f"nginx configuration test failed:\n{error_msg}")
        
        except FileNotFoundError:
            raise RuntimeError("nginx command not found - is nginx installed?")
    
    def reload(self, force: bool = False) -> bool:
        """
        Reload nginx configuration
        
        Args:
            force: Skip confirmation
        
        Returns:
            True if reload successful
        
        Raises:
            RuntimeError: If reload fails
        """
        if self.dry_run:
            self.logger.info("[DRY-RUN] Would reload nginx configuration")
            return True
        
        # Test config first
        if not force:
            self.test_config()
        
        try:
            result = subprocess.run(
                ['systemctl', 'reload', 'nginx'],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                self.logger.info("nginx configuration reloaded successfully")
                return True
            else:
                error_msg = result.stderr or result.stdout
                raise RuntimeError(f"nginx reload failed:\n{error_msg}")
        
        except FileNotFoundError:
            raise RuntimeError("systemctl command not found")
    
    def generate_domain_config(self, domain: str) -> str:
        """
        Generate nginx configuration snippet for domain
        
        Args:
            domain: Domain name
        
        Returns:
            Generated configuration as string
        """
        config = self._load_domains_config()
        domain_config = config.get('domains', {}).get(domain)
        
        if not domain_config:
            raise ValueError(f"Domain {domain} not found in configuration")
        
        # Template for domain-specific nginx config
        template_str = '''# Copyright (c) 2025 by L2C2 Technologies. All rights reserved.
# UKABU WAF configuration for {{ domain }}
# Generated automatically - do not edit manually

# Domain-specific variables
set $pow_protected 1;
set $pow_difficulty {{ difficulty }};
set $pow_cookie_duration {{ cookie_duration }};
set $pow_lockout_period {{ lockout_period }};
set $pow_excuse_first_timeout {{ excuse_first_timeout }};

# HMAC secret (load from file)
set_by_lua_block $pow_hmac_secret {
    local file = io.open("{{ secret_file }}", "r")
    if file then
        local secret = file:read("*all")
        file:close()
        return secret:gsub("%s+", "")
    end
    return ""
}

# Exempt paths (bypass PoW)
{% if exempt_paths %}
map $request_uri $is_path_whitelisted {
    default 0;
{% for path in exempt_paths %}
    {{ path }} 1;
{% endfor %}
}
{% endif %}

# Restricted paths (IP-based access)
{% if restricted_paths %}
{% for path, ips in restricted_paths.items() %}
# Path: {{ path }}
geo $restricted_{{ loop.index }} {
    default 0;
{% for ip in ips %}
    {{ ip }} 1;
{% endfor %}
}
{% endfor %}

map $request_uri $is_restricted_path {
    default 0;
{% for path in restricted_paths.keys() %}
    {{ path }} $restricted_{{ loop.index }};
{% endfor %}
}
{% endif %}
'''
        
        template = Template(template_str)
        
        # Render template
        config_output = template.render(
            domain=domain,
            difficulty=domain_config.get('pow_difficulty', 18),
            cookie_duration=domain_config.get('cookie_duration', 604800),
            lockout_period=domain_config.get('lockout_period', 10080),
            excuse_first_timeout=1 if domain_config.get('excuse_first_timeout', False) else 0,
            secret_file=domain_config.get('hmac_secret_file', ''),
            exempt_paths=domain_config.get('exempt_paths', []),
            restricted_paths=domain_config.get('restricted_paths', {})
        )
        
        return config_output
    
    def save_domain_config(self, domain: str, backup: bool = True) -> Path:
        """
        Generate and save nginx configuration for domain
        
        Args:
            domain: Domain name
            backup: Create backup of existing config
        
        Returns:
            Path to saved config file
        """
        # Generate config
        config_content = self.generate_domain_config(domain)
        
        # Create includes directory
        self.includes_dir.mkdir(parents=True, exist_ok=True, mode=0o755)
        
        # Output path
        config_file = self.includes_dir / f"{domain}.conf"
        
        if self.dry_run:
            self.logger.info(f"[DRY-RUN] Would save config to {config_file}")
            return config_file
        
        # Backup existing config
        if backup and config_file.exists():
            backup_file = config_file.with_suffix('.conf.bak')
            config_file.rename(backup_file)
            self.logger.info(f"Backed up existing config to {backup_file}")
        
        # Write config
        with open(config_file, 'w') as f:
            f.write(config_content)
        
        config_file.chmod(0o644)
        self.logger.info(f"Saved nginx config for {domain} to {config_file}")
        
        return config_file
    
    def remove_domain_config(self, domain: str) -> bool:
        """
        Remove nginx configuration for domain
        
        Args:
            domain: Domain name
        
        Returns:
            True if config was removed
        """
        config_file = self.includes_dir / f"{domain}.conf"
        
        if not config_file.exists():
            self.logger.info(f"Config file for {domain} does not exist, no changes made")
            return False
        
        if self.dry_run:
            self.logger.info(f"[DRY-RUN] Would remove {config_file}")
            return True
        
        # Backup before removing
        backup_file = config_file.with_suffix('.conf.removed')
        config_file.rename(backup_file)
        self.logger.info(f"Removed nginx config for {domain} (backed up to {backup_file})")
        
        return True
    
    def generate_all_configs(self) -> List[Path]:
        """
        Generate nginx configurations for all domains
        
        Returns:
            List of paths to generated config files
        """
        config = self._load_domains_config()
        domains = config.get('domains', {}).keys()
        
        generated_files = []
        for domain in domains:
            try:
                config_file = self.save_domain_config(domain, backup=True)
                generated_files.append(config_file)
            except Exception as e:
                self.logger.error(f"Failed to generate config for {domain}: {e}")
        
        self.logger.info(f"Generated {len(generated_files)} domain configuration(s)")
        return generated_files
    
    def get_vhost_template(self, domain: str, upstream: str = "http://localhost:8080") -> str:
        """
        Generate example vhost configuration with UKABU integration
        
        Args:
            domain: Domain name
            upstream: Upstream server address
        
        Returns:
            Example vhost configuration
        """
        template_str = '''# Copyright (c) 2025 by L2C2 Technologies. All rights reserved.
# Example vhost configuration for {{ domain }} with UKABU WAF

upstream {{ domain }}_backend {
    server {{ upstream }};
}

server {
    listen 80;
    server_name {{ domain }};
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name {{ domain }};
    
    # SSL configuration
    ssl_certificate /etc/ssl/certs/{{ domain }}.crt;
    ssl_certificate_key /etc/ssl/private/{{ domain }}.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    # UKABU WAF includes
    include /etc/ukabu/includes/config.conf;
    include /etc/ukabu/includes/domains/{{ domain }}.conf;
    include /etc/ukabu/includes/endpoints.inc;
    include /etc/ukabu/includes/enforcement.inc;
    
    # Proxy configuration
    location / {
        proxy_pass {{ upstream }};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
'''
        
        template = Template(template_str)
        return template.render(domain=domain, upstream=upstream)
    
    def validate_configuration(self) -> Dict[str, Any]:
        """
        Validate current nginx and UKABU configuration
        
        Returns:
            Dictionary with validation results
        """
        results = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Check if nginx is installed
        try:
            subprocess.run(['nginx', '-v'], capture_output=True, check=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            results['valid'] = False
            results['errors'].append("nginx is not installed or not in PATH")
            return results
        
        # Test nginx config
        try:
            self.test_config()
        except RuntimeError as e:
            results['valid'] = False
            results['errors'].append(str(e))
        
        # Check if domain configs exist
        config = self._load_domains_config()
        domains = config.get('domains', {}).keys()
        
        for domain in domains:
            config_file = self.includes_dir / f"{domain}.conf"
            if not config_file.exists():
                results['warnings'].append(
                    f"nginx config file missing for domain {domain} "
                    f"(run 'ukabu-manager nginx generate-config')"
                )
        
        # Check UKABU includes
        required_includes = [
            UKABU_INCLUDES_DIR / 'config.conf',
            UKABU_INCLUDES_DIR / 'endpoints.inc',
            UKABU_INCLUDES_DIR / 'enforcement.inc'
        ]
        
        for include_file in required_includes:
            if not include_file.exists():
                results['valid'] = False
                results['errors'].append(f"Required include file missing: {include_file}")
        
        return results
