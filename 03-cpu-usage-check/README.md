# 03 - CPU Usage Check

## What This Script Does

This script monitors **CPU utilization** on a Linux system by reading `/proc/stat` twice with a 1-second interval.
It calculates real CPU usage from the delta between two snapshots — the same method used by tools like `top` and `vmstat`.

## How It Works

1. **Snapshot 1**: Reads the first line of `/proc/stat` (aggregate CPU stats).
2. Waits **1 second** using `time.sleep(1)`.
3. **Snapshot 2**: Reads `/proc/stat` again.
4. Calculates the **delta** (difference) for total and idle CPU ticks.
5. Computes CPU usage:
   ```
   busy_diff  = total_diff - idle_diff
   usage_%    = (busy_diff / total_diff) * 100
   ```
6. Compares against an **80% threshold**:
   - Above 80% → prints a **WARNING**
   - At or below 80% → prints **CPU is healthy**

## Why Two Snapshots?

`/proc/stat` reports **cumulative** CPU ticks since boot. A single reading is useless for current usage.
Taking two readings and computing the delta gives the actual CPU activity during that interval.
This is exactly how system utilities like `top`, `htop`, and `mpstat` work internally.

## /proc/stat CPU Line Format

```
cpu  user nice system idle iowait irq softirq steal guest guest_nice
```

| Index | Field | Meaning |
|---|---|---|
| 3 | idle | Time spent doing nothing |
| 4 | iowait | Time waiting for I/O |

`idle_time = numbers[3] + numbers[4]` (both are "not doing real work")

## SRE Relevance

CPU saturation causes request queuing, latency spikes, and service degradation. SREs monitor CPU to:
- Detect runaway processes or hot threads
- Trigger auto-scaling actions
- Diagnose performance incidents using the USE method (Utilization, Saturation, Errors)

## Interview Insight

> **Q: How do you measure CPU usage in Python on Linux without psutil?**
> A: Read `/proc/stat` twice with a time gap, compute the delta of idle vs total ticks, and derive the busy percentage.

## Usage

```bash
python3 cpu_usage_check.py
```

## Sample Output

```
Taking Snapshot 1...
Taking Snapshot 2...
CPU is healthy. Current usage: 12.45%
# or
Taking Snapshot 1...
Taking Snapshot 2...
WARNING: CPU usage is high at 91.30%!
```

## Requirements

- Python 3.x
- **Linux only** (requires `/proc/stat`)
- No third-party packages needed
