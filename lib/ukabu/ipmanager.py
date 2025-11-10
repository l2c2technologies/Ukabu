#!/usr/bin/env python3
# Copyright (c) 2025 by L2C2 Technologies. All rights reserved.
# 
# For licensing inquiries, contact:
# Indranil Das Gupta <indradg@l2c2.co.in>

"""
IP whitelist and blacklist management for UKABU WAF
"""

import json
import logging
from typing import List, Dict, Optional, Any
from pathlib import Path

from .utils import (
    IP_WHITELIST, IP_BLACKLIST,
    validate_ip, get_timestamp_iso,
    load_line_file, save_line_file
)


class IPManager:
    """Manager for IP whitelist and blacklist"""
    
    def __init__(self, dry_run: bool = False):
        """
        Initialize IP manager
        
        Args:
            dry_run: If True, don't actually modify files
        """
        self.dry_run = dry_run
        self.logger = logging.getLogger('ukabu-manager.ip')
        self.whitelist_path = IP_WHITELIST
        self.blacklist_path = IP_BLACKLIST
    
    # Whitelist management
    
    def get_whitelist(self) -> List[str]:
        """
        Get list of whitelisted IPs
        
        Returns:
            List of IP addresses/ranges
        """
        return load_line_file(self.whitelist_path)
    
    def add_to_whitelist(self, ip_address: str) -> bool:
        """
        Add IP to whitelist (idempotent)
        
        Args:
            ip_address: IP address or CIDR range
        
        Returns:
            True if IP was added, False if already exists
        """
        # Validate IP
        is_valid, error = validate_ip(ip_address)
        if not is_valid:
            raise ValueError(f"Invalid IP address: {error}")
        
        # Load current whitelist
        whitelist = self.get_whitelist()
        
        # Check if already whitelisted (idempotent)
        if ip_address in whitelist:
            self.logger.info(f"IP {ip_address} already whitelisted, no changes made")
            return False
        
        # Add to whitelist
        whitelist.append(ip_address)
        
        if not self.dry_run:
            save_line_file(self.whitelist_path, whitelist, backup=True)
            self.logger.info(f"Added {ip_address} to whitelist")
        else:
            self.logger.info(f"[DRY-RUN] Would add {ip_address} to whitelist")
        
        return True
    
    def remove_from_whitelist(self, ip_address: str) -> bool:
        """
        Remove IP from whitelist
        
        Args:
            ip_address: IP address or CIDR range
        
        Returns:
            True if IP was removed, False if not found
        """
        whitelist = self.get_whitelist()
        
        if ip_address not in whitelist:
            self.logger.info(f"IP {ip_address} not in whitelist, no changes made")
            return False
        
        whitelist.remove(ip_address)
        
        if not self.dry_run:
            save_line_file(self.whitelist_path, whitelist, backup=True)
            self.logger.info(f"Removed {ip_address} from whitelist")
        else:
            self.logger.info(f"[DRY-RUN] Would remove {ip_address} from whitelist")
        
        return True
    
    def flush_whitelist(self, force: bool = False) -> int:
        """
        Remove all IPs from whitelist
        
        Args:
            force: Skip confirmation
        
        Returns:
            Number of IPs removed
        """
        whitelist = self.get_whitelist()
        count = len(whitelist)
        
        if count == 0:
            self.logger.info("Whitelist is already empty, no changes made")
            return 0
        
        if not self.dry_run:
            save_line_file(self.whitelist_path, [], backup=True)
            self.logger.info(f"Flushed {count} IPs from whitelist")
        else:
            self.logger.info(f"[DRY-RUN] Would flush {count} IPs from whitelist")
        
        return count
    
    # Blacklist management
    
    def _load_blacklist(self) -> List[Dict[str, Any]]:
        """
        Load blacklist entries from file
        
        Returns:
            List of blacklist entry dictionaries
        """
        if not self.blacklist_path.exists():
            return []
        
        entries = []
        try:
            with open(self.blacklist_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        try:
                            entry = json.loads(line)
                            entries.append(entry)
                        except json.JSONDecodeError:
                            self.logger.warning(f"Skipping invalid JSON in blacklist: {line}")
        except PermissionError:
            raise PermissionError(f"Cannot read {self.blacklist_path} - insufficient permissions")
        
        return entries
    
    def _save_blacklist(self, entries: List[Dict[str, Any]]) -> None:
        """
        Save blacklist entries to file
        
        Args:
            entries: List of blacklist entry dictionaries
        """
        if self.dry_run:
            self.logger.info(f"[DRY-RUN] Would save {len(entries)} entries to blacklist")
            return
        
        # Create parent directory if needed
        self.blacklist_path.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
        
        # Backup existing file
        if self.blacklist_path.exists():
            backup_path = self.blacklist_path.with_suffix(self.blacklist_path.suffix + '.bak')
            self.blacklist_path.rename(backup_path)
        
        # Write entries as JSONL (JSON Lines)
        try:
            with open(self.blacklist_path, 'w') as f:
                for entry in entries:
                    json.dump(entry, f)
                    f.write('\n')
            
            # Set permissions
            self.blacklist_path.chmod(0o644)
            self.logger.info(f"Saved {len(entries)} entries to blacklist")
        except Exception as e:
            raise RuntimeError(f"Failed to save blacklist: {e}")
    
    def get_blacklist(self) -> List[Dict[str, Any]]:
        """
        Get list of blacklisted IPs
        
        Returns:
            List of blacklist entry dictionaries
        """
        return self._load_blacklist()
    
    def is_blacklisted(self, ip_address: str) -> bool:
        """
        Check if IP is blacklisted
        
        Args:
            ip_address: IP address to check
        
        Returns:
            True if IP is blacklisted
        """
        blacklist = self._load_blacklist()
        return any(entry['ip_address'] == ip_address for entry in blacklist)
    
    def add_to_blacklist(
        self,
        ip_address: str,
        duration: int = 0,
        reason: str = ""
    ) -> bool:
        """
        Add IP to blacklist (idempotent)
        
        Args:
            ip_address: IP address or CIDR range
            duration: Lockout duration in minutes (0 for permanent)
            reason: Reason for blacklisting
        
        Returns:
            True if IP was added, False if already exists
        """
        # Validate IP
        is_valid, error = validate_ip(ip_address)
        if not is_valid:
            raise ValueError(f"Invalid IP address: {error}")
        
        # Load current blacklist
        blacklist = self._load_blacklist()
        
        # Check if already blacklisted (idempotent)
        if self.is_blacklisted(ip_address):
            self.logger.info(f"IP {ip_address} already blacklisted, no changes made")
            return False
        
        # Create blacklist entry
        entry = {
            'ip_address': ip_address,
            'timestamp': get_timestamp_iso(),
            'lockout_period': duration,
            'reason': reason
        }
        
        blacklist.append(entry)
        self._save_blacklist(blacklist)
        
        if duration == 0:
            self.logger.info(f"Added {ip_address} to permanent blacklist")
        else:
            self.logger.info(f"Added {ip_address} to blacklist for {duration} minutes")
        
        return True
    
    def remove_from_blacklist(self, ip_address: str) -> bool:
        """
        Remove IP from blacklist
        
        Args:
            ip_address: IP address or CIDR range
        
        Returns:
            True if IP was removed, False if not found
        """
        blacklist = self._load_blacklist()
        
        # Find matching entry
        matching_entries = [e for e in blacklist if e['ip_address'] == ip_address]
        if not matching_entries:
            self.logger.info(f"IP {ip_address} not in blacklist, no changes made")
            return False
        
        # Remove all matching entries
        blacklist = [e for e in blacklist if e['ip_address'] != ip_address]
        self._save_blacklist(blacklist)
        
        self.logger.info(f"Removed {ip_address} from blacklist")
        return True
    
    def update_blacklist_entry(
        self,
        ip_address: str,
        duration: Optional[int] = None,
        reason: Optional[str] = None
    ) -> bool:
        """
        Update existing blacklist entry
        
        Args:
            ip_address: IP address
            duration: New lockout duration (None to keep current)
            reason: New reason (None to keep current)
        
        Returns:
            True if entry was updated
        """
        blacklist = self._load_blacklist()
        
        # Find matching entry
        entry_index = None
        for i, entry in enumerate(blacklist):
            if entry['ip_address'] == ip_address:
                entry_index = i
                break
        
        if entry_index is None:
            raise ValueError(f"IP {ip_address} not found in blacklist")
        
        # Update entry
        entry = blacklist[entry_index]
        if duration is not None:
            entry['lockout_period'] = duration
        if reason is not None:
            entry['reason'] = reason
        entry['updated_at'] = get_timestamp_iso()
        
        self._save_blacklist(blacklist)
        self.logger.info(f"Updated blacklist entry for {ip_address}")
        return True
    
    def flush_blacklist(self, force: bool = False) -> int:
        """
        Remove all IPs from blacklist
        
        Args:
            force: Skip confirmation
        
        Returns:
            Number of IPs removed
        """
        blacklist = self._load_blacklist()
        count = len(blacklist)
        
        if count == 0:
            self.logger.info("Blacklist is already empty, no changes made")
            return 0
        
        self._save_blacklist([])
        self.logger.info(f"Flushed {count} IPs from blacklist")
        return count
    
    def get_permanent_blocks(self) -> List[str]:
        """
        Get list of permanently blacklisted IPs
        
        Returns:
            List of IP addresses with lockout_period=0
        """
        blacklist = self._load_blacklist()
        return [
            entry['ip_address']
            for entry in blacklist
            if entry.get('lockout_period', 0) == 0
        ]
    
    def get_temporary_blocks(self) -> List[Dict[str, Any]]:
        """
        Get list of temporarily blacklisted IPs
        
        Returns:
            List of blacklist entries with lockout_period>0
        """
        blacklist = self._load_blacklist()
        return [
            entry
            for entry in blacklist
            if entry.get('lockout_period', 0) > 0
        ]
