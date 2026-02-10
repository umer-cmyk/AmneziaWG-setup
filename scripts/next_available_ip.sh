#!/bin/bash

# Configuration
INTERFACE="awg0"
PREFIX_1="10"
PREFIX_2="100"

# 1. Get list of currently used IPs
USED_IPS=$(sudo awg show $INTERFACE allowed-ips | awk '{print $2}' | cut -d'/' -f1)

# 2. Nested Loop to find the next available IP
# Outer Loop: The 3rd octet (0 to 255) -> 10.100.X.xxx
for ((octet3=0; octet3<=255; octet3++)); do

    # Inner Loop: The 4th octet (2 to 254) -> 10.100.xxx.Y
    # We start at 2 to reserve .1 for the gateway (10.100.0.1)
    for ((octet4=2; octet4<=254; octet4++)); do

        CANDIDATE="${PREFIX_1}.${PREFIX_2}.${octet3}.${octet4}"

        # Check if this IP is in the used list
        # using -F for fixed string search is slightly faster and safer
        if ! echo "$USED_IPS" | grep -F -q -w "$CANDIDATE"; then
            echo "$CANDIDATE"
            exit 0
        fi

    done
done

echo "Error: Network is full (65k IPs assigned!)" >&2
exit 1