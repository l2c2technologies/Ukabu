#!/usr/bin/env python3
# Copyright (c) 2025 by L2C2 Technologies. All rights reserved.
# 
# For licensing inquiries, contact:
# Indranil Das Gupta <indradg@l2c2.co.in>

"""
ukabu-verify-bing.py - Verify Bing bot via reverse DNS

Performs 2-step verification:
1. Reverse DNS: IP -> hostname
2. Verify hostname ends with .search.msn.com
3. Forward DNS: hostname -> IP
4. Verify IP matches original
"""

import sys
import socket
import json
from datetime import datetime

def verify_bing_ip(ip_address, verbose=False):
    """
    Verify if IP belongs to Bing bot.
    
    Args:
        ip_address: IP address to verify
        verbose: Print detailed information
    
    Returns:
        True if verified, False otherwise
    """
    try:
        # Step 1: Reverse DNS lookup
        if verbose:
            print(f"Verifying {ip_address}...")
            print(f"  Step 1: Reverse DNS lookup...")
        
        hostname, _, _ = socket.gethostbyaddr(ip_address)
        
        if verbose:
            print(f"    â†’ {hostname}")
        
        # Step 2: Verify hostname ends with .search.msn.com
        if not hostname.endswith('.search.msn.com'):
            if verbose:
                print(f"  Step 2: Hostname verification FAILED")
                print(f"    Expected: *.search.msn.com")
                print(f"    Got: {hostname}")
            return False
        
        if verbose:
            print(f"  Step 2: Hostname verification OK")
        
        # Step 3: Forward DNS lookup
        if verbose:
            print(f"  Step 3: Forward DNS lookup...")
        
        forward_ip = socket.gethostbyname(hostname)
        
        if verbose:
            print(f"    â†’ {forward_ip}")
        
        # Step 4: Verify IP matches
        if forward_ip != ip_address:
            if verbose:
                print(f"  Step 4: IP verification FAILED")
                print(f"    Expected: {ip_address}")
                print(f"    Got: {forward_ip}")
            return False
        
        if verbose:
            print(f"  Step 4: IP verification OK")
            print(f"\nâœ“ VERIFIED: {ip_address} is Bing bot ({hostname})")
        
        return True
        
    except socket.herror:
        if verbose:
            print(f"  No reverse DNS record found for {ip_address}")
        return False
    except Exception as e:
        if verbose:
            print(f"  Verification failed: {e}")
        return False

def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: ukabu-verify-bing.py <ip_address> [--verbose] [--json]")
        sys.exit(1)
    
    ip_address = sys.argv[1]
    verbose = '--verbose' in sys.argv or '-v' in sys.argv
    json_output = '--json' in sys.argv
    
    verified = verify_bing_ip(ip_address, verbose=verbose and not json_output)
    
    if json_output:
        result = {
            'ip': ip_address,
            'engine': 'Bing' if verified else None,
            'verified': verified,
            'method': 'reverse_dns',
            'timestamp': datetime.now().isoformat()
        }
        print(json.dumps(result, indent=2))
    elif not verbose:
        if verified:
            print(f"âœ“ {ip_address} verified as Bing bot")
        else:
            print(f"âœ— {ip_address} not verified as Bing bot")
    
    sys.exit(0 if verified else 1)

if __name__ == '__main__':
    main()
