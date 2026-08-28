#!/usr/bin/env python3
"""
Script 05 - Systemd Service Health Check + Auto-Start
Checks if a given systemd service is running.
If it is not running, it automatically attempts to start it.
No psutil needed - uses subprocess to call systemctl (the correct, minimal way).
"""
import subprocess


def check_and_start_service(service_name):
    """
    Checks if a systemd service is active.
    If not, attempts to start it and reports the result.
    """
    # Step 1: Ask systemd "is this service active right now?"
    # "systemctl is-active <service>" returns a single word:
    #   "active"       -> service is running normally
    #   "inactive"     -> service is stopped (not running)
    #   "failed"       -> service crashed / hit an error
    #   "activating"   -> service is starting up
    #   "deactivating" -> service is shutting down
    result = subprocess.run(
        ["systemctl", "is-active", service_name],
        capture_output=True,
        text=True
    )

    # stdout.strip() removes the trailing newline character
    status = result.stdout.strip()

    if status == "active":
        print(f"OK: {service_name} is running.")
        return

    # Step 2: Service is NOT active - print its current state
    print(f"WARNING: {service_name} is NOT running. Current status: [{status}]")
    print(f"Attempting to start {service_name}...")

    # Step 3: Try to start it using "systemctl start <service>"
    # Note: This requires root (sudo) privileges on most systems.
    start = subprocess.run(
        ["systemctl", "start", service_name],
        capture_output=True,
        text=True
    )

    # returncode == 0 means the command succeeded
    # returncode != 0 means it failed (e.g., permission denied, service not found)
    if start.returncode == 0:
        print(f"SUCCESS: {service_name} has been started successfully.")
    else:
        print(f"FAILED: Could not start {service_name}.")
        print(f"Error: {start.stderr.strip()}")


if __name__ == "__main__":
    # Change "nginx" to any service you want to check
    check_and_start_service("nginx")
