# Copyright (c) 2025 by L2C2 Technologies. All rights reserved.
# 
# For licensing inquiries, contact:
# Indranil Das Gupta <indradg@l2c2.co.in>

"""
Search engine detection module for UKABU WAF.
Handles Google (IP whitelist) and Bing (reverse DNS) verification.
"""

import json
import socket
import ipaddress
from datetime import datetime, timedelta
from typing import Optional, Dict
import os
from .utils import log_action

class SearchEngineDetector:
    """Detects and verifies search engine bots."""
    
    def __init__(self, 
                 google_config="/etc/ukabu/config/search_engines_google.conf",
                 bing_cache="/etc/ukabu/config/search_engines_bing_cache.json"):
        self.google_config = google_config
        self.bing_cache = bing_cache
        self.google_ips = self._load_google_ips()
        self.bing_cache_data = self._load_bing_cache()
    
    def _load_google_ips(self) -> set:
        """Load Google bot IP ranges from config file."""
        ips = set()
        
        if not os.path.exists(self.google_config):
            return ips
        
        try:
            with open(self.google_config, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        ips.add(line)
        except Exception as e:
            print(f"Warning: Could not load Google IPs: {e}")
        
        return ips
    
    def _load_bing_cache(self) -> dict:
        """Load Bing DNS verification cache."""
        if not os.path.exists(self.bing_cache):
            return {}
        
        try:
            with open(self.bing_cache, 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def _save_bing_cache(self):
        """Save Bing DNS verification cache."""
        try:
            with open(self.bing_cache, 'w') as f:
                json.dump(self.bing_cache_data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save Bing cache: {e}")
    
    def verify(self, ip: str, verbose: bool = False) -> Optional[Dict[str, str]]:
        """
        Verify if IP belongs to a known search engine.
        
        Args:
            ip: IP address to verify
            verbose: Verbose output
        
        Returns:
            Dict with 'engine' and 'method' if verified, None otherwise
        """
        # Check Google first (fast IP whitelist)
        if self._is_google(ip):
            if verbose:
                print(f"âœ“ {ip} verified as Google (IP whitelist)")
            return {'engine': 'Google', 'method': 'ip_whitelist'}
        
        # Check Bing (reverse DNS with caching)
        if self._is_bing(ip, verbose):
            if verbose:
                print(f"âœ“ {ip} verified as Bing (reverse DNS)")
            return {'engine': 'Bing', 'method': 'reverse_dns'}
        
        if verbose:
            print(f"âœ— {ip} not recognized as search engine")
        
        return None
    
    def _is_google(self, ip: str) -> bool:
        """Check if IP is in Google IP whitelist."""
        try:
            ip_addr = ipaddress.ip_address(ip)
            
            for ip_range in self.google_ips:
                try:
                    if '/' in ip_range:
                        network = ipaddress.ip_network(ip_range, strict=False)
                        if ip_addr in network:
                            return True
                    elif str(ip_addr) == ip_range:
                        return True
                except:
                    continue
            
            return False
        except:
            return False
    
    def _is_bing(self, ip: str, verbose: bool = False) -> bool:
        """
        Verify Bing bot using reverse DNS (2-step verification).
        
        Steps:
        1. Reverse DNS lookup: IP -> hostname
        2. Verify hostname ends with .search.msn.com
        3. Forward DNS lookup: hostname -> IP
        4. Verify IP matches original
        
        Results are cached for 24 hours.
        """
        # Check cache first
        if ip in self.bing_cache_data:
            cached = self.bing_cache_data[ip]
            cache_time = datetime.fromisoformat(cached['timestamp'])
            
            # Cache valid for 24 hours
            if datetime.now() - cache_time < timedelta(hours=24):
                if verbose:
                    print(f"  (using cached result: {cached['verified']})")
                return cached['verified']
        
        # Perform verification
        verified = False
        
        try:
            # Step 1: Reverse DNS lookup
            hostname, _, _ = socket.gethostbyaddr(ip)
            
            if verbose:
                print(f"  Reverse DNS: {ip} -> {hostname}")
            
            # Step 2: Verify hostname
            if hostname.endswith('.search.msn.com'):
                # Step 3: Forward DNS lookup
                forward_ip = socket.gethostbyname(hostname)
                
                if verbose:
                    print(f"  Forward DNS: {hostname} -> {forward_ip}")
                
                # Step 4: Verify IP matches
                if forward_ip == ip:
                    verified = True
        except socket.herror:
            if verbose:
                print(f"  No reverse DNS record found")
        except Exception as e:
            if verbose:
                print(f"  Verification failed: {e}")
        
        # Update cache
        self.bing_cache_data[ip] = {
            'verified': verified,
            'timestamp': datetime.now().isoformat()
        }
        self._save_bing_cache()
        
        return verified
    
    def update_google_ips(self, dry_run: bool = False, verbose: bool = False) -> bool:
        """
        Update Google IP whitelist from official source.
        
        This is normally called by systemd timer daily.
        
        Args:
            dry_run: If True, only show what would be done
            verbose: Verbose output
        
        Returns:
            True if successful
        """
        import subprocess
        
        url = "https://www.gstatic.com/ipranges/goog.json"
        
        if dry_run:
            print(f"[DRY RUN] Would fetch Google IPs from {url}")
            return True
        
        try:
            if verbose:
                print(f"Fetching Google IP ranges from {url}...")
            
            # Fetch JSON
            result = subprocess.run(
                ['curl', '-s', url],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                print(f"Error fetching Google IPs: curl failed")
                return False
            
            data = json.loads(result.stdout)
            
            # Extract IPv4 prefixes
            ipv4_ranges = []
            for prefix in data.get('prefixes', []):
                if 'ipv4Prefix' in prefix:
                    ipv4_ranges.append(prefix['ipv4Prefix'])
            
            if not ipv4_ranges:
                print("Error: No IPv4 ranges found in response")
                return False
            
            # Write to config file
            with open(self.google_config, 'w') as f:
                f.write(f"# Google bot IP ranges\n")
                f.write(f"# Auto-updated: {datetime.now().isoformat()}\n")
                f.write(f"# Source: {url}\n")
                f.write(f"# Count: {len(ipv4_ranges)} ranges\n\n")
                for ip_range in ipv4_ranges:
                    f.write(f"{ip_range}\n")
            
            log_action(f"Updated Google IP whitelist ({len(ipv4_ranges)} ranges)")
            
            if verbose:
                print(f"âœ“ Updated {len(ipv4_ranges)} Google IP ranges")
            else:
                print(f"âœ“ Updated Google IP whitelist")
            
            # Reload cached IPs
            self.google_ips = self._load_google_ips()
            
            return True
            
        except Exception as e:
            print(f"Error updating Google IPs: {e}")
            return False
    
    def clear_bing_cache(self, dry_run: bool = False) -> bool:
        """
        Clear Bing DNS verification cache.
        
        Args:
            dry_run: If True, only show what would be done
        
        Returns:
            True if successful
        """
        if dry_run:
            print(f"[DRY RUN] Would clear Bing DNS cache ({len(self.bing_cache_data)} entries)")
            return True
        
        count = len(self.bing_cache_data)
        self.bing_cache_data = {}
        self._save_bing_cache()
        
        log_action(f"Cleared Bing DNS cache ({count} entries)")
        print(f"âœ“ Cleared Bing DNS cache ({count} entries)")
        
        return True
    
    def list_recognized(self) -> bool:
        """
        List currently recognized search engines.
        
        Returns:
            True if successful
        """
        print("\nRecognized Search Engines:")
        print("=" * 60)
        
        print(f"\nGoogle (IP Whitelist):")
        print(f"  IP Ranges: {len(self.google_ips)}")
        if self.google_ips:
            sample = list(self.google_ips)[:5]
            for ip_range in sample:
                print(f"    â€¢ {ip_range}")
            if len(self.google_ips) > 5:
                print(f"    ... and {len(self.google_ips) - 5} more")
        
        print(f"\nBing (Reverse DNS):")
        print(f"  Cached Verifications: {len(self.bing_cache_data)}")
        if self.bing_cache_data:
            verified = sum(1 for v in self.bing_cache_data.values() if v['verified'])
            print(f"  Verified IPs: {verified}")
        
        print("")
        return True
