# Amnezia_WireGuard_setup

This repository contains everything you need to setup Amnezia wireguard on Ubuntu 22.04 server with automated peer management and comprehensive server monitoring.

## Contents

- **`guides/server_setup.md`** - Complete step-by-step setup guide for bare-metal AmneziaWG server
- **`setup_amnezia_wireguard.yml`** - Fully automated Ansible playbook for deployment
- **`scripts/`** - Helper scripts for peer management and monitoring:
  - `add_peer.sh` - Register VPN clients and assign IPs
  - `next_available_ip.py` - Find next available IP in subnet
  - `cleanup_inactive.sh` - Remove stale/disconnected peers
  - `awg_stats_to_api.py` - Send server stats (users, CPU, status) to monitoring API
- **`api/server.js`** - Express.js API for client registration (handles add_peer.sh via secured endpoints)

## Quick Start

```bash
# For automated deployment:
ansible-playbook -i inventory.ini setup_amnezia_wireguard.yml

# For manual setup:
# Follow: guides/server_setup.md
```

## Features

- ✅ Stealth AmneziaWG kernel module for obfuscation
- ✅ Hot-swappable peer management via API
- ✅ Real-time server monitoring (CPU, active users, service status)
- ✅ Automatic inactive peer cleanup
- ✅ Express.js API for client registration
- ✅ Full Ansible automation
