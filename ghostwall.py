#!/usr/bin/env python3
import os
import time
import platform
import subprocess
import requests
from datetime import datetime
from rich.live import Live
from rich.table import Table
from rich.console import Console
from random import choice

console = Console()

# === Configuration ===
BLOCK_THRESHOLD = 10
SCORE_RULES = {
    "port_scan": 5,
    "geo_blocked": 7,
    "rapid_hits": 4,
    "real_connection": 2
}
BLOCKED_IPS_LOG = "logs/blocked.log"
SCORES = {}
REASONS = {}
SEEN_IPS = set()
WHITELIST = set()
GEO_BLOCKED_COUNTRIES = ["RU", "CN", "KP"]

os.makedirs("logs", exist_ok=True)

IS_WINDOWS = platform.system().lower().startswith("win")

# === GeoIP Lookup ===
def get_country_by_ip(ip):
    try:
        response = requests.get(f"https://ipapi.co/{ip}/country/", timeout=3)
        if response.status_code == 200:
            return response.text.strip()
        return "??"
    except:
        return "??"

# === Block IP (Linux only) ===
def block_ip(ip, reason=""):
    if ip in WHITELIST or IS_WINDOWS:
        return
    subprocess.call(["sudo", "iptables", "-A", "INPUT", "-s", ip, "-j", "DROP"])
    log_block(ip, reason)
    REASONS[ip] = f"❌ Blocked ({reason})"

# === Logging ===
def log_block(ip, reason):
    with open(BLOCKED_IPS_LOG, "a") as f:
        f.write(f"[{datetime.now()}] Blocked IP: {ip} | Reason: {reason}\n")

# === Score Handling ===
def apply_score(ip, reason, score):
    if ip not in SCORES:
        SCORES[ip] = 0
        REASONS[ip] = ""
    SCORES[ip] += score
    if "Blocked" not in REASONS[ip]:
        REASONS[ip] = reason
    if SCORES[ip] >= BLOCK_THRESHOLD:
        block_ip(ip, f"{reason} | Score: {SCORES[ip]}")

# === Monitor Real Traffic ===
def monitor_real_traffic():
    try:
        cmd = ["netstat", "-an"] if IS_WINDOWS else ["netstat", "-ntu"]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
        lines = result.stdout.splitlines()

        for line in lines:
            if any(state in line for state in ["ESTABLISHED", "SYN_RECV"]):
                parts = line.split()
                remote = parts[-2] if IS_WINDOWS else parts[4]
                ip = remote.split(":")[0]

                if ip.startswith("127.") or ip.startswith("192.168.") or ip in SEEN_IPS:
                    continue

                SEEN_IPS.add(ip)
                country = get_country_by_ip(ip)
                if country in GEO_BLOCKED_COUNTRIES:
                    apply_score(ip, f"Blocked Country ({country})", SCORE_RULES["geo_blocked"])
                else:
                    apply_score(ip, "real_connection", SCORE_RULES["real_connection"])
    except Exception as e:
        console.print(f"[red]Error monitoring traffic: {e}[/]")

# === CLI Table Dashboard ===
def generate_dashboard():
    table = Table(title="🛡️ GhostWall — Live IP Monitor", style="bold cyan")
    table.add_column("IP", style="bold white")
    table.add_column("Country", style="green")
    table.add_column("Score", style="yellow")
    table.add_column("Reason", style="magenta")

    sorted_ips = sorted(SCORES.items(), key=lambda x: x[1], reverse=True)

    for ip, score in sorted_ips:
        country = get_country_by_ip(ip)
        status = REASONS.get(ip, "-")
        table.add_row(ip, country, str(score), status)

    return table

# === Simulate Traffic (for demo/testing) ===
def simulate_traffic():
    test_ips = [
        "103.54.22.1",     # Simulated RU
        "81.2.69.142",     # Simulated CN
        "106.51.72.21",    # Simulated IN
        "192.168.1.10"      # Local
    ]
    for _ in range(5):
        ip = choice(test_ips)
        action = choice(list(SCORE_RULES.keys()))
        score = SCORE_RULES[action]
        country = get_country_by_ip(ip)
        if action == "geo_blocked" and country in GEO_BLOCKED_COUNTRIES:
            apply_score(ip, f"Blocked Country ({country})", score)
        else:
            apply_score(ip, action, score)
        time.sleep(1)

# === Main ===
if __name__ == "__main__":
    console.print("[bold green]🔐 GhostWall v0.4 Running with CLI Dashboard...[/]")

    simulate_traffic()  # Optional test

    try:
        with Live(generate_dashboard(), refresh_per_second=0.5) as live:
            while True:
                monitor_real_traffic()
                live.update(generate_dashboard())
                time.sleep(3)
    except KeyboardInterrupt:
        console.print("[bold red]🛑 Stopped by user.[/]")
