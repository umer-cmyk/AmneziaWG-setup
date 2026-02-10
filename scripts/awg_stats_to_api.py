#!/usr/bin/env python3
import time
import subprocess
import requests
import os
import time as t

# ----------------------------
# CONFIGURATION
# ----------------------------
API_BASE_URL = "https://papi.fusionsai.net/api"
WG_INTERFACE = "awg0" 
SERVICE_NAME = f"awg-quick@{WG_INTERFACE}.service"
PLATFORM = "android"
# Time in seconds to consider a peer "active" (e.g., handshake within last 3 mins)
HANDSHAKE_THRESHOLD = 180

# ----------------------------
# FETCH PUBLIC IP
# ----------------------------
try:
    command = "curl -4 -s ifconfig.me"
    result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, text=True)
    ipAddress = result.stdout.strip()
    # Fallback if curl fails
    if not ipAddress:
        ipAddress = "0.0.0.0"
except Exception as e:
    print(f"[ERROR] Could not fetch IP: {e}")
    ipAddress = "0.0.0.0"

print(f"Getting stats for IP: {ipAddress}")

# ----------------------------
# FUNCTION: FETCH AMNEZIA WG USERS
# ----------------------------
def get_wg_users():
    """
    Parses 'awg show <interface> dump' to count peers with a recent handshake.
    """
    try:
        # We use sudo because 'awg show' requires root privileges
        command = f"sudo awg show {WG_INTERFACE} dump"
        result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.returncode != 0:
            print(f"[ERROR] awg command failed: {result.stderr.strip()}")
            return "0"

        active_clients = 0
        current_time = int(t.time())

        lines = result.stdout.strip().split('\n')

        for line in lines:
            parts = line.split('\t')
            # A valid peer line in dump has at least 5 columns.
            # Index 4 is 'latest-handshake' (epoch timestamp)
            if len(parts) >= 5:
                try:
                    last_handshake = int(parts[4])
                    # Check if handshake happened within the threshold
                    if last_handshake > 0 and (current_time - last_handshake) <= HANDSHAKE_THRESHOLD:
                        active_clients += 1
                except ValueError:
                    continue

        print(f"Total AmneziaWG Active Clients (last {HANDSHAKE_THRESHOLD}s): {active_clients}")
        return str(active_clients)

    except Exception as e:
        print(f"[ERROR] Failed to get AmneziaWG users: {e}")
        return "0"

# ----------------------------
# FUNCTION: FETCH 15-MIN CPU USAGE
# ----------------------------
def get_cpu_usage_15min():
    try:
        load1, load5, load15 = os.getloadavg()
        total_cores = os.cpu_count() or 1
        cpu_usage_percent = (load15 / total_cores) * 100
        return round(cpu_usage_percent, 2)
    except Exception as e:
        print(f"Error getting CPU usage: {e}")
        return 0.0

# ----------------------------
# FUNCTION: CHECK SERVICE STATUS
# ----------------------------
def check_service_status(service_name):
    """Check if the AmneziaWG service is active (returns '1' or '0')."""
    try:
        result = subprocess.run(
            ["systemctl", "is-active", service_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        status = "1" if result.stdout.strip() == "active" else "0"
    except Exception:
        status = "0"
    print(f"Service '{service_name}' status = {status}")
    return status

# ----------------------------
# FUNCTION: SEND DATA TO API
# ----------------------------
def send_data():
    totalClientsValue = get_wg_users()
    cpu_usage = get_cpu_usage_15min()
    
    # Send User count
    try:
        responseWG = requests.post(
            f"{API_BASE_URL}/total-users/amnezia/{ipAddress}/{totalClientsValue}",
            timeout=10
        )
        print(f"[INFO] Sent total users → {API_BASE_URL}/total-users/amnezia/{ipAddress}/{totalClientsValue} | Status: {responseWG.status_code}")
    except Exception as e:
        print(f"[ERROR] Failed to send total users: {e}")

    # Send CPU usage
    try:
        responseCPU = requests.post(
            f"{API_BASE_URL}/cpu-usage/amnezia/{ipAddress}/{cpu_usage}",
            timeout=10
        )
        print(f"[INFO] Sent CPU usage   → {API_BASE_URL}/cpu-usage/amnezia/{ipAddress}/{cpu_usage} | Status: {responseCPU.status_code}")
    except Exception as e:
        print(f"[ERROR] Failed to send CPU usage: {e}")

    # Send Service status
    try:
        status = check_service_status(SERVICE_NAME)
        responseStatus = requests.post(
            f"{API_BASE_URL}/update-instance-status/{ipAddress}/amnezia/{PLATFORM}/{status}",
            timeout=10
        )
        print(f"[INFO] Sent service status → {API_BASE_URL}/update-instance-status/{ipAddress}/amnezia/{PLATFORM}/{status} | Status: {responseStatus.status_code}")
    except Exception as e:
        print(f"[ERROR] Failed to send service status: {e}")

# ----------------------------
# MAIN EXECUTION
# ----------------------------
if __name__ == "__main__":
    time.sleep(2)
    send_data()