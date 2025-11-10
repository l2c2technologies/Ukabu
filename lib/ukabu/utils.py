#!/usr/bin/env python3
# Copyright (c) 2025 by L2C2 Technologies. All rights reserved.
# 
# For licensing inquiries, contact:
# Indranil Das Gupta <indradg@l2c2.co.in>

"""
Common utility functions for UKABU WAF management
"""

import os
import sys
import json
import logging
import shutil
import secrets
import ipaddress
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Configuration paths
UKABU_CONFIG_DIR = Path("/etc/ukabu/config")
UKABU_SECRETS_DIR = Path("/etc/ukabu/secrets")
UKABU_INCLUDES_DIR = Path("/etc/ukabu/includes")
UKABU_LOG_DIR = Path("/var/log/ukabu")
UKABU_LIB_DIR = Path("/var/lib/ukabu")
NGINX_SITES_AVAILABLE = Path("/etc/nginx/sites-available")
NGINX_SITES_ENABLED = Path("/etc/nginx/sites-enabled")

# Configuration files
DOMAINS_CONFIG = UKABU_CONFIG_DIR / "domains.json"
IP_WHITELIST = UKABU_CONFIG_DIR / "ip_whitelist.conf"
IP_BLACKLIST = UKABU_CONFIG_DIR / "ip_blacklist.conf"
PATH_WHITELIST = UKABU_CONFIG_DIR / "path_whitelist.conf"
PATH_BLACKLIST = UKABU_CONFIG_DIR / "path_blacklist.conf"

# Daemon socket
DAEMON_SOCKET = "/var/run/ukabu-trackerd.sock"

# Audit log
AUDIT_LOG = UKABU_LOG_DIR / "manager.log"


def setup_logging(verbose: bool = False, audit: bool = True) -> logging.Logger:
    """
    Set up logging for ukabu-manager
    
    Args:
        verbose: Enable debug logging
        audit: Enable audit logging to file
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger('ukabu-manager')
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # Audit log handler
    if audit:
        try:
            UKABU_LOG_DIR.mkdir(parents=True, exist_ok=True, mode=0o755)
            file_handler = logging.FileHandler(AUDIT_LOG)
            file_handler.setLevel(logging.INFO)
            file_formatter = logging.Formatter(
                '%(asctime)s [%(levelname)s] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        except PermissionError:
            logger.warning(f"Cannot write to audit log {AUDIT_LOG} - insufficient permissions")
    
    return logger


def validate_ip(ip_str: str) -> Tuple[bool, Optional[str]]:
    """
    Validate IP address or CIDR range
    
    Args:
        ip_str: IP address or CIDR notation
    
    Returns:
        (is_valid, error_message)
    """
    try:
        ipaddress.ip_network(ip_str, strict=False)
        return True, None
    except ValueError as e:
        return False, str(e)


def validate_domain(domain: str) -> Tuple[bool, Optional[str]]:
    """
    Validate domain name format
    
    Args:
        domain: Domain name to validate
    
    Returns:
        (is_valid, error_message)
    """
    if not domain or len(domain) > 253:
        return False, "Domain name must be 1-253 characters"
    
    # Basic domain validation
    parts = domain.split('.')
    if len(parts) < 2:
        return False, "Domain must have at least one dot (e.g., example.com)"
    
    for part in parts:
        if not part or len(part) > 63:
            return False, "Domain labels must be 1-63 characters"
        if not part.replace('-', '').replace('_', '').isalnum():
            return False, "Domain labels must be alphanumeric (with - or _)"
    
    return True, None


def generate_hmac_secret(length: int = 64) -> str:
    """
    Generate cryptographically secure HMAC secret
    
    Args:
        length: Length of secret in bytes (default 64)
    
    Returns:
        Hex-encoded secret string
    """
    return secrets.token_hex(length)


def load_json_file(filepath: Path, default: Any = None) -> Any:
    """
    Load JSON file with error handling
    
    Args:
        filepath: Path to JSON file
        default: Default value if file doesn't exist
    
    Returns:
        Parsed JSON data or default
    """
    if not filepath.exists():
        return default if default is not None else {}
    
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {filepath}: {e}")
    except PermissionError:
        raise PermissionError(f"Cannot read {filepath} - insufficient permissions")


def save_json_file(filepath: Path, data: Any, backup: bool = True) -> None:
    """
    Save JSON file with atomic write and optional backup
    
    Args:
        filepath: Path to JSON file
        data: Data to save
        backup: Create backup of existing file
    """
    # Create parent directory if needed
    filepath.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
    
    # Backup existing file
    if backup and filepath.exists():
        backup_path = filepath.with_suffix(filepath.suffix + '.bak')
        shutil.copy2(filepath, backup_path)
    
    # Atomic write using temp file
    temp_path = filepath.with_suffix(filepath.suffix + '.tmp')
    try:
        with open(temp_path, 'w') as f:
            json.dump(data, f, indent=2, sort_keys=True)
            f.write('\n')  # Add trailing newline
        
        # Atomic rename
        temp_path.replace(filepath)
        
        # Set permissions (readable by nginx user)
        os.chmod(filepath, 0o644)
    except Exception as e:
        # Clean up temp file on error
        if temp_path.exists():
            temp_path.unlink()
        raise RuntimeError(f"Failed to save {filepath}: {e}")


def load_line_file(filepath: Path) -> List[str]:
    """
    Load line-based config file (e.g., IP whitelist)
    
    Args:
        filepath: Path to file
    
    Returns:
        List of non-empty, non-comment lines
    """
    if not filepath.exists():
        return []
    
    try:
        with open(filepath, 'r') as f:
            lines = []
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith('#'):
                    lines.append(line)
            return lines
    except PermissionError:
        raise PermissionError(f"Cannot read {filepath} - insufficient permissions")


def save_line_file(filepath: Path, lines: List[str], backup: bool = True) -> None:
    """
    Save line-based config file with atomic write
    
    Args:
        filepath: Path to file
        lines: List of lines to save
        backup: Create backup of existing file
    """
    # Create parent directory if needed
    filepath.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
    
    # Backup existing file
    if backup and filepath.exists():
        backup_path = filepath.with_suffix(filepath.suffix + '.bak')
        shutil.copy2(filepath, backup_path)
    
    # Atomic write
    temp_path = filepath.with_suffix(filepath.suffix + '.tmp')
    try:
        with open(temp_path, 'w') as f:
            for line in lines:
                f.write(f"{line}\n")
        
        temp_path.replace(filepath)
        os.chmod(filepath, 0o644)
    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        raise RuntimeError(f"Failed to save {filepath}: {e}")


def confirm_action(prompt: str, default: bool = False) -> bool:
    """
    Prompt user for confirmation
    
    Args:
        prompt: Confirmation prompt
        default: Default response if user just presses Enter
    
    Returns:
        True if confirmed, False otherwise
    """
    choices = 'Y/n' if default else 'y/N'
    response = input(f"{prompt} [{choices}]: ").strip().lower()
    
    if not response:
        return default
    
    return response in ('y', 'yes')


def check_root_privileges() -> bool:
    """
    Check if running with root privileges
    
    Returns:
        True if running as root
    """
    return os.geteuid() == 0


def get_timestamp_iso() -> str:
    """
    Get current timestamp in ISO format (UTC)
    
    Returns:
        ISO 8601 timestamp string
    """
    return datetime.now(timezone.utc).isoformat()


def parse_iso_timestamp(timestamp_str: str) -> datetime:
    """
    Parse ISO 8601 timestamp
    
    Args:
        timestamp_str: ISO timestamp string
    
    Returns:
        datetime object
    """
    return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))


def is_secret_expired(timestamp_str: str, grace_hours: int = 12) -> bool:
    """
    Check if a secret has expired based on grace period
    
    Args:
        timestamp_str: ISO timestamp when secret was rotated
        grace_hours: Grace period in hours
    
    Returns:
        True if expired
    """
    rotated_time = parse_iso_timestamp(timestamp_str)
    now = datetime.now(timezone.utc)
    age_hours = (now - rotated_time).total_seconds() / 3600
    return age_hours > grace_hours


def format_bytes(bytes_val: int) -> str:
    """
    Format bytes as human-readable string
    
    Args:
        bytes_val: Number of bytes
    
    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} PB"


def ensure_directories() -> None:
    """
    Ensure all required directories exist with correct permissions
    """
    directories = [
        (UKABU_CONFIG_DIR, 0o755),
        (UKABU_SECRETS_DIR, 0o700),  # Secrets directory is restricted
        (UKABU_INCLUDES_DIR, 0o755),
        (UKABU_LOG_DIR, 0o755),
        (UKABU_LIB_DIR, 0o755),
    ]
    
    for directory, mode in directories:
        directory.mkdir(parents=True, exist_ok=True, mode=mode)
        # Ensure correct permissions even if directory existed
        os.chmod(directory, mode)
