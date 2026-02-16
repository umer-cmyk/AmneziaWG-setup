#!/usr/bin/env python3
import subprocess
import sys

# CONFIGURATION
INTERFACE = "awg0"
PREFIX = "10.100"

def get_next_available_ip():
    # 1. Get all currently used IPs (One single system call)
    try:
        # Run 'awg show' and capture output
        cmd = f"sudo awg show {INTERFACE} allowed-ips"
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, text=True)
        
        # Parse output into a Python SET for O(1) instant lookups
        used_ips = set()
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2:
                # Format is usually: publicKey  10.100.0.2/32
                ip_cidr = parts[1]
                ip = ip_cidr.split('/')[0]
                used_ips.add(ip)
                
    except Exception as e:
        print(f"Error fetching IPs: {e}", file=sys.stderr)
        sys.exit(1)

    # 2. Iterate to find the first free IP
    # We use python ranges which are incredibly fast
    for octet3 in range(0, 256):       # 0 to 255
        for octet4 in range(2, 255):   # 2 to 254 (Skip .0, .1, .255)
            
            candidate = f"{PREFIX}.{octet3}.{octet4}"
            
            # The Magic: This lookup is instant. No grep. No subprocess.
            if candidate not in used_ips:
                print(candidate)
                return

    print("Error: Network is full", file=sys.stderr)
    sys.exit(1)

if __name__ == "__main__":
    get_next_available_ip()