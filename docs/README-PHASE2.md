# UKABU WAF - Component B (ukabu-monitor): Strike Tracking & IP Blocking

**Copyright (c) 2025 by L2C2 Technologies. All rights reserved.**

For licensing inquiries: Indranil Das Gupta <indradg@l2c2.co.in>

## Component B (ukabu-monitor) Objectives

✅ Strike tracking with SQLite persistence  
✅ Unix socket communication  
✅ ipset management  
✅ Automatic firewall rules  
✅ iptables/nftables auto-detection  
✅ Prometheus metrics  
✅ First timeout excuse (per-domain)  
✅ Expired block cleanup  

## Installation

```bash
tar -xzf ukabu-component2.tar.gz
cd ukabu-component2
sudo bash install-component2.sh
```

## Verification

```bash
# Check daemon
systemctl status ukabu-trackerd

# Check ipsets
sudo ipset list | grep ukabu

# Check metrics
curl http://localhost:9090/metrics
```

See full documentation in the tarball.
