# 40 SRE Scripts

> A collection of Python scripts covering real-world SRE tasks and common interview questions.
> Each script lives in its own numbered folder with a dedicated README explaining the concept, approach, and SRE relevance.

## Script Index

| # | Script | Description | Platform |
|---|--------|-------------|----------|
| 01 | [Disk Usage Check](./01-disk-usage-check/) | Checks `/` disk usage via `shutil`, warns if > 80% | Linux + macOS |
| 02 | [Memory Usage Check](./02-memory-usage-check/) | Reads `/proc/meminfo` to check RAM, warns if > 80% | Linux |
| 03 | [CPU Usage Check](./03-cpu-usage-check/) | Reads `/proc/stat` twice to compute real CPU %, warns if > 80% | Linux |
| 04 | [Top CPU Processes](./04-top-cpu-processes/) | Identifies top 5 CPU-consuming processes via `/proc/<pid>/stat` delta | Linux |
| 05 | [Systemd Service Check](./05-systemd-service-check/) | Checks if a service is active; auto-starts it if not | Linux (systemd) |
| 06 | [Log Error Counter](./06-log-error-counter/) | Counts ERROR lines in a log file, alerts if above threshold | All platforms |
| 07 | [HTTP Health Check](./07-http-health-check/) | Checks if an HTTP endpoint is UP or DOWN with timeout handling | All platforms |
| 08 | [Largest Files Finder](./08-largest-files-finder/) | Recursively finds top 5 largest files in a directory | Linux + macOS |
| 09 | [TCP Port Checker](./09-tcp-port-checker/) | Tests if a TCP port is OPEN or CLOSED using raw sockets | All platforms |
| 10 | [Stale Log Checker](./10-stale-log-checker/) | Warns if a log file has not been written to in > 5 minutes | Linux + macOS |
| 11 | [Suspicious IP Detector](./11-suspicious-ip-detector/) | Finds IPs with > 5 failed login attempts in auth logs | All platforms |
| 12 | [HTTP Status Counter](./12-http-status-counter/) | Counts requests per HTTP status code from access logs | All platforms |
| 13 | [MariaDB Connection Check](./13-mariadb-connection-check/) | Verifies MariaDB is up by reading the MySQL protocol greeting packet | All platforms |

## How to Use

Each folder is self-contained. Navigate into a folder and run the script:

```bash
cd 13-mariadb-connection-check
python3 mariadb_connection_check.py
# or with a remote host:
python3 mariadb_connection_check.py db.prod.internal 3306
```

## Goal

- Build a hands-on library of **40 SRE-level Python scripts**
- Cover topics like: system monitoring, log parsing, alerting, process management, networking, security, database checks, Kubernetes, CI/CD helpers, and more
- Serve as an **interview preparation reference** with real, deep explanations

## Topics Covered (Planned)

- System resource monitoring (CPU, Memory, Disk, Network)
- Process management
- Log file analysis and alerting
- HTTP health checks and endpoint monitoring
- TCP/UDP port and connectivity checks
- Security: brute-force detection, auth log analysis
- HTTP access log analysis
- Database connectivity checks (MariaDB, PostgreSQL, Redis...)
- DNS lookups
- Alert thresholds and notifications
- Kubernetes and container basics
- Cron job utilities

---
> Scripts are written in pure Python using built-in modules wherever possible to demonstrate deep Linux and SRE knowledge.
