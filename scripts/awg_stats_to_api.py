#!/usr/bin/env python3
import time
import subprocess
import requests
import os
import json

# ----------------------------
# CONFIGURATION
# ----------------------------
API_BASE_URL = "https://papi.fusionsai.net/api"
WG_INTERFACE = "awg0" 
# REPLACE <interface> with your actual interface (e.g., enp6s0 or eth0)
NETWORK_INTERFACE = "<interface>" 
SERVICE_NAME = f"awg-quick@{WG_INTERFACE}.service"
PLATFORM = "android"
HANDSHAKE_THRESHOLD = 180

# ----------------------------
# FETCH PUBLIC IP
# ----------------------------
try:
    command = "curl -s -4 icanhazip.com"
    result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, text=True)
    ipAddress = result.stdout.strip()
    if not ipAddress:
        ipAddress = "0.0.0.0"
except Exception as e:
    print(f"[ERROR] Could not fetch IP: {e}")
    ipAddress = "0.0.0.0"

# ----------------------------
# HELPER FUNCTIONS
# ----------------------------

def get_download_speed(interface, interval=1):
    """
    Calculates only Download (RX) speed in Mbps.
    """
    def get_rx_bytes(iface):
        try:
            return int(open(f'/sys/class/net/{iface}/statistics/rx_bytes').read())
        except FileNotFoundError:
            return 0

    rx1 = get_rx_bytes(interface)
    time.sleep(interval)
    rx2 = get_rx_bytes(interface)

    # Calculate Mbps: (Bytes * 8) / 1,000,000 / seconds
    download_mbps = round(((rx2 - rx1) * 8) / 1_000_000 / interval, 2)

    return download_mbps

def get_vnstat_usage(interface):
    stats = {"daily": 0.0, "weekly": 0.0, "monthly": 0.0}
    if subprocess.call(["which", "vnstat"], stdout=subprocess.DEVNULL) != 0:
        return stats

    try:
        result = subprocess.run(["vnstat", "-i", interface, "--json"], capture_output=True, text=True)
        if result.returncode != 0 or not result.stdout.strip():
            return stats

        data = json.loads(result.stdout)
        if "interfaces" not in data or not data["interfaces"]:
            return stats

        iface_data = data["interfaces"][0]
        traffic = iface_data.get("traffic", {})

        # Daily
        days = traffic.get("day", [])
        if days:
            today = days[-1]
            stats["daily"] = round((today['rx'] + today['tx']) / 1073741824, 2)

        # Weekly (Sum last 7 days)
        if days:
            last_7 = days[-7:]
            week_bytes = sum(d['rx'] + d['tx'] for d in last_7)
            stats["weekly"] = round(week_bytes / 1073741824, 2)

        # Monthly
        months = traffic.get("month", [])
        if months:
            this_month = months[-1]
            stats["monthly"] = round((this_month['rx'] + this_month['tx']) / 1073741824, 2)

        return stats
    except Exception:
        return stats

def get_wg_users():
    try:
        command = f"sudo awg show {WG_INTERFACE} dump"
        result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            return "0"

        active_clients = 0
        current_time = int(time.time())
        lines = result.stdout.strip().split('\n')

        for line in lines:
            parts = line.split('\t')
            if len(parts) >= 5:
                try:
                    last_handshake = int(parts[4])
                    if last_handshake > 0 and (current_time - last_handshake) <= HANDSHAKE_THRESHOLD:
                        active_clients += 1
                except ValueError:
                    continue
        return str(active_clients)
    except Exception:
        return "0"

def get_cpu_usage_15min():
    try:
        load1, load5, load15 = os.getloadavg()
        total_cores = os.cpu_count() or 1
        return round((load15 / total_cores) * 100, 2)
    except Exception:
        return 0.0

def check_service_status(service_name):
    try:
        result = subprocess.run(
            ["systemctl", "is-active", service_name],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        return "1" if result.stdout.strip() == "active" else "0"
    except Exception:
        return "0"

# ----------------------------
# MAIN LOGIC
# ----------------------------
def send_data():
    print(f"Getting stats for IP: {ipAddress}")
    
    # --- PHASE 1: GATHER DATA & PRINT STATS ---
    
    # 1. Users
    user_count = get_wg_users()
    print(f"Total AmneziaWG Active Clients (last {HANDSHAKE_THRESHOLD}s): {user_count}")

    # 2. CPU
    cpu_val = get_cpu_usage_15min()
    print(f"CPU Utilization (15m avg): {cpu_val}%")
    
    # 3. Service Status
    svc_status = check_service_status(SERVICE_NAME)
    print(f"Service '{SERVICE_NAME}' status = {svc_status}")

    # 4. Historical Data
    vn_stats = get_vnstat_usage(NETWORK_INTERFACE)
    print(f"Historical Data -> Daily: {vn_stats['daily']} GB | Weekly: {vn_stats['weekly']} GB | Monthly: {vn_stats['monthly']} GB")

    # 5. Bandwidth Speed (Download Only)
    dl_mbps = get_download_speed(NETWORK_INTERFACE)
    print(f"Current Speed: {dl_mbps} Mbps (Download)")

    print("-" * 60) # Separator

    # --- PHASE 2: SEND TO API ---

    # Send Users
    try:
        url = f"{API_BASE_URL}/total-users/amnezia/{ipAddress}/{user_count}"
        resp = requests.post(url, timeout=10)
        print(f"[INFO] Users   → {resp.url} | Status: {resp.status_code}")
    except Exception as e:
        print(f"[ERROR] Users API: {e}")

    # Send CPU
    try:
        url = f"{API_BASE_URL}/cpu-usage/amnezia/{ipAddress}/{cpu_val}"
        resp = requests.post(url, timeout=10)
        print(f"[INFO] CPU     → {resp.url} | Status: {resp.status_code}")
    except Exception as e:
        print(f"[ERROR] CPU API: {e}")

    # Send Service Status
    try:
        url = f"{API_BASE_URL}/update-instance-status/{ipAddress}/amnezia/{PLATFORM}/{svc_status}"
        resp = requests.post(url, timeout=10)
        print(f"[INFO] Status  → {resp.url} | Status: {resp.status_code}")
    except Exception as e:
        print(f"[ERROR] Status API: {e}")

    # Send Speed (UPDATED ENDPOINT - Download Only)
    try:
        url = f"{API_BASE_URL}/server-speed/amnezia/{ipAddress}/{dl_mbps}"
        resp = requests.post(url, timeout=10)
        print(f"[INFO] Speed   → {resp.url} | Status: {resp.status_code}")
    except Exception as e:
        print(f"[ERROR] Bandwidth API: {e}")

    # Send History
    try:
        # Format: /historical-bandwidth/amnezia/{IP}/{Daily}/{Weekly}/{Monthly}
        url = f"{API_BASE_URL}/historical-bandwidth/amnezia/{ipAddress}/{vn_stats['daily']}/{vn_stats['weekly']}/{vn_stats['monthly']}"
        resp = requests.post(url, timeout=10)
        print(f"[INFO] History → {resp.url} | Status: {resp.status_code}")
    except Exception as e:
        print(f"[ERROR] History API: {e}")

if __name__ == "__main__":
    send_data()