# 40 SRE Scripts

> A hands-on library of Python scripts covering real-world Site Reliability Engineering tasks and common interview questions.
> Every script is self-contained with a deep README that explains the **why**, the **how**, and what the interviewer is looking for.

---

## 📋 Script Index

| # | Folder | What It Does | Key Concept | Platform |
|---|--------|-------------|-------------|----------|
| 01 | [disk-usage-check](./01-disk-usage-check/) | Checks `/` filesystem usage, warns if > 80% | `shutil.disk_usage()` | Linux + macOS |
| 02 | [memory-usage-check](./02-memory-usage-check/) | Parses `/proc/meminfo` to check available RAM | `/proc/meminfo` parsing | Linux |
| 03 | [cpu-usage-check](./03-cpu-usage-check/) | Two-snapshot delta on `/proc/stat` for real CPU % | `/proc/stat` delta method | Linux |
| 04 | [top-cpu-processes](./04-top-cpu-processes/) | Ranks top 5 CPU-hungry processes without psutil | `/proc/<pid>/stat` delta | Linux |
| 05 | [systemd-service-check](./05-systemd-service-check/) | Checks service state; auto-starts if inactive | `subprocess` + `systemctl` | Linux (systemd) |
| 06 | [log-error-counter](./06-log-error-counter/) | Counts ERROR lines; alerts if above threshold | Line-by-line file iteration | All platforms |
| 07 | [http-health-check](./07-http-health-check/) | Checks HTTP endpoint — prints UP or DOWN | `urllib`, timeout, HTTPError vs URLError | All platforms |
| 08 | [largest-files-finder](./08-largest-files-finder/) | Recursively finds top 5 largest files | `os.walk()`, symlink safety | Linux + macOS |
| 09 | [tcp-port-checker](./09-tcp-port-checker/) | Tests if a TCP port is OPEN or CLOSED | Raw socket, 3-way handshake | All platforms |
| 10 | [stale-log-checker](./10-stale-log-checker/) | Warns if a log file hasn't been written to in > 5 min | `os.path.getmtime()`, Unix timestamps | Linux + macOS |
| 11 | [suspicious-ip-detector](./11-suspicious-ip-detector/) | Flags IPs with > 5 failed login attempts | Dict counting, `dict.get()` pattern | All platforms |
| 12 | [http-status-counter](./12-http-status-counter/) | Counts requests per HTTP status code from access logs | Combined Log Format parsing, `dict.get()` | All platforms |
| 13 | [mariadb-connection-check](./13-mariadb-connection-check/) | Verifies MariaDB is live by reading the MySQL protocol greeting | MySQL protocol bytes, `greeting[4]` | All platforms |
| 14 | [redis-connection-check](./14-redis-connection-check/) | Sends RESP PING, verifies PONG, reports RTT latency | RESP protocol, `sendall`, latency measurement | All platforms |
| 15 | [port-process-finder](./15-port-process-finder/) | Finds which process owns a TCP port | `ss -lptn`, subprocess, regex capture groups | Linux |
| 16 | [config-file-diff](./16-config-file-diff/) | Compares two config files; reports missing/changed lines | `difflib.unified_diff()`, unified diff format | All platforms |
| 17 | [http-retry-health-check](./17-http-retry-health-check/) | Health check with 3 retries and exponential backoff | Retry loop, `2^attempt` backoff, HTTPError vs URLError | All platforms |

---

## 🚀 Quick Start

Each script is self-contained. Clone the repo, navigate to any folder, and run:

```bash
git clone https://github.com/AssassinSaurabh/40-SRE-Scripts.git
cd 40-SRE-Scripts

# Example: check disk usage
python3 01-disk-usage-check/disk_usage_check.py

# Example: find who's using port 8080
python3 15-port-process-finder/port_process_finder.py 8080

# Example: compare two config files
python3 16-config-file-diff/config_diff.py server1.conf server2.conf

# Example: health check with retry
python3 17-http-retry-health-check/http_retry_health_check.py https://myapp.com/health
```

---

## 📚 What Each README Contains

Every script folder has a `README.md` with these sections:

1. **The Interview Question** — exact phrasing as asked in real interviews
2. **What This Script Does** — numbered list of what the script actually does
3. **The Solution** — the minimal clean code block
4. **How We Achieved This** — every line explained from first principles (baby-level for `/proc` scripts)
5. **What the Interviewer Is Looking For** — table format covering each evaluation criterion
6. **How This Convinces the Interviewer** — production context + what to say out loud
7. **Sample Output** — exact terminal output for each scenario
8. **Usage** — copy-paste commands

---

## 🗺️ Topics Covered

| Category | Scripts |
|----------|---------|
| **System Monitoring** | 01 Disk, 02 Memory, 03 CPU, 04 Top Processes |
| **Process & Service Management** | 05 Systemd, 15 Port Finder |
| **Log Analysis** | 06 Error Counter, 10 Stale Log, 11 Suspicious IPs, 12 HTTP Status |
| **Network & Connectivity** | 07 HTTP Check, 09 TCP Port, 17 Retry Health Check |
| **Database Checks** | 13 MariaDB, 14 Redis |
| **File & Config** | 08 Largest Files, 16 Config Diff |

**Coming soon:** DNS lookup, PostgreSQL check, Kubernetes pod status, disk I/O monitor, alert thresholds, cron job utilities, deployment verification scripts.

---

## 🎯 Goal

Build 40 production-grade SRE Python scripts that:
- Use **Python built-in modules only** (no psutil, no requests, no third-party libs unless the question requires it)
- Demonstrate deep understanding of **Linux internals** (`/proc`, `ss`, `systemctl`, log formats)
- Show **protocol-level knowledge** (MySQL greeting packet, RESP PING/PONG, TCP handshake)
- Are ready to **copy-paste and run** on any Linux server

---

> Written with deep explanations so that even someone new to SRE can understand not just the *what* but the *why* behind every line.
