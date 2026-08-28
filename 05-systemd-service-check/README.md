# 05 - Systemd Service Health Check + Auto-Start

## The Interview Question

> *"Write a Python script that checks whether a given systemd service is running. If it's not running, print an appropriate message — and also start the service."*

---

## What This Script Does

1. Asks systemd whether a service is `active` (running)
2. If it is → prints **OK**
3. If it is **not** → prints a warning with the real status, then **attempts to start it**
4. Reports whether the start succeeded or failed (and shows the error if it failed)

---

## The Minimal, Interview-Ready Solution

```python
import subprocess

def check_and_start_service(service_name):
    result = subprocess.run(["systemctl", "is-active", service_name], capture_output=True, text=True)
    status = result.stdout.strip()

    if status == "active":
        print(f"OK: {service_name} is running.")
        return

    print(f"WARNING: {service_name} is NOT running. Status: [{status}]. Attempting start...")

    start = subprocess.run(["systemctl", "start", service_name], capture_output=True, text=True)

    if start.returncode == 0:
        print(f"SUCCESS: {service_name} started.")
    else:
        print(f"FAILED: {start.stderr.strip()}")

check_and_start_service("nginx")
```

**That is it. ~15 lines. No external libraries. This is exactly what the interviewer wants to see.**

---

## How We Achieved This — Step by Step

### Step 1: Why `subprocess` and not `os.system()`?

`os.system()` prints output directly to the terminal and only gives you the exit code.
You cannot capture the output to compare it in your Python code.

`subprocess.run()` gives you full control:

```
subprocess.run(
    ["systemctl", "is-active", "nginx"],  <- command as a list (safe, no shell injection)
    capture_output=True,                  <- capture stdout AND stderr into variables
    text=True                             <- decode bytes to Python string automatically
)
```

| Attribute | What it contains |
|-----------|-----------------|
| `result.stdout` | The text output of the command (what it printed) |
| `result.stderr` | Any error messages the command printed |
| `result.returncode` | 0 = success, non-zero = failure |

### Step 2: What is `systemctl is-active`?

`systemctl` is the command-line tool to control **systemd** — the process manager that runs everything on a modern Linux server.

`systemctl is-active <service>` prints exactly ONE word and exits:

```
active        -> The service is running and healthy
inactive      -> The service is stopped (not running, not crashed)
failed        -> The service ran but crashed / hit an error
activating    -> The service is still in the process of starting
deactivating  -> The service is shutting down
unknown       -> systemd has never heard of this service name
```

We compare `result.stdout.strip()` against `"active"`. The `.strip()` removes the trailing newline `\n` that the command adds.

### Step 3: `systemctl start` — starting the service

```python
start = subprocess.run(["systemctl", "start", service_name], capture_output=True, text=True)
```

This runs `systemctl start nginx` (or whatever service).
It does not print anything on success — it just returns exit code `0`.
On failure it returns a non-zero exit code and puts the error in `stderr`.

We check `start.returncode == 0` to know if it worked.

> **Important:** `systemctl start` requires **root/sudo** privileges. On a real server, this script would be run as root or via a sudoers rule.

---

## What the Interviewer Is Looking For

| What they check | What your script demonstrates |
|----------------|-------------------------------|
| Do you know systemd? | You used `systemctl is-active` — the real, official way |
| Do you know subprocess? | You used `capture_output=True` and `text=True` correctly |
| Can you handle failure? | You checked `returncode` and printed `stderr` on failure |
| Is your code minimal? | No unnecessary imports, no over-engineering |
| Do you understand Linux? | You know `active/inactive/failed` are real systemd states |

**The interviewer is NOT looking for:** reading `/proc` files manually, using psutil, or parsing `ps aux`.
For systemd services, `systemctl` IS the right tool — using it from Python via `subprocess` is the professional answer.

---

## How This Script Helps You Convince the Interviewer

In production SRE work, this pattern is everywhere:

- **Health check scripts** that run via cron every 5 minutes and restart dead services
- **Deployment pipelines** that verify a service came up after rolling it out
- **Runbooks-as-code**: Instead of "log in and manually restart nginx", automate it

Showing this in an interview proves you understand:
1. How Linux service management actually works (systemd)
2. How to interact with system tools from Python safely
3. How to write self-healing automation — a core SRE skill

---

## Sample Output

```bash
# When service IS running:
OK: nginx is running.

# When service is stopped and start succeeds:
WARNING: nginx is NOT running. Current status: [inactive]. Attempting start...
SUCCESS: nginx has been started successfully.

# When service is stopped and start fails (e.g. no root):
WARNING: nginx is NOT running. Current status: [inactive]. Attempting start...
FAILED: Could not start nginx.
Error: Failed to start nginx.service: Interactive authentication required.
```

---

## Usage

```bash
# Check nginx:
python3 systemd_service_check.py

# To check a different service, edit the last line:
# check_and_start_service("postgresql")
# check_and_start_service("docker")

# Starting services requires root:
sudo python3 systemd_service_check.py
```

## Requirements

- Python 3.x
- **Linux with systemd** (Ubuntu 16+, CentOS 7+, RHEL 7+, Debian 8+)
- `sudo` / root privileges to start services
- No third-party packages needed
