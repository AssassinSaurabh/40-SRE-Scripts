# 40 SRE Scripts

> A collection of Python scripts covering real-world SRE tasks and common interview questions.
> Each script lives in its own numbered folder with a dedicated README explaining the concept, approach, and SRE relevance.

## Script Index

| # | Script | Description | Linux Only |
|---|---|---|---|
| 01 | [Disk Usage Check](./01-disk-usage-check/) | Checks `/` disk usage, warns if > 80% | No (macOS too) |
| 02 | [Memory Usage Check](./02-memory-usage-check/) | Reads `/proc/meminfo` to check RAM, warns if > 80% | Yes |
| 03 | [CPU Usage Check](./03-cpu-usage-check/) | Reads `/proc/stat` twice to compute real CPU %, warns if > 80% | Yes |

## How to Use

Each folder is self-contained. Navigate into a folder and run the script:

```bash
cd 01-disk-usage-check
python3 disk_usage_check.py
```

## Goal

- Build a hands-on library of **40 SRE-level Python scripts**
- Cover topics like: system monitoring, log parsing, alerting, process management, networking, Kubernetes checks, CI/CD helpers, and more
- Serve as an **interview preparation reference** with real explanations

## Topics Covered (Planned)

- System resource monitoring (CPU, Memory, Disk, Network)
- Process management
- Log file analysis
- HTTP health checks
- DNS lookups
- Alert thresholds and notifications
- Kubernetes & container basics
- Cron job utilities

---
> Scripts are written in pure Python using built-in modules wherever possible to demonstrate deep Linux knowledge.
