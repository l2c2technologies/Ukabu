# Copyright (c) 2025 by L2C2 Technologies. All rights reserved.
# 
# For licensing inquiries, contact:
# Indranil Das Gupta <indradg@l2c2.co.in>

"""
Path management module for UKABU WAF.
Handles exempt paths and restricted paths configuration.
"""

import json
from typing import List, Dict, Optional
from .utils import load_json, save_json, log_action, validate_ip_or_cidr

class PathManager:
    """Manages exempt and restricted paths for domains."""
    
    def __init__(self, config_path="/etc/ukabu/config/domains.json"):
        self.config_path = config_path
        self.config = load_json(config_path)
    
    def add_exempt(self, domain: str, path: str, dry_run: bool = False) -> bool:
        """
        Add an exempt path (bypasses PoW challenge).
        
        Args:
            domain: Domain name
            path: Path pattern (e.g., /static/*, /favicon.ico)
            dry_run: If True, only show what would be done
        
        Returns:
            True if successful or no-op (idempotent)
        """
        if domain not in self.config['domains']:
            print(f"Error: Domain {domain} not found")
            return False
        
        domain_config = self.config['domains'][domain]
        
        # Initialize exempt_paths if not present
        if 'exempt_paths' not in domain_config:
            domain_config['exempt_paths'] = []
        
        exempt_paths = domain_config['exempt_paths']
        
        # Check if already added (idempotent)
        if path in exempt_paths:
            print(f"Path {path} already exempt for {domain}, no changes made")
            return True
        
        if dry_run:
            print(f"[DRY RUN] Would add exempt path {path} to {domain}")
            return True
        
        exempt_paths.append(path)
        domain_config['exempt_paths'] = exempt_paths
        
        save_json(self.config_path, self.config)
        
        log_action(f"Added exempt path {path} to {domain}")
        print(f"âœ“ Added exempt path {path} to {domain}")
        print(f"\nRemember to:")
        print(f"  1. Regenerate nginx config: ukabu-manager nginx generate-config -d {domain}")
        print(f"  2. Reload nginx: ukabu-manager nginx reload")
        
        return True
    
    def remove_exempt(self, domain: str, path: str, dry_run: bool = False) -> bool:
        """
        Remove an exempt path.
        
        Args:
            domain: Domain name
            path: Path pattern
            dry_run: If True, only show what would be done
        
        Returns:
            True if successful or no-op (idempotent)
        """
        if domain not in self.config['domains']:
            print(f"Error: Domain {domain} not found")
            return False
        
        domain_config = self.config['domains'][domain]
        exempt_paths = domain_config.get('exempt_paths', [])
        
        if path not in exempt_paths:
            print(f"Path {path} not found in exempt paths for {domain}, nothing to remove")
            return True
        
        if dry_run:
            print(f"[DRY RUN] Would remove exempt path {path} from {domain}")
            return True
        
        exempt_paths.remove(path)
        domain_config['exempt_paths'] = exempt_paths
        
        save_json(self.config_path, self.config)
        
        log_action(f"Removed exempt path {path} from {domain}")
        print(f"âœ“ Removed exempt path {path} from {domain}")
        
        return True
    
    def list_exempt(self, domain: str) -> bool:
        """
        List all exempt paths for a domain.
        
        Args:
            domain: Domain name
        
        Returns:
            True if successful
        """
        if domain not in self.config['domains']:
            print(f"Error: Domain {domain} not found")
            return False
        
        domain_config = self.config['domains'][domain]
        exempt_paths = domain_config.get('exempt_paths', [])
        
        if not exempt_paths:
            print(f"No exempt paths configured for {domain}")
            return True
        
        print(f"\nExempt Paths for {domain} ({len(exempt_paths)}):")
        print("=" * 60)
        for path in exempt_paths:
            print(f"  â€¢ {path}")
        print("")
        
        return True
    
    def add_restricted(self, domain: str, path: str, allowed_ip: str, dry_run: bool = False) -> bool:
        """
        Add a restricted path with allowed IP.
        
        Args:
            domain: Domain name
            path: Path pattern (e.g., /admin/*)
            allowed_ip: IP address or CIDR range
            dry_run: If True, only show what would be done
        
        Returns:
            True if successful or no-op (idempotent)
        """
        if domain not in self.config['domains']:
            print(f"Error: Domain {domain} not found")
            return False
        
        # Validate IP/CIDR
        if not validate_ip_or_cidr(allowed_ip):
            print(f"Error: Invalid IP or CIDR: {allowed_ip}")
            return False
        
        domain_config = self.config['domains'][domain]
        
        # Initialize restricted_paths if not present
        if 'restricted_paths' not in domain_config:
            domain_config['restricted_paths'] = {}
        
        restricted_paths = domain_config['restricted_paths']
        
        # Initialize path if not present
        if path not in restricted_paths:
            restricted_paths[path] = []
        
        # Check if IP already added (idempotent)
        if allowed_ip in restricted_paths[path]:
            print(f"IP {allowed_ip} already allowed for path {path} on {domain}, no changes made")
            return True
        
        if dry_run:
            print(f"[DRY RUN] Would add allowed IP {allowed_ip} to restricted path {path} on {domain}")
            return True
        
        restricted_paths[path].append(allowed_ip)
        domain_config['restricted_paths'] = restricted_paths
        
        save_json(self.config_path, self.config)
        
        log_action(f"Added allowed IP {allowed_ip} to restricted path {path} on {domain}")
        print(f"âœ“ Added allowed IP {allowed_ip} to restricted path {path}")
        print(f"\nRemember to:")
        print(f"  1. Regenerate nginx config: ukabu-manager nginx generate-config -d {domain}")
        print(f"  2. Reload nginx: ukabu-manager nginx reload")
        
        return True
    
    def remove_restricted_ip(self, domain: str, path: str, allowed_ip: str, dry_run: bool = False) -> bool:
        """
        Remove an allowed IP from a restricted path.
        
        Args:
            domain: Domain name
            path: Path pattern
            allowed_ip: IP address or CIDR range
            dry_run: If True, only show what would be done
        
        Returns:
            True if successful or no-op (idempotent)
        """
        if domain not in self.config['domains']:
            print(f"Error: Domain {domain} not found")
            return False
        
        domain_config = self.config['domains'][domain]
        restricted_paths = domain_config.get('restricted_paths', {})
        
        if path not in restricted_paths:
            print(f"Path {path} not found in restricted paths for {domain}, nothing to remove")
            return True
        
        if allowed_ip not in restricted_paths[path]:
            print(f"IP {allowed_ip} not found in restricted path {path}, nothing to remove")
            return True
        
        if dry_run:
            print(f"[DRY RUN] Would remove allowed IP {allowed_ip} from restricted path {path} on {domain}")
            return True
        
        restricted_paths[path].remove(allowed_ip)
        
        # Remove path if no more allowed IPs
        if not restricted_paths[path]:
            del restricted_paths[path]
        
        domain_config['restricted_paths'] = restricted_paths
        
        save_json(self.config_path, self.config)
        
        log_action(f"Removed allowed IP {allowed_ip} from restricted path {path} on {domain}")
        print(f"âœ“ Removed allowed IP {allowed_ip} from restricted path {path}")
        
        return True
    
    def remove_restricted(self, domain: str, path: str, dry_run: bool = False) -> bool:
        """
        Remove an entire restricted path (all allowed IPs).
        
        Args:
            domain: Domain name
            path: Path pattern
            dry_run: If True, only show what would be done
        
        Returns:
            True if successful or no-op (idempotent)
        """
        if domain not in self.config['domains']:
            print(f"Error: Domain {domain} not found")
            return False
        
        domain_config = self.config['domains'][domain]
        restricted_paths = domain_config.get('restricted_paths', {})
        
        if path not in restricted_paths:
            print(f"Path {path} not found in restricted paths for {domain}, nothing to remove")
            return True
        
        if dry_run:
            print(f"[DRY RUN] Would remove restricted path {path} from {domain}")
            return True
        
        del restricted_paths[path]
        domain_config['restricted_paths'] = restricted_paths
        
        save_json(self.config_path, self.config)
        
        log_action(f"Removed restricted path {path} from {domain}")
        print(f"âœ“ Removed restricted path {path} from {domain}")
        
        return True
    
    def list_restricted(self, domain: str) -> bool:
        """
        List all restricted paths for a domain.
        
        Args:
            domain: Domain name
        
        Returns:
            True if successful
        """
        if domain not in self.config['domains']:
            print(f"Error: Domain {domain} not found")
            return False
        
        domain_config = self.config['domains'][domain]
        restricted_paths = domain_config.get('restricted_paths', {})
        
        if not restricted_paths:
            print(f"No restricted paths configured for {domain}")
            return True
        
        print(f"\nRestricted Paths for {domain} ({len(restricted_paths)}):")
        print("=" * 60)
        for path, allowed_ips in restricted_paths.items():
            print(f"\nâ€¢ {path}")
            print(f"  Allowed IPs ({len(allowed_ips)}):")
            for ip in allowed_ips:
                print(f"    - {ip}")
        print("")
        
        return True
