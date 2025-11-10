# Copyright (c) 2025 by L2C2 Technologies. All rights reserved.
# 
# For licensing inquiries, contact:
# Indranil Das Gupta <indradg@l2c2.co.in>

"""
X-Forwarded-For (XFF) management module for UKABU WAF.
Handles per-domain XFF configuration and trusted proxy management.
"""

import json
import os
import ipaddress
from typing import List, Dict, Optional
from .utils import load_json, save_json, log_action, validate_ip_or_cidr

class XFFManager:
    """Manages X-Forwarded-For configuration for domains."""
    
    def __init__(self, config_path="/etc/ukabu/config/domains.json"):
        self.config_path = config_path
        self.config = load_json(config_path)
    
    def enable(self, domain: str, sources: Optional[List[str]] = None, dry_run: bool = False) -> bool:
        """
        Enable XFF handling for a domain.
        
        Args:
            domain: Domain name
            sources: List of CDN sources (cloudflare, aws, google, digitalocean)
            dry_run: If True, only show what would be done
        
        Returns:
            True if successful or no-op (idempotent)
        """
        if domain not in self.config['domains']:
            print(f"Error: Domain {domain} not found")
            return False
        
        domain_config = self.config['domains'][domain]
        
        # Initialize xff_handling if not present
        if 'xff_handling' not in domain_config:
            domain_config['xff_handling'] = {
                'enabled': False,
                'trusted_proxy_sources': [],
                'custom_proxies': []
            }
        
        xff = domain_config['xff_handling']
        
        # Check if already enabled with same sources
        if xff.get('enabled') == True:
            if sources is None or set(sources) == set(xff.get('trusted_proxy_sources', [])):
                print(f"XFF already enabled for {domain}, no changes made")
                return True
        
        if dry_run:
            print(f"[DRY RUN] Would enable XFF for {domain}")
            if sources:
                print(f"[DRY RUN] Would set trusted sources: {', '.join(sources)}")
            return True
        
        # Enable XFF
        xff['enabled'] = True
        
        # Set sources if provided
        if sources:
            valid_sources = ['cloudflare', 'aws', 'google', 'digitalocean']
            for source in sources:
                if source not in valid_sources:
                    print(f"Warning: Invalid source '{source}', valid: {', '.join(valid_sources)}")
            xff['trusted_proxy_sources'] = [s for s in sources if s in valid_sources]
        elif not xff.get('trusted_proxy_sources'):
            # Default to all sources if none specified
            xff['trusted_proxy_sources'] = ['cloudflare', 'aws', 'google', 'digitalocean']
        
        # Save configuration
        save_json(self.config_path, self.config)
        
        log_action(f"Enabled XFF for {domain} with sources: {', '.join(xff['trusted_proxy_sources'])}")
        print(f"âœ“ XFF enabled for {domain}")
        print(f"  Trusted sources: {', '.join(xff['trusted_proxy_sources'])}")
        print(f"\nRemember to:")
        print(f"  1. Regenerate nginx config: ukabu-manager nginx generate-config -d {domain}")
        print(f"  2. Reload nginx: ukabu-manager nginx reload")
        
        return True
    
    def disable(self, domain: str, dry_run: bool = False) -> bool:
        """
        Disable XFF handling for a domain.
        
        Args:
            domain: Domain name
            dry_run: If True, only show what would be done
        
        Returns:
            True if successful or no-op (idempotent)
        """
        if domain not in self.config['domains']:
            print(f"Error: Domain {domain} not found")
            return False
        
        domain_config = self.config['domains'][domain]
        
        if 'xff_handling' not in domain_config or not domain_config['xff_handling'].get('enabled'):
            print(f"XFF already disabled for {domain}, no changes made")
            return True
        
        if dry_run:
            print(f"[DRY RUN] Would disable XFF for {domain}")
            return True
        
        domain_config['xff_handling']['enabled'] = False
        
        save_json(self.config_path, self.config)
        
        log_action(f"Disabled XFF for {domain}")
        print(f"âœ“ XFF disabled for {domain}")
        print(f"\nRemember to:")
        print(f"  1. Regenerate nginx config: ukabu-manager nginx generate-config -d {domain}")
        print(f"  2. Reload nginx: ukabu-manager nginx reload")
        
        return True
    
    def add_custom_proxy(self, domain: str, ip_or_cidr: str, dry_run: bool = False) -> bool:
        """
        Add a custom trusted proxy IP/CIDR.
        
        Args:
            domain: Domain name
            ip_or_cidr: IP address or CIDR range
            dry_run: If True, only show what would be done
        
        Returns:
            True if successful or no-op (idempotent)
        """
        if domain not in self.config['domains']:
            print(f"Error: Domain {domain} not found")
            return False
        
        # Validate IP/CIDR
        if not validate_ip_or_cidr(ip_or_cidr):
            print(f"Error: Invalid IP or CIDR: {ip_or_cidr}")
            return False
        
        domain_config = self.config['domains'][domain]
        
        # Initialize xff_handling if not present
        if 'xff_handling' not in domain_config:
            domain_config['xff_handling'] = {
                'enabled': False,
                'trusted_proxy_sources': [],
                'custom_proxies': []
            }
        
        custom_proxies = domain_config['xff_handling'].get('custom_proxies', [])
        
        # Check if already added (idempotent)
        if ip_or_cidr in custom_proxies:
            print(f"Proxy {ip_or_cidr} already added to {domain}, no changes made")
            return True
        
        if dry_run:
            print(f"[DRY RUN] Would add custom proxy {ip_or_cidr} to {domain}")
            return True
        
        custom_proxies.append(ip_or_cidr)
        domain_config['xff_handling']['custom_proxies'] = custom_proxies
        
        save_json(self.config_path, self.config)
        
        log_action(f"Added custom proxy {ip_or_cidr} to {domain}")
        print(f"âœ“ Added custom proxy {ip_or_cidr} to {domain}")
        print(f"\nRemember to:")
        print(f"  1. Update custom proxies file: ukabu-manager nginx generate-config -d {domain}")
        print(f"  2. Reload nginx: ukabu-manager nginx reload")
        
        return True
    
    def remove_custom_proxy(self, domain: str, ip_or_cidr: str, dry_run: bool = False) -> bool:
        """
        Remove a custom trusted proxy IP/CIDR.
        
        Args:
            domain: Domain name
            ip_or_cidr: IP address or CIDR range
            dry_run: If True, only show what would be done
        
        Returns:
            True if successful or no-op (idempotent)
        """
        if domain not in self.config['domains']:
            print(f"Error: Domain {domain} not found")
            return False
        
        domain_config = self.config['domains'][domain]
        
        if 'xff_handling' not in domain_config:
            print(f"No custom proxies configured for {domain}")
            return True
        
        custom_proxies = domain_config['xff_handling'].get('custom_proxies', [])
        
        if ip_or_cidr not in custom_proxies:
            print(f"Proxy {ip_or_cidr} not found in {domain}, nothing to remove")
            return True
        
        if dry_run:
            print(f"[DRY RUN] Would remove custom proxy {ip_or_cidr} from {domain}")
            return True
        
        custom_proxies.remove(ip_or_cidr)
        domain_config['xff_handling']['custom_proxies'] = custom_proxies
        
        save_json(self.config_path, self.config)
        
        log_action(f"Removed custom proxy {ip_or_cidr} from {domain}")
        print(f"âœ“ Removed custom proxy {ip_or_cidr} from {domain}")
        
        return True
    
    def show(self, domain: str) -> bool:
        """
        Show XFF configuration for a domain.
        
        Args:
            domain: Domain name
        
        Returns:
            True if successful
        """
        if domain not in self.config['domains']:
            print(f"Error: Domain {domain} not found")
            return False
        
        domain_config = self.config['domains'][domain]
        xff = domain_config.get('xff_handling', {})
        
        print(f"\nXFF Configuration for {domain}")
        print("=" * 60)
        print(f"Enabled: {xff.get('enabled', False)}")
        
        if xff.get('enabled'):
            sources = xff.get('trusted_proxy_sources', [])
            print(f"Trusted CDN Sources ({len(sources)}):")
            for source in sources:
                print(f"  â€¢ {source}")
            
            custom = xff.get('custom_proxies', [])
            if custom:
                print(f"\nCustom Trusted Proxies ({len(custom)}):")
                for proxy in custom:
                    print(f"  â€¢ {proxy}")
            else:
                print(f"\nCustom Trusted Proxies: None")
        else:
            print("  (XFF disabled - using $remote_addr directly)")
        
        print("")
        return True
    
    def list_enabled(self) -> bool:
        """
        List all domains with XFF enabled.
        
        Returns:
            True if successful
        """
        enabled_domains = []
        
        for domain, config in self.config['domains'].items():
            xff = config.get('xff_handling', {})
            if xff.get('enabled'):
                enabled_domains.append((domain, xff))
        
        if not enabled_domains:
            print("No domains with XFF enabled")
            return True
        
        print(f"\nDomains with XFF Enabled ({len(enabled_domains)}):")
        print("=" * 60)
        
        for domain, xff in enabled_domains:
            sources = xff.get('trusted_proxy_sources', [])
            custom = xff.get('custom_proxies', [])
            print(f"\nâ€¢ {domain}")
            print(f"  CDN Sources: {', '.join(sources) if sources else 'None'}")
            if custom:
                print(f"  Custom Proxies: {len(custom)}")
        
        print("")
        return True
