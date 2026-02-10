#!/bin/bash

# Configuration
INTERFACE="awg0"
HOURS=2
# Convert hours to seconds
LIMIT_SECONDS=$((HOURS * 3600))
CURRENT_TIME=$(date +%s)

echo "Starting cleanup on interface $INTERFACE..."

# 2. Loop through all peers and check last handshake
awg show $INTERFACE latest-handshakes | while read -r PUBLIC_KEY HANDSHAKE_TIME; do

    # CASE A: Peer never connected (Handshake is 0)
    if [ "$HANDSHAKE_TIME" -eq 0 ]; then
        echo "Removing Peer: $PUBLIC_KEY"
        echo "  - Reason: Never connected (Handshake 0)"
        
        awg set $INTERFACE peer "$PUBLIC_KEY" remove
        continue
    fi

    # CASE B: Peer connected before, but is now inactive
    TIME_DIFF=$((CURRENT_TIME - HANDSHAKE_TIME))

    if [ "$TIME_DIFF" -gt "$LIMIT_SECONDS" ]; then
        HOURS_INACTIVE=$((TIME_DIFF / 3600))
        
        echo "Removing Peer: $PUBLIC_KEY"
        echo "  - Reason: Inactive for $HOURS_INACTIVE hours"
        
        awg set $INTERFACE peer "$PUBLIC_KEY" remove
    fi
done

# 3. Save changes to disk
# This ensures the removals are written to /etc/amnezia/amneziawg/awg0.conf
awg-quick save $INTERFACE > /dev/null 2>&1

echo "Cleanup complete."