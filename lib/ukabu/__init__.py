#!/usr/bin/env python3
# Copyright (c) 2025 by L2C2 Technologies. All rights reserved.
#
# For licensing inquiries, contact:
# Indranil Das Gupta <indradg@l2c2.co.in>

"""
UKABU WAF - Python Management Library

Modular library for managing UKABU WAF configuration, domains, IP lists,
and communication with the ukabu-trackerd daemon.
"""

__version__ = "1.0.0-phase3"
__author__ = "L2C2 Technologies"
__license__ = "Proprietary"

# Import main modules for convenience
from .utils import (
    setup_logging,
    validate_ip,
    validate_domain,
    check_root_privileges,
    confirm_action,
    format_bytes
)
from .daemon import DaemonClient
from .domain import DomainManager
from .ipmanager import IPManager
from .nginx import NginxManager

__all__ = [
    'setup_logging',
    'validate_ip',
    'validate_domain',
    'check_root_privileges',
    'confirm_action',
    'format_bytes',
    'DaemonClient',
    'DomainManager',
    'IPManager',
    'NginxManager',
]
