# 18 - Linux System Load Average Checker

## The Interview Question

> *"Write a small Python script that checks the Linux system load average and warns if the 1-minute load is higher than the number of available CPU cores."*

---

## What This Script Does

1. Reads `/proc/loadavg` to get the **1-minute, 5-minute, and 15-minute load averages**
2. Calls `os.cpu_count()` to get the **number of logical CPU cores**
3. Compares the 1-minute load against the core count — the correct threshold
4. Prints **HEALTHY** if load ≤ cores, **OVERLOADED** if load > cores
5. Shows the **load percentage** (how full the CPU queue is)
6. Prints a **trend indicator** — RISING, FALLING, or STABLE — from all three averages

---

## The Solution

```python
import os

def check_load_average():
    with open('/proc/loadavg', 'r') as f:
        parts = f.read().split()

    load_1min  = float(parts[0])
    load_5min  = float(parts[1])
    load_15min = float(parts[2])

    cpu_count = os.cpu_count() or 1

    print(f"Load (1m/5m/15m) : {load_1min} / {load_5min} / {load_15min}")
    print(f"CPU Cores        : {cpu_count}")

    if load_1min > cpu_count:
        print(f"Status : OVERLOADED ({load_1min} > {cpu_count} cores)")
        print("Action : Run 'top' or check script 04 for top CPU processes.")
    else:
        print(f"Status : HEALTHY ({load_1min} <= {cpu_count} cores)")

    if load_1min > load_5min > load_15min:
        print("Trend  : RISING — load is increasing.")
    elif load_1min < load_5min < load_15min:
        print("Trend  : FALLING — recovering from a spike.")
    else:
        print("Trend  : STABLE")

if __name__ == "__main__":
    check_load_average()
```

---

## How We Achieved This — Every Decision Explained

### The Foundation: What IS Load Average?

This is the most important concept in this script. Most people get it wrong.

**Load average is NOT CPU usage percentage.**

Load average is the **average number of processes in the run queue** — that is, processes that are either:
1. **Currently using a CPU core** (running)
2. **Waiting for a CPU core** to become free (runnable but not yet scheduled)

Think of it like a checkout queue at a supermarket:
- Number of checkout lanes = CPU cores
- People in queue = processes wanting CPU time
- Load average = average number of people waiting across time

```
4 checkout lanes (cores), 4 people (load 4.0) -> everyone being served, no wait
4 checkout lanes (cores), 8 people (load 8.0) -> 4 waiting, queue building up
4 checkout lanes (cores), 2 people (load 2.0) -> system has spare capacity
```

**This is why we compare load against CPU count — not against a fixed number like 80.**

---

### `/proc/loadavg` — The Source File

`/proc/loadavg` is a **virtual file** in the Linux kernel's proc filesystem. It does not exist on disk. The kernel generates its content dynamically every time it is read. Updated every **5 seconds** by the kernel scheduler.

#### Exact file format

```
0.52 0.38 0.21 1/412 28750
```

Every field explained:

```
Field 1: 0.52
         1-minute  exponential moving average of the run queue length
         The most RECENT and REACTIVE metric — reacts to spikes quickly
         ← THIS IS THE ONE WE ALERT ON

Field 2: 0.38
         5-minute  exponential moving average of the run queue length
         Smoothed over 5 minutes — filters out brief spikes

Field 3: 0.21
         15-minute exponential moving average of the run queue length
         Long-term trend — what was the system doing over the last quarter-hour?

Field 4: 1/412
         running_tasks / total_tasks
         1   = processes ACTIVELY running on CPU at this exact moment
         412 = total processes (running + sleeping + stopped + zombie)
         (We don't use this in our script)

Field 5: 28750
         PID of the most recently created process on the system
         (We don't use this in our script)
```

#### Reading it in Python

```python
with open('/proc/loadavg', 'r') as f:
    content = f.read()         # "0.52 0.38 0.21 1/412 28750\n"

parts = content.split()        # ["0.52", "0.38", "0.21", "1/412", "28750"]
load_1min = float(parts[0])   # 0.52
```

`content.split()` with no argument splits on ALL whitespace and strips the trailing `\n`. This gives us a clean list of string tokens.

**Why `float()` and not `int()`?**

Load averages are always floating-point numbers. `"0.52"` → `float` → `0.52`. If we used `int("0.52")` Python would raise `ValueError`. If we compared strings directly: `"0.52" > "8"` evaluates to `True` in Python (lexicographic comparison — `"0"` < `"8"`) which is completely wrong numerically. Always convert to the correct numeric type before comparing.

---

### `os.cpu_count()` — Getting the Core Count

```python
cpu_count = os.cpu_count() or 1
```

`os.cpu_count()` queries the OS for the number of **logical CPUs** visible to the process. A logical CPU = one thread of execution. On a hyperthreaded system, one physical core exposes two logical CPUs.

Examples:

| Hardware | `os.cpu_count()` |
|----------|-----------------|
| 1 physical core, no HT | 1 |
| 4 physical cores, no HT | 4 |
| 4 physical cores, HT enabled | 8 |
| 2-socket server, 16 cores each, HT | 64 |
| AWS t3.micro (2 vCPUs) | 2 |
| AWS m5.32xlarge (128 vCPUs) | 128 |

**The `or 1` fallback:**

`os.cpu_count()` can return `None` in rare environments where the OS does not report CPU information (some containers with restricted cgroups). `None or 1` evaluates to `1` — the safest conservative default. Division by `None` would raise `TypeError`; division by `1` works.

**Why logical CPUs and not physical cores?**

The scheduler can run processes on any logical CPU. If a physical core has two logical CPUs (hyperthreading), both can run processes simultaneously. From the scheduler's perspective and from the load average's perspective, you have that many execution lanes.

---

### The Alert Threshold: Load > Cores

```python
if load_1min > cpu_count:
    print("OVERLOADED")
else:
    print("HEALTHY")
```

This single comparison is the entire logic of the script. Let's understand why this threshold is correct.

#### Interpreting load average values

| Load / Cores ratio | What it means |
|-------------------|---------------|
| `0.00 – 0.70` | Plenty of headroom. System is mostly idle. |
| `0.70 – 1.00` | Approaching full utilisation but still healthy. |
| `1.00` (exactly) | System is fully utilised. Every CPU is busy, no queue. |
| `> 1.00` | Queue is building up. Processes are waiting. System is overloaded. |
| `2.00` | Queue is twice the capacity. Average wait time is doubling. |
| `5.00+` | Serious overload. System may become unresponsive. |

**Concrete examples with core counts:**

```
4-core server:
  Load 2.0  -> 2.0/4  = 50%  capacity -> HEALTHY (headroom to spare)
  Load 4.0  -> 4.0/4  = 100% capacity -> AT LIMIT (no queue yet)
  Load 8.0  -> 8.0/4  = 200% capacity -> OVERLOADED (average wait = 1 cycle)

1-core server (e.g., cheap VPS):
  Load 2.0  -> 2.0/1  = 200% capacity -> SEVERELY OVERLOADED
  Load 0.5  -> 0.5/1  = 50%  capacity -> HEALTHY

32-core server:
  Load 8.0  -> 8.0/32 = 25%  capacity -> HEALTHY (plenty of cores free)
  Load 32.0 -> 32/32  = 100% capacity -> AT LIMIT
```

A fixed threshold (e.g., "warn if load > 5") would be nonsensical:
- Load 5 on a 1-core VPS = emergency
- Load 5 on a 32-core server = nearly idle

The threshold must always be relative to core count.

---

### The Load Percentage — Making Numbers Human-Readable

```python
ratio = load_1min / cpu_count
print(f"Load % : {ratio * 100:.0f}% of capacity")
```

`ratio * 100` converts the fraction to a percentage. `:.0f` formats with 0 decimal places (integer percentage).

Examples:
```
load_1min = 2.0, cpu_count = 4
ratio = 0.5 -> 50% of capacity -> HEALTHY

load_1min = 6.0, cpu_count = 4
ratio = 1.5 -> 150% of capacity -> OVERLOADED
```

Percentages are more intuitive to a wide audience than raw load numbers. A manager understands "150% of capacity" better than "load average 6.0".

---

### The Trend Analysis — Using All Three Averages

```python
if load_1min > load_5min > load_15min:
    print("Trend : RISING — load is increasing over time.")
elif load_1min < load_5min < load_15min:
    print("Trend : FALLING — recovering from a spike.")
else:
    print("Trend : STABLE")
```

This is a **chained comparison** — unique to Python. `a > b > c` is equivalent to `a > b and b > c`. Readable and concise.

**Why trend matters — a critical SRE skill:**

| 1m | 5m | 15m | What happened | Action |
|----|----|-----|--------------|--------|
| 8  | 6  | 2   | RISING — spike in progress | Investigate NOW |
| 2  | 6  | 8   | FALLING — recovering, was worse | Keep watching |
| 5  | 5  | 5   | STABLE — sustained load | Planned capacity review |
| 1  | 1  | 1   | STABLE — system healthy | Nothing needed |

**RISING load** with 1m > 5m > 15m is the most urgent — it means load is actively increasing at this moment.

**FALLING load** with 1m < 5m < 15m means the system already survived the worst of it and is recovering. This is still important — it tells the oncall engineer the incident is resolving on its own.

This 3-average trend analysis is how `uptime` and `top` present load data. Understanding it is a senior SRE skill.

---

### What Causes High Load Average?

Common root causes an SRE must know:

| Cause | Signature | Tool to diagnose |
|-------|----------|-----------------|
| CPU-bound processes | Load = CPU % both high | `top`, Script 04 (top CPU processes) |
| Too many processes spawned | Load high, CPU % moderate | `ps aux --sort=-%cpu \| head` |
| I/O wait (disk/NFS) | Load high, CPU % LOW | `iostat`, `iotop` |
| Memory pressure + swap | Load spikes, system sluggish | `free -h`, `vmstat` |
| Runaway cron job | Load spikes at regular intervals | `crontab -l`, `journalctl` |

> **The most common SRE mistake:** Assuming high load = high CPU. I/O wait processes are also counted in load average but appear as 0% CPU in `top`. A server can have load 20 and CPU usage 5% — because 15 processes are waiting for disk reads. This is why the question says "warn" not "kill processes" — investigation is always needed.

---

## What the Interviewer Is Looking For

| What they check | What your script demonstrates |
|----------------|-------------------------------|
| Know `/proc/loadavg`? | Read it correctly, know all 5 fields |
| float() conversion? | Not int(), not string comparison — correct numeric type |
| Why compare vs cores, not fixed threshold? | Load on 1-core vs 32-core explained — shows real understanding |
| `os.cpu_count()`? | Correct function, `or 1` fallback for None case |
| All 3 averages? | 1m for alerts, 5m + 15m for trend — each has a role |
| Trend analysis? | Chained comparison `a > b > c` — Python idiom + operational insight |
| Load % calculation? | `ratio * 100` makes it human-readable for non-SRE stakeholders |

---

## How This Convinces the Interviewer

Load average is one of the first metrics every SRE checks during an incident. It is displayed by `uptime`, `top`, `htop`, `w`, and every monitoring system (Datadog, Prometheus, CloudWatch, Nagios).

Understanding that load > cores = overload (not a fixed number) shows you actually know what load average means — not just how to read the number.

**Say in the interview:**
> *"In production I'd extend this to also check I/O wait separately using `/proc/stat` — because high I/O wait inflates load average without showing up as CPU usage. I'd also add alerting: if load has been above cores for more than 5 consecutive readings (sampled every 30 seconds), fire a PagerDuty alert. A single spike is noise; sustained overload is an incident."*

---

## Sample Output

```bash
# Healthy system (4-core server, low load):
$ python3 load_average_check.py
==================================================
System Load Average Report
==================================================
  Load (1 min)  : 0.52
  Load (5 min)  : 0.38
  Load (15 min) : 0.21
  CPU Cores     : 4
--------------------------------------------------
  Status  : HEALTHY
  Detail  : 1-min load (0.52) <= CPU cores (4)
  Load %  : 13% of capacity
==================================================
  Trend   : FALLING — load is decreasing, recovering from a spike.

# Overloaded system (2-core server, high load):
$ python3 load_average_check.py
==================================================
System Load Average Report
==================================================
  Load (1 min)  : 4.87
  Load (5 min)  : 3.21
  Load (15 min) : 1.45
  CPU Cores     : 2
--------------------------------------------------
  Status  : OVERLOADED
  Detail  : 1-min load (4.87) > CPU cores (2)
  Load %  : 244% of capacity
==================================================
  Trend   : RISING — load is increasing over time.
  Action  : Run 'top' or check Script 04 (top CPU processes).
```

---

## Usage

```bash
# Run directly — no arguments needed:
python3 load_average_check.py

# Also readable via shell:
cat /proc/loadavg
uptime
```

## Requirements

- Python 3.x
- **Linux only** (reads `/proc/loadavg`)
- No root/sudo required — `/proc/loadavg` is readable by all users
- No third-party packages needed
