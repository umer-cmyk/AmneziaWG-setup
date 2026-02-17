#!/bin/bash

# --- CONFIGURATION ---
SCRIPTS_DIR="/etc/amnezia/amneziawg/scripts"
SERVER_CONF="/etc/amnezia/amneziawg/awg0.conf"
SERVER_PUB_KEY_FILE="/etc/amnezia/amneziawg/publickey"
INTERFACE="awg0"

# MATCHING YOUR FILE NAME:
IP_SCRIPT="next_available_ip.py"

# Automatically fetch the server's public IP
SERVER_IP=$(curl -s -4 ifconfig.me)
LISTEN_PORT=$(grep "ListenPort" $SERVER_CONF | awk '{print $3}')
SERVER_PUB_KEY=$(cat $SERVER_PUB_KEY_FILE)

# --- 1. GENERATE CLIENT IDENTITY ---
CLIENT_PRIV_KEY=$(awg genkey)
CLIENT_PUB_KEY=$(echo "$CLIENT_PRIV_KEY" | awg pubkey)

# --- 2. GET NEXT AVAILABLE IP ---
# Calling the python script explicitly with python3
CLIENT_IP=$(python3 "$SCRIPTS_DIR/$IP_SCRIPT")

# Check if script returned an error or empty string
if [ -z "$CLIENT_IP" ] || [[ "$CLIENT_IP" == *"Error"* ]]; then
    echo "Error: Could not determine next IP. Output: $CLIENT_IP"
    exit 1
fi

# --- 3. REGISTER PEER ON SERVER ---
# Using 'awg set' to add the peer immediately
awg set $INTERFACE peer "$CLIENT_PUB_KEY" allowed-ips "$CLIENT_IP/32"

# Save the config so it persists
awg-quick save $INTERFACE > /dev/null 2>&1

# --- 4. EXTRACT STEALTH PARAMETERS ---
# We pull these directly from the running interface config
JC=$(grep "^Jc" $SERVER_CONF | awk '{print $3}')
JMIN=$(grep "^Jmin" $SERVER_CONF | awk '{print $3}')
JMAX=$(grep "^Jmax" $SERVER_CONF | awk '{print $3}')
S1=$(grep "^S1" $SERVER_CONF | awk '{print $3}')
S2=$(grep "^S2" $SERVER_CONF | awk '{print $3}')
H1=$(grep "^H1" $SERVER_CONF | awk '{print $3}')
H2=$(grep "^H2" $SERVER_CONF | awk '{print $3}')
H3=$(grep "^H3" $SERVER_CONF | awk '{print $3}')
H4=$(grep "^H4" $SERVER_CONF | awk '{print $3}')

# --- 5. ASSEMBLE CLIENT CONFIGURATION ---
# We store this temporarily to generate the QR code
TMP_CONF=$(mktemp)

cat <<EOF > "$TMP_CONF"
[Interface]
PrivateKey = $CLIENT_PRIV_KEY
Address = $CLIENT_IP/32
DNS = 1.1.1.1
Jc = $JC
Jmin = $JMIN
Jmax = $JMAX
S1 = $S1
S2 = $S2
H1 = $H1
H2 = $H2
H3 = $H3
H4 = $H4

[Peer]
PublicKey = $SERVER_PUB_KEY
Endpoint = $SERVER_IP:$LISTEN_PORT
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
EOF

# --- 6. OUTPUT RESULTS ---
clear
echo "=========================================================="
echo "AMNEZIAWG STEALTH CLIENT CREATED"
echo "=========================================================="
echo "IP Assigned: $CLIENT_IP"
echo "Public Key:  $CLIENT_PUB_KEY"
echo "=========================================================="
echo ""
echo "Scan the QR Code below with the AmneziaWG Android/iOS App:"
echo ""

# Install qrencode if not present (for QR code generation)
if ! command -v qrencode &> /dev/null; then
    echo "qrencode not found. Installing..."
    if [ -x "$(command -v apt)" ]; then
        sudo apt update && sudo apt install -y qrencode
    elif [ -x "$(command -v yum)" ]; then
        sudo yum install -y qrencode
    else
        echo "Error: Package manager not found. Please install qrencode manually."
        exit 1
    fi
fi

# Generate QR Code
qrencode -t ansiutf8 < "$TMP_CONF"

echo ""
echo "=========================================================="
echo "Full Config Text:"
echo "=========================================================="
cat "$TMP_CONF"

# Cleanup
rm "$TMP_CONF"