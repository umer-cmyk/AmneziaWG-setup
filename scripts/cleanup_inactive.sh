#!/bin/bash

# Configuration
INTERFACE="awg0"
MINUTES=10
LIMIT_SECONDS=$((MINUTES * 60))
CURRENT_TIME=$(date +%s)

echo "Starting cleanup on interface $INTERFACE..."

# We use 'dump' because it gives us everything in one tab-separated line:
# Col 1: Public Key
# Col 4: Allowed IPs
# Col 5: Latest Handshake (Epoch timestamp)
#
# We set IFS to tab ($'\t') to correctly parse fields even if they contain spaces.
while IFS=$'\t' read -r PUB_KEY _ _ ALLOWED_IPS HANDSHAKE _; do
    
    # 1. REMOVE INVALID PEERS (Race Condition Fix)
    # Check if allowed-ips is exactly "(none)"
    if [[ "$ALLOWED_IPS" == "(none)" ]]; then
        echo "Removing Peer: $PUB_KEY"
        echo "  - Reason: Invalid IP configuration ((none))"
        awg set "$INTERFACE" peer "$PUB_KEY" remove
        continue
    fi

    # 2. REMOVE NEVER CONNECTED PEERS
    # Check if handshake is 0
    if [[ "$HANDSHAKE" -eq 0 ]]; then
        echo "Removing Peer: $PUB_KEY"
        echo "  - Reason: Never connected (Handshake 0)"
        awg set "$INTERFACE" peer "$PUB_KEY" remove
        continue
    fi

    # 3. REMOVE INACTIVE PEERS
    # Calculate time difference
    TIME_DIFF=$((CURRENT_TIME - HANDSHAKE))

    if [[ "$TIME_DIFF" -gt "$LIMIT_SECONDS" ]]; then
        MINUTES_INACTIVE=$((TIME_DIFF / 60))
        echo "Removing Peer: $PUB_KEY"
        echo "  - Reason: Inactive for $MINUTES_INACTIVE minutes"
        awg set "$INTERFACE" peer "$PUB_KEY" remove
    fi

done < <(awg show "$INTERFACE" dump)

# Save changes to disk
awg-quick save "$INTERFACE" > /dev/null 2>&1

echo "Cleanup complete."