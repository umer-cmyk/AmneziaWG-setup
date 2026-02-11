# AmneziaWG Bare-Metal Server Setup

This guide provides a step-by-step process for setting up an AmneziaWG VPN server on Ubuntu 22.04. It reproduces the "hot-swappable" and API-driven architecture while using the AmneziaWG kernel module for stealth.

## Prerequisites

- A fresh Ubuntu 22.04 server
- Root or sudo access

## 1. Install AmneziaWG

AmneziaWG is not in the default Ubuntu repositories. Add the official PPA and install the package:

```bash
# Add the Amnezia PPA
sudo add-apt-repository ppa:amnezia/ppa -y
sudo apt update

# Install the kernel module and tools
sudo apt install amneziawg -y
```
## 2. Generate Server Identity & Stealth Parameters

Amnezia requires traditional keypairs and a set of stealth "magic" parameters.

```bash
# Generate standard keys (private and public)
umask 077
awg genkey | tee privatekey | awg pubkey > publickey

# Generate random stealth parameters (Jc, Jmin, Jmax, S1, S2, H1-H4)
echo "Jc = $(shuf -i 3-10 -n 1)" > magic_params
echo "Jmin = $(shuf -i 10-50 -n 1)" >> magic_params
echo "Jmax = $(shuf -i 50-100 -n 1)" >> magic_params
echo "S1 = $(shuf -i 15-150 -n 1)" >> magic_params
echo "S2 = $(shuf -i 15-150 -n 1)" >> magic_params
echo "H1 = $(shuf -i 100000000-999999999 -n 1)" >> magic_params
echo "H2 = $(shuf -i 100000000-999999999 -n 1)" >> magic_params
echo "H3 = $(shuf -i 100000000-999999999 -n 1)" >> magic_params
echo "H4 = $(shuf -i 100000000-999999999 -n 1)" >> magic_params
```
## 3. Create the Server Configuration

Create the main configuration file at /etc/amnezia/amneziawg/awg0.conf and paste the values from `magic_params` into the `[Interface]` block.

```bash
sudo nano /etc/amnezia/amneziawg/awg0.conf
```

Example configuration:

```ini
[Interface]
# Internal server IP
Address = 10.100.0.1/16

# UDP port AmneziaWG listens on (choose a random unused port)
ListenPort = <PORT>

# Server private key
PrivateKey = <INSERT_SERVER_PRIVATE_KEY_HERE>

# --- AMNEZIA STEALTH PARAMETERS (copy from magic_params) ---
Jc = <INSERT_JC>
Jmin = <INSERT_JMIN>
Jmax = <INSERT_JMAX>
S1 = <INSERT_S1>
S2 = <INSERT_S2>
H1 = <INSERT_H1>
H2 = <INSERT_H2>
H3 = <INSERT_H3>
H4 = <INSERT_H4>
# -----------------------------------------------------------

# Allow the awg tools to persist peers
SaveConfig = true

# Firewall / NAT helpers: replace <interface> with the external NIC name
PostUp = ufw route allow in on awg0 out on <interface>
PostUp = iptables -t nat -I POSTROUTING -o <interface> -s 10.100.0.0/16 -j MASQUERADE
PreDown = iptables -t nat -D POSTROUTING -o <interface> -s 10.100.0.0/16 -j MASQUERADE
PostDown = ufw route delete allow in on awg0 out on <interface>
```

> **Note:** Replace `<interface>` with your actual network interface name (check with `ip link` or `ifconfig`)
## 4. Enable IP forwarding

Enable IPv4 forwarding as usual:

```bash
sudo nano /etc/sysctl.conf
# Uncomment or add: net.ipv4.ip_forward=1
sudo sysctl -p
```
## 5. Configure firewall (UFW)

Allow the chosen UDP port and SSH, then enable UFW:

```bash
sudo ufw allow <PORT>/udp
sudo ufw allow OpenSSH
sudo ufw enable
```
## 6. Start the server

```bash
# Start the interface and enable at boot
sudo systemctl start awg-quick@awg0
sudo systemctl enable awg-quick@awg0

# Verify
sudo awg show
```

You should see the `awg0` interface and the stealth parameters listed.

## 7. Automating peer management (scripts)

Create a scripts directory for AmneziaWG and copy the helper scripts from this repository. All server-side helper scripts are expected under `/etc/amnezia/amneziawg/scripts`.

```bash
sudo mkdir -p /etc/amnezia/amneziawg/scripts
sudo cp -v scripts/* /etc/amnezia/amneziawg/scripts/
sudo chmod +x /etc/amnezia/amneziawg/scripts/*.sh
sudo chmod +x /etc/amnezia/amneziawg/scripts/*.py
```

Recommended scripts (provided in this repository):
- `next_available_ip.sh` — finds the next available IP in the 10.100.x.x space
- `add_peer.sh` — adds a peer or returns an existing assignment
- `cleanup_inactive.sh` — removes stale peers
- `wg_stats_to_api.py` — sends server stats to the API endpoint

Schedule the cleanup script every 5 minutes and the stats script every 3 minutes using cron. Edit the root crontab (`sudo crontab -e`) and add:

```cron
*/3 * * * * /etc/amnezia/amneziawg/scripts/cleanup_inactive.sh >> /var/log/cleanup_inactive.log 2>&1
*/3 * * * * /etc/amnezia/amneziawg/scripts/wg_stats_to_api.py >> /var/log/wg_stats_to_api.log 2>&1
```

Adjust paths and timings as needed.

## 8. Setting up the API (Express.js)

Expose `add_peer.sh` via a small API. Run the API under `/etc/amnezia/amneziawg/vpn_api` and use a system account or reverse-proxy with authentication in front of it.

### A. Install Node.js & dependencies

Install Node.js (NVM is optional). Example using NVM:

```bash
# Install NVM (if desired)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
nvm install --lts

# Create API directory and install dependencies
sudo mkdir -p /etc/amnezia/amneziawg/vpn_api
sudo chown $USER /etc/amnezia/amneziawg/vpn_api
cd /etc/amnezia/amneziawg/vpn_api
npm init -y
npm install express
```

### B. Deploy the API server

Copy `api/server.js` from this repository into `/etc/amnezia/amneziawg/vpn_api/server.js` and adjust any paths inside to call `/etc/amnezia/amneziawg/scripts/add_peer.sh`.

### C. Configure sudoers for script execution

Allow the API process (or a dedicated user) to run the add-peer script without a password. Edit the sudoers file with `sudo visudo` and add a line like:

```
# Allow the API user (replace 'api_user' with the actual user)
api_user ALL=(ALL) NOPASSWD: /etc/amnezia/amneziawg/scripts/add_peer.sh
```

### D. Start the API Service

Use PM2 to keep the API running in the background.

```bash
# Install PM2 globally
sudo npm install pm2 -g

# Start the API
sudo pm2 start server.js --name vpn_api

# Save PM2 list so it restarts on reboot
sudo pm2 startup
sudo pm2 save
```

### E. Firewall the API

Open the API port (default 9008 in this guide). Restrict access where possible.

```bash
# Restrict to a single backend IP (recommended)
sudo ufw allow from 192.168.1.50 to any port 9008 proto tcp

# OR, for testing only, allow everyone
sudo ufw allow 9008/tcp
```

## 9. Final verification

Test the flow locally on the server. Example (generate a test key pair and call the API):

```bash
# Generate a test key pair (private then public)
TEST_PRIV=$(awg genkey)
TEST_PUB=$(echo "$TEST_PRIV" | awg pubkey)

# Call the API
curl -X POST http://localhost:9008/api/register-key-get-ip \
  -H "Content-Type: application/json" \
  -d "{\"public_key\": \"$TEST_PUB\"}"
```

Expected JSON should contain an assigned IP address, for example:

```json
{ "ipaddress": "10.100.x.y" }
```

Verify the peer was added to the interface:

```bash
sudo awg show
```

Adjust any commands above if you run the API under a different user or port.

---

If you want, I can also:
- update the `api/server.js` to use the correct script path and add minimal auth,
- run a quick lint/spellcheck pass, or
- create a systemd unit for the API service.