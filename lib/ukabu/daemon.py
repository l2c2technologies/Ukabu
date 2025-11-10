#!/usr/bin/env python3
# Copyright (c) 2025 by L2C2 Technologies. All rights reserved.
# 
# For licensing inquiries, contact:
# Indranil Das Gupta <indradg@l2c2.co.in>

"""
Unix socket client for communicating with ukabu-trackerd daemon
"""

import json
import socket
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

from .utils import DAEMON_SOCKET


class DaemonClient:
    """Client for communicating with ukabu-trackerd via Unix socket"""
    
    def __init__(self, socket_path: str = DAEMON_SOCKET, timeout: float = 5.0):
        """
        Initialize daemon client
        
        Args:
            socket_path: Path to Unix socket
            timeout: Socket timeout in seconds
        """
        self.socket_path = socket_path
        self.timeout = timeout
        self.logger = logging.getLogger('ukabu-manager.daemon')
    
    def _send_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send command to daemon and receive response
        
        Args:
            command: Command dictionary
        
        Returns:
            Response dictionary
        
        Raises:
            ConnectionError: If cannot connect to daemon
            RuntimeError: If daemon returns error
        """
        if not Path(self.socket_path).exists():
            raise ConnectionError(
                f"Daemon socket not found at {self.socket_path}. "
                "Is ukabu-trackerd running?"
            )
        
        try:
            # Connect to Unix socket
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect(self.socket_path)
            
            # Send command
            command_json = json.dumps(command) + '\n'
            sock.sendall(command_json.encode('utf-8'))
            
            # Receive response
            response_data = b''
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response_data += chunk
                if b'\n' in response_data:
                    break
            
            sock.close()
            
            # Parse response
            response = json.loads(response_data.decode('utf-8'))
            
            # Check for errors
            if response.get('status') == 'error':
                raise RuntimeError(response.get('message', 'Unknown daemon error'))
            
            return response
        
        except socket.timeout:
            raise ConnectionError("Daemon socket timeout - daemon may be unresponsive")
        except ConnectionRefusedError:
            raise ConnectionError("Daemon refused connection - is it running?")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON response from daemon: {e}")
        except Exception as e:
            raise RuntimeError(f"Daemon communication error: {e}")
    
    def ping(self) -> bool:
        """
        Check if daemon is responsive
        
        Returns:
            True if daemon responds
        """
        try:
            response = self._send_command({"action": "ping"})
            return response.get('status') == 'ok'
        except Exception as e:
            self.logger.debug(f"Daemon ping failed: {e}")
            return False
    
    def reload_config(self) -> bool:
        """
        Signal daemon to reload configuration
        
        Returns:
            True if successful
        """
        response = self._send_command({"action": "reload"})
        return response.get('status') == 'ok'
    
    def get_strikes(self, ip_address: Optional[str] = None) -> Dict[str, Any]:
        """
        Get strike counts for IP(s)
        
        Args:
            ip_address: Specific IP to query (None for all)
        
        Returns:
            Dictionary of IP addresses and their strike counts
        """
        command = {"action": "strikes"}
        if ip_address:
            command["ip"] = ip_address
        
        response = self._send_command(command)
        return response.get('data', {})
    
    def flush_strikes(self, ip_address: str) -> bool:
        """
        Flush strikes for specific IP
        
        Args:
            ip_address: IP address to unblock
        
        Returns:
            True if successful
        """
        response = self._send_command({
            "action": "flush",
            "ip": ip_address
        })
        return response.get('status') == 'ok'
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get daemon statistics
        
        Returns:
            Statistics dictionary with uptime, memory, counts, etc.
        """
        response = self._send_command({"action": "stats"})
        return response.get('data', {})
    
    def get_blocks(self) -> List[Dict[str, Any]]:
        """
        Get list of currently blocked IPs
        
        Returns:
            List of blocked IP records
        """
        response = self._send_command({"action": "blocks"})
        return response.get('data', {}).get('blocks', [])
    
    def add_block(self, ip_address: str, duration: int, reason: str = "") -> bool:
        """
        Manually add IP to blocklist
        
        Args:
            ip_address: IP to block
            duration: Lockout duration in minutes (0 for permanent)
            reason: Block reason
        
        Returns:
            True if successful
        """
        response = self._send_command({
            "action": "block",
            "ip": ip_address,
            "duration": duration,
            "reason": reason
        })
        return response.get('status') == 'ok'
    
    def remove_block(self, ip_address: str) -> bool:
        """
        Remove IP from blocklist
        
        Args:
            ip_address: IP to unblock
        
        Returns:
            True if successful
        """
        response = self._send_command({
            "action": "unblock",
            "ip": ip_address
        })
        return response.get('status') == 'ok'
    
    def is_running(self) -> bool:
        """
        Check if daemon is running
        
        Returns:
            True if daemon is responsive
        """
        return self.ping()
    
    def health_check(self) -> Dict[str, Any]:
        """
        Comprehensive health check of daemon
        
        Returns:
            Dictionary with health status information
        """
        health = {
            'running': False,
            'responsive': False,
            'uptime': None,
            'memory_mb': None,
            'total_strikes': 0,
            'active_blocks': 0,
            'error': None
        }
        
        try:
            # Check if daemon is running
            if not Path(self.socket_path).exists():
                health['error'] = 'Socket not found'
                return health
            
            health['running'] = True
            
            # Try to get stats
            stats = self.get_stats()
            health['responsive'] = True
            health['uptime'] = stats.get('uptime_seconds')
            health['memory_mb'] = stats.get('memory_mb')
            health['total_strikes'] = stats.get('total_strikes', 0)
            health['active_blocks'] = stats.get('active_blocks', 0)
        
        except Exception as e:
            health['error'] = str(e)
        
        return health
