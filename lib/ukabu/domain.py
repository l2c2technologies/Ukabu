#!/usr/bin/env python3
# Copyright (c) 2025 by L2C2 Technologies. All rights reserved.
# 
# For licensing inquiries, contact:
# Indranil Das Gupta <indradg@l2c2.co.in>

"""
Domain management for UKABU WAF
"""

import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

from .utils import (
    DOMAINS_CONFIG, UKABU_SECRETS_DIR,
    validate_domain, generate_hmac_secret,
    load_json_file, save_json_file,
    get_timestamp_iso, parse_iso_timestamp, is_secret_expired
)


class DomainManager:
    """Manager for domain configuration and secrets"""
    
    def __init__(self, dry_run: bool = False):
        """
        Initialize domain manager
        
        Args:
            dry_run: If True, don't actually modify files
        """
        self.dry_run = dry_run
        self.logger = logging.getLogger('ukabu-manager.domain')
        self.config_path = DOMAINS_CONFIG
        self.secrets_dir = UKABU_SECRETS_DIR
    
    def _load_config(self) -> Dict[str, Any]:
        """Load domains configuration"""
        return load_json_file(self.config_path, default={'domains': {}})
    
    def _save_config(self, config: Dict[str, Any]) -> None:
        """Save domains configuration"""
        if not self.dry_run:
            save_json_file(self.config_path, config, backup=True)
            self.logger.info(f"Saved configuration to {self.config_path}")
        else:
            self.logger.info(f"[DRY-RUN] Would save configuration to {self.config_path}")
    
    def _get_secret_path(self, domain: str, secret_type: str = 'current') -> Path:
        """Get path to secret file for domain"""
        return self.secrets_dir / f"{domain}.{secret_type}.key"
    
    def _load_secret(self, domain: str, secret_type: str = 'current') -> Optional[str]:
        """Load secret for domain"""
        secret_path = self._get_secret_path(domain, secret_type)
        if not secret_path.exists():
            return None
        
        try:
            with open(secret_path, 'r') as f:
                return f.read().strip()
        except Exception as e:
            self.logger.error(f"Failed to load secret for {domain}: {e}")
            return None
    
    def _save_secret(self, domain: str, secret: str, secret_type: str = 'current') -> None:
        """Save secret for domain"""
        if self.dry_run:
            self.logger.info(f"[DRY-RUN] Would save {secret_type} secret for {domain}")
            return
        
        secret_path = self._get_secret_path(domain, secret_type)
        self.secrets_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        
        try:
            with open(secret_path, 'w') as f:
                f.write(secret)
            # Restrict permissions (root only)
            secret_path.chmod(0o600)
            self.logger.info(f"Saved {secret_type} secret for {domain}")
        except Exception as e:
            raise RuntimeError(f"Failed to save secret for {domain}: {e}")
    
    def list_domains(self) -> List[str]:
        """
        List all configured domains
        
        Returns:
            List of domain names
        """
        config = self._load_config()
        return sorted(config.get('domains', {}).keys())
    
    def domain_exists(self, domain: str) -> bool:
        """
        Check if domain exists in configuration
        
        Args:
            domain: Domain name
        
        Returns:
            True if domain exists
        """
        config = self._load_config()
        return domain in config.get('domains', {})
    
    def get_domain_config(self, domain: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for specific domain
        
        Args:
            domain: Domain name
        
        Returns:
            Domain configuration dictionary or None
        """
        config = self._load_config()
        return config.get('domains', {}).get(domain)
    
    def add_domain(
        self,
        domain: str,
        difficulty: int = 18,
        cookie_duration: int = 604800,
        lockout_period: int = 10080,
        excuse_first_timeout: bool = False,
        hmac_secret: Optional[str] = None
    ) -> bool:
        """
        Add new domain to configuration (idempotent)
        
        Args:
            domain: Domain name
            difficulty: PoW difficulty (bits)
            cookie_duration: Cookie validity in seconds
            lockout_period: Lockout duration in minutes
            excuse_first_timeout: Excuse first timeout failure
            hmac_secret: Manual HMAC secret (None to auto-generate)
        
        Returns:
            True if domain was added, False if already exists
        """
        # Validate domain
        is_valid, error = validate_domain(domain)
        if not is_valid:
            raise ValueError(f"Invalid domain: {error}")
        
        # Check if already exists
        if self.domain_exists(domain):
            self.logger.info(f"Domain {domain} already exists, no changes made")
            return False
        
        # Generate or use provided secret
        if hmac_secret is None:
            hmac_secret = generate_hmac_secret(64)
        
        # Create domain configuration
        domain_config = {
            'pow_difficulty': difficulty,
            'cookie_duration': cookie_duration,
            'lockout_period': lockout_period,
            'excuse_first_timeout': excuse_first_timeout,
            'hmac_secret_file': str(self._get_secret_path(domain, 'current')),
            'exempt_paths': [],
            'restricted_paths': {},
            'created_at': get_timestamp_iso(),
            'updated_at': get_timestamp_iso()
        }
        
        # Save secret
        self._save_secret(domain, hmac_secret, 'current')
        
        # Update configuration
        config = self._load_config()
        if 'domains' not in config:
            config['domains'] = {}
        config['domains'][domain] = domain_config
        self._save_config(config)
        
        self.logger.info(f"Added domain: {domain}")
        return True
    
    def remove_domain(self, domain: str, force: bool = False) -> bool:
        """
        Remove domain from configuration
        
        Args:
            domain: Domain name
            force: Skip confirmation
        
        Returns:
            True if domain was removed
        """
        if not self.domain_exists(domain):
            self.logger.info(f"Domain {domain} does not exist, no changes made")
            return False
        
        # Load configuration
        config = self._load_config()
        del config['domains'][domain]
        self._save_config(config)
        
        # Remove secret files
        for secret_type in ['current', 'previous']:
            secret_path = self._get_secret_path(domain, secret_type)
            if secret_path.exists() and not self.dry_run:
                secret_path.unlink()
                self.logger.info(f"Removed {secret_type} secret for {domain}")
        
        self.logger.info(f"Removed domain: {domain}")
        return True
    
    def update_domain(
        self,
        domain: str,
        difficulty: Optional[int] = None,
        cookie_duration: Optional[int] = None,
        lockout_period: Optional[int] = None,
        excuse_first_timeout: Optional[bool] = None
    ) -> bool:
        """
        Update domain settings
        
        Args:
            domain: Domain name
            difficulty: New PoW difficulty (None to keep current)
            cookie_duration: New cookie duration (None to keep current)
            lockout_period: New lockout period (None to keep current)
            excuse_first_timeout: New excuse setting (None to keep current)
        
        Returns:
            True if domain was updated
        """
        if not self.domain_exists(domain):
            raise ValueError(f"Domain {domain} does not exist")
        
        config = self._load_config()
        domain_config = config['domains'][domain]
        
        # Update fields if provided
        if difficulty is not None:
            if difficulty < 1 or difficulty > 32:
                raise ValueError("Difficulty must be between 1 and 32 bits")
            domain_config['pow_difficulty'] = difficulty
        
        if cookie_duration is not None:
            if cookie_duration < 60:
                raise ValueError("Cookie duration must be at least 60 seconds")
            domain_config['cookie_duration'] = cookie_duration
        
        if lockout_period is not None:
            if lockout_period < 0:
                raise ValueError("Lockout period cannot be negative")
            domain_config['lockout_period'] = lockout_period
        
        if excuse_first_timeout is not None:
            domain_config['excuse_first_timeout'] = excuse_first_timeout
        
        # Update timestamp
        domain_config['updated_at'] = get_timestamp_iso()
        
        # Save configuration
        self._save_config(config)
        self.logger.info(f"Updated domain: {domain}")
        return True
    
    def rotate_secret(self, domain: str, new_secret: Optional[str] = None) -> bool:
        """
        Rotate HMAC secret for domain
        
        Args:
            domain: Domain name
            new_secret: New secret (None to auto-generate)
        
        Returns:
            True if secret was rotated
        """
        if not self.domain_exists(domain):
            raise ValueError(f"Domain {domain} does not exist")
        
        # Load current secret
        current_secret = self._load_secret(domain, 'current')
        if current_secret is None:
            raise RuntimeError(f"No current secret found for {domain}")
        
        # Generate new secret
        if new_secret is None:
            new_secret = generate_hmac_secret(64)
        
        # Move current to previous
        self._save_secret(domain, current_secret, 'previous')
        
        # Save new secret as current
        self._save_secret(domain, new_secret, 'current')
        
        # Update configuration with rotation timestamp
        config = self._load_config()
        domain_config = config['domains'][domain]
        domain_config['secret_rotated_at'] = get_timestamp_iso()
        domain_config['updated_at'] = get_timestamp_iso()
        self._save_config(config)
        
        self.logger.info(f"Rotated secret for domain: {domain}")
        self.logger.info("Previous secret will remain valid for 12 hours")
        return True
    
    def cleanup_expired_secrets(self) -> int:
        """
        Remove expired previous secrets (older than 12 hours)
        
        Returns:
            Number of expired secrets removed
        """
        config = self._load_config()
        removed = 0
        
        for domain in config.get('domains', {}).keys():
            domain_config = config['domains'][domain]
            rotation_time = domain_config.get('secret_rotated_at')
            
            if rotation_time and is_secret_expired(rotation_time, grace_hours=12):
                # Remove previous secret
                prev_secret_path = self._get_secret_path(domain, 'previous')
                if prev_secret_path.exists() and not self.dry_run:
                    prev_secret_path.unlink()
                    self.logger.info(f"Removed expired previous secret for {domain}")
                    removed += 1
                
                # Clear rotation timestamp
                del domain_config['secret_rotated_at']
        
        if removed > 0 and not self.dry_run:
            self._save_config(config)
        
        return removed
    
    def add_exempt_path(self, domain: str, path: str) -> bool:
        """
        Add exempt path for domain (idempotent)
        
        Args:
            domain: Domain name
            path: Path pattern (e.g., /health, /static/*)
        
        Returns:
            True if path was added
        """
        if not self.domain_exists(domain):
            raise ValueError(f"Domain {domain} does not exist")
        
        config = self._load_config()
        domain_config = config['domains'][domain]
        
        if 'exempt_paths' not in domain_config:
            domain_config['exempt_paths'] = []
        
        # Check if already exempt (idempotent)
        if path in domain_config['exempt_paths']:
            self.logger.info(f"Path {path} already exempt for {domain}, no changes made")
            return False
        
        domain_config['exempt_paths'].append(path)
        domain_config['updated_at'] = get_timestamp_iso()
        self._save_config(config)
        
        self.logger.info(f"Added exempt path {path} for domain: {domain}")
        return True
    
    def remove_exempt_path(self, domain: str, path: str) -> bool:
        """
        Remove exempt path for domain
        
        Args:
            domain: Domain name
            path: Path pattern
        
        Returns:
            True if path was removed
        """
        if not self.domain_exists(domain):
            raise ValueError(f"Domain {domain} does not exist")
        
        config = self._load_config()
        domain_config = config['domains'][domain]
        
        if path not in domain_config.get('exempt_paths', []):
            self.logger.info(f"Path {path} not exempt for {domain}, no changes made")
            return False
        
        domain_config['exempt_paths'].remove(path)
        domain_config['updated_at'] = get_timestamp_iso()
        self._save_config(config)
        
        self.logger.info(f"Removed exempt path {path} from domain: {domain}")
        return True
    
    def add_restricted_path(self, domain: str, path: str, allowed_ips: List[str]) -> bool:
        """
        Add restricted path with allowed IPs (idempotent)
        
        Args:
            domain: Domain name
            path: Path pattern
            allowed_ips: List of allowed IP addresses/ranges
        
        Returns:
            True if restriction was added or updated
        """
        if not self.domain_exists(domain):
            raise ValueError(f"Domain {domain} does not exist")
        
        config = self._load_config()
        domain_config = config['domains'][domain]
        
        if 'restricted_paths' not in domain_config:
            domain_config['restricted_paths'] = {}
        
        # Check if already exists with same IPs
        existing_ips = domain_config['restricted_paths'].get(path, [])
        if set(existing_ips) == set(allowed_ips):
            self.logger.info(f"Path {path} already restricted with same IPs for {domain}, no changes made")
            return False
        
        domain_config['restricted_paths'][path] = allowed_ips
        domain_config['updated_at'] = get_timestamp_iso()
        self._save_config(config)
        
        self.logger.info(f"Added/updated restricted path {path} for domain: {domain}")
        return True
    
    def remove_restricted_path(self, domain: str, path: str) -> bool:
        """
        Remove restricted path
        
        Args:
            domain: Domain name
            path: Path pattern
        
        Returns:
            True if restriction was removed
        """
        if not self.domain_exists(domain):
            raise ValueError(f"Domain {domain} does not exist")
        
        config = self._load_config()
        domain_config = config['domains'][domain]
        
        if path not in domain_config.get('restricted_paths', {}):
            self.logger.info(f"Path {path} not restricted for {domain}, no changes made")
            return False
        
        del domain_config['restricted_paths'][path]
        domain_config['updated_at'] = get_timestamp_iso()
        self._save_config(config)
        
        self.logger.info(f"Removed restricted path {path} from domain: {domain}")
        return True
