#!/bin/bash

# Configuration
INTERFACE="awg0"
IP_SCRIPT="/etc/amnezia/amneziawg/scripts/next_available_ip.py" 

# 2. Check argument
if [ -z "$1" ]; then
    echo "Error: Missing Public Key argument."
    exit 1
fi
PUB_KEY="$1"

# 4. Check if Peer Exists
EXISTING_ENTRY=$(awg show $INTERFACE allowed-ips | grep "$PUB_KEY")

if [ -n "$EXISTING_ENTRY" ]; then
    # If not empty, the peer exists. Extract the IP.
    # awk '{print $2}' gets the IP part (e.g., 10.100.0.5/32)
    # cut -d'/' -f1 removes the subnet mask (e.g., 10.100.0.5)
    EXISTING_IP=$(echo "$EXISTING_ENTRY" | awk '{print $2}' | cut -d'/' -f1)
    
    # Return the existing IP and exit success
    echo "$EXISTING_IP"
    exit 0
fi

# 5. Get IP (Silence any errors from the helper script)
NEXT_IP=$($IP_SCRIPT 2>/dev/null)
if [ $? -ne 0 ]; then
    echo "Error: No available IPs found."
    exit 1
fi

# 6. Add Peer (Suppress output/errors)
awg set $INTERFACE peer "$PUB_KEY" allowed-ips "${NEXT_IP}/32" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Error: Failed to add peer to AmneziaWG."
    exit 1
fi

# 7. Save Config (Suppress output/errors)
# Note: Since we set 'SaveConfig = true' in awg0.conf, this is a safety measure.
# We redirect output to ensure it doesn't pollute the API response.
awg-quick save $INTERFACE > /dev/null 2>&1

# Success: Output ONLY the IP
echo "$NEXT_IP"