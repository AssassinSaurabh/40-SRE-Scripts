# 04 - Top CPU Consuming Processes

## The Interview Question

> *"A production Linux server is reporting high resource utilization. Write a Python script that identifies the top CPU consuming processes and reports their PID, process name, and CPU usage."*
>
> **Constraint:** You cannot use `psutil`, and you cannot simply execute `ps aux` and parse its output.

---

## What This Script Does

This script finds the **Top 5 CPU-consuming processes** on a Linux system by:
1. Reading `/proc/<pid>/stat` for every running process (Snapshot 1)
2. Waiting 1 second
3. Reading them again (Snapshot 2)
4. Computing the **delta** (difference) to find actual live CPU usage
5. Printing a sorted table like `top` or `htop` does

**No psutil. No shell commands. Pure Python + Linux `/proc` filesystem.**

---

## Sample Output

```
Gathering Snapshot 1...
Gathering Snapshot 2...

PID      PROCESS              CPU %
----------------------------------------
1337     chrome               87.3%
982      python3              34.1%
501      kworker/u8:2         12.0%
204      Xorg                 5.4%
88       systemd-journald     1.1%
```

---

## Deep Dive: The Linux `/proc` Filesystem

### What is `/proc`?

`/proc` is a **virtual filesystem** — it does not exist on disk.
The Linux kernel creates it in memory and exposes it as if it were a regular folder.
Every time you read a file inside `/proc`, the kernel generates the content on-the-fly from live kernel data structures.

Think of it like this:
```
/proc/
├── 1/             <- Process with PID 1 (init/systemd)
│   └── stat       <- CPU accounting for PID 1
├── 982/           <- Process with PID 982
│   └── stat       <- CPU accounting for PID 982
├── cpuinfo        <- Info about your CPU hardware
├── meminfo        <- RAM statistics
└── stat           <- System-wide CPU statistics (ALL processes combined)
```

Every numbered folder = one running process. The folder disappears the moment the process dies.

---

## Deep Dive: `/proc/stat` (System-Wide CPU Ticks)

This file holds **aggregate CPU statistics** across the entire system, for every CPU core combined.

### What it looks like

```
cpu  274042 2002 79541 10493813 14350 0 1270 0 0 0
cpu0 68510  501  19885 2623453  3587  0 317  0 0 0
cpu1 68760  500  19885 2623453  3587  0 317  0 0 0
cpu2 68386  500  19885 2623453  3587  0 317  0 0 0
cpu3 68386  501  19886 2623454  3589  0 319  0 0 0
intr 45678901 ...
ctxt 12345678
btime 1692000000
processes 45678
procs_running 3
procs_blocked 0
```

### The First Line Explained — Column by Column

```
cpu  274042   2002    79541    10493813  14350    0     1270     0      0      0
     |        |       |        |         |        |     |        |      |      |
     user     nice    system   idle      iowait   irq   softirq  steal  guest  guest_nice
```

All values are in **jiffies** (clock ticks). On most Linux systems, **1 jiffy = 10ms** (100 ticks per second per core).

| Column | Name | What it means — baby-level explanation |
|--------|------|----------------------------------------|
| 1 | `user` | Time the CPU spent running YOUR programs (apps, scripts, etc.) in normal mode |
| 2 | `nice` | Time spent running programs that were deliberately slowed down (low-priority tasks) |
| 3 | `system` | Time the CPU spent inside the kernel — e.g., writing files, opening sockets |
| 4 | `idle` | Time the CPU did literally **nothing** (just waiting). This is "free time" |
| 5 | `iowait` | Time the CPU was waiting for a disk or network operation to finish |
| 6 | `irq` | Time spent handling hardware interrupts (keyboard press, NIC received a packet) |
| 7 | `softirq` | Time spent handling software interrupts (kernel-internal tasks) |
| 8 | `steal` | On a VM/cloud server — time the hypervisor "stole" from your VM to give to another |
| 9 | `guest` | Time spent running a virtual CPU for a guest OS (if you are running a VM inside your server) |
| 10 | `guest_nice` | Same as guest, but for niced guest processes |

### Why we sum ALL columns

```python
parts = line.split()[1:]        # Remove the "cpu" label
return sum(int(x) for x in parts)  # Sum everything
```

We sum everything because **ALL of it represents time the CPU was ticking away**, whether busy or idle.
This total is our **denominator** — the 100% baseline.
When we compute a process's share, we ask: *"Out of all the ticks that passed, how many did this process use?"*

---

## Deep Dive: `/proc/<pid>/stat` (Per-Process CPU Ticks)

This file holds **CPU accounting for one specific process**. Every running process has its own copy.

### What it looks like (raw)

```
1234 (my web server) S 1 1234 1234 0 -1 4194304 1234 0 0 0 58 12 0 0 20 0 5 0 12345678 987654321 9876 18446744073709551615 0 0 0 0 0 0 0 0 0 0 0 0 17 3 0 0 0 0 0
```

That's one long line. Let's break it apart field by field:

### Field Map (kernel-documented, 1-indexed)

```
Field  1 : pid          = 1234                 <- Process ID
Field  2 : comm         = (my web server)      <- Process name in parentheses
Field  3 : state        = S                    <- S=Sleeping R=Running Z=Zombie D=Disk-wait
Field  4 : ppid         = 1                    <- Parent process ID (who launched this)
Field  5 : pgrp         = 1234                 <- Process group ID
Field  6 : session      = 1234                 <- Session ID
Field  7 : tty_nr       = 0                    <- Terminal number (0 = no terminal)
Field  8 : tpgid        = -1                   <- Terminal process group ID
Field  9 : flags        = 4194304              <- Kernel flags (bitmask)
Field 10 : minflt       = 1234                 <- Minor page faults (no disk needed)
Field 11 : cminflt      = 0                    <- Minor page faults of waited-for children
Field 12 : majflt       = 0                    <- Major page faults (needed disk access)
Field 13 : cmajflt      = 0                    <- Major page faults of children
Field 14 : utime        = 58     *** WE USE THIS ***  <- Ticks in USER mode
Field 15 : stime        = 12     *** WE USE THIS ***  <- Ticks in KERNEL mode
Field 16 : cutime       = 0                    <- User ticks of waited-for children
Field 17 : cstime       = 0                    <- Kernel ticks of waited-for children
Field 18 : priority     = 20                   <- Scheduling priority
Field 19 : nice         = 0                    <- Nice value (-20 to 19)
Field 20 : num_threads  = 5                    <- Number of threads in this process
...and many more fields we don't need...
```

### The Two Fields We Care About

| Field | Name | Baby explanation |
|-------|------|-----------------|
| **Field 14** | `utime` | How many ticks this process spent running **your code** (user space) |
| **Field 15** | `stime` | How many ticks this process spent doing **kernel stuff** (reading files, network calls) |

**Total CPU ticks for this process = `utime + stime`**

These are **cumulative since the process started** — so a process that started yesterday has large numbers.
That's why we need two snapshots and take the DIFFERENCE.

### The Tricky Parsing Problem — Spaces in Process Names

The process name field (Field 2) is wrapped in parentheses, BUT process names can contain spaces!

```
# Normal case:
982 (python3) S 1 982 ...

# Tricky case (spaces in name):
1337 (Web Content) S 1 1337 ...

# Even trickier:
4421 (kworker/0:1H-mm) S 2 0 ...
```

A naive `line.split()` would break `"Web Content"` into two separate tokens.

**The SRE Trick — split on delimiters, not spaces:**

```python
# Step 1: Split ONCE on " (" to separate PID from everything else
# "1337 (Web Content) S 1 1337 ..."
#  becomes:
#    pid_str = "1337"
#    rest    = "Web Content) S 1 1337 ..."
pid_str, rest = stat_line.split(" (", 1)

# Step 2: Split ONCE on ") " to extract the name
# "Web Content) S 1 1337 ..."
#  becomes:
#    comm = "Web Content"       <- full name, spaces preserved!
#    rest = "S 1 1337 ..."      <- remaining fields
comm, rest = rest.split(") ", 1)

# Step 3: Now split the rest by space normally
stats = rest.split()
# stats[0] = "S"       (state)
# stats[1] = "1"       (ppid)
# ...continuing...
# stats[11] = utime     <- index 11 because we already removed field 1 (pid) and field 2 (name)
# stats[12] = stime
```

### Why index 11 and 12?

After extracting PID and name (fields 1 and 2), the `rest` string starts at **field 3 (state)**.
When we do `stats = rest.split()`, the 0-based indexing shifts:

```
Field in kernel docs    -> Index in stats[] array
Field  3 (state)        -> stats[0]
Field  4 (ppid)         -> stats[1]
Field  5 (pgrp)         -> stats[2]
Field  6 (session)      -> stats[3]
Field  7 (tty_nr)       -> stats[4]
Field  8 (tpgid)        -> stats[5]
Field  9 (flags)        -> stats[6]
Field 10 (minflt)       -> stats[7]
Field 11 (cminflt)      -> stats[8]
Field 12 (majflt)       -> stats[9]
Field 13 (cmajflt)      -> stats[10]
Field 14 (utime)        -> stats[11]  *** HERE ***
Field 15 (stime)        -> stats[12]  *** HERE ***
```

---

## Deep Dive: The CPU % Formula

```
cpu_percent = (proc_diff / sys_time_diff) * 100 * num_cores
```

Let's trace through a real example:

```
Setup: 4-core machine, 1-second interval

System total ticks (all cores):
  Snapshot 1: 10,000 ticks
  Snapshot 2: 10,400 ticks
  sys_time_diff = 400 ticks

Process "chrome":
  Snapshot 1: 5,000 ticks (cumulative since start)
  Snapshot 2: 5,100 ticks (cumulative since start)
  proc_diff = 100 ticks used in last 1 second

Without cores:  (100 / 400) * 100 = 25%
  -> chrome used 25% of total system capacity
  -> On a 4-core machine, this means it used 1 full core

With cores:     25% * 4 = 100%
  -> Displayed as 100% = "using 1 full CPU core"
  -> This matches what top/htop shows
```

**Why multiply by cores?**
`/proc/stat`'s `cpu` line sums ALL cores. If 4 cores each tick 100 times per second,
`sys_time_diff` = 400 for 1 second. A process on 1 full core contributes 100 ticks.
Without the cores multiplier: `(100/400)*100 = 25%` — technically correct as system share.
With the cores multiplier: `25% * 4 = 100%` — matches `top`'s display (100% = 1 full core).

---

## Race Conditions — Why We Ignore Missing Processes

```python
except (FileNotFoundError, ProcessLookupError, IndexError):
    pass
```

Linux is a live system. Between the moment we call `os.listdir("/proc")` and the moment we open
`/proc/982/stat`, that process might have died. This is normal — especially on busy servers.

| Exception | When it happens |
|-----------|----------------|
| `FileNotFoundError` | Process exited between listing and opening |
| `ProcessLookupError` | PID table entry removed by kernel |
| `IndexError` | File was partially written (kernel race) |

We don't crash. We silently skip. A production monitoring script **must** be resilient to this.

---

## SRE Relevance

| Scenario | How this script helps |
|----------|-----------------------|
| CPU saturation incident | Quickly identify the runaway process eating CPU |
| "top is not installed" | Works with zero external tools — just Python + Linux |
| Performance regression | Automate CPU profiling in CI/CD pipelines |
| Security incident | Spot unexpected processes consuming abnormal CPU (cryptominer, etc.) |

---

## Interview Q&A

> **Q: Why two snapshots instead of reading once?**
> A: `/proc/<pid>/stat` gives **cumulative** ticks since process start. Absolute values tell you nothing about "right now". The delta over a known time window gives actual current CPU rate.

> **Q: Why split on `" ("` instead of splitting by spaces?**
> A: Process names (field 2 in `/proc/<pid>/stat`) are wrapped in parentheses and CAN contain spaces. `" ("` and `") "` are the reliable delimiters guaranteed by the kernel format.

> **Q: Why multiply by `os.cpu_count()`?**
> A: `/proc/stat`'s `cpu` line is the aggregate across all cores. Multiplying normalizes the percentage to "cores used" scale, matching the output of `top`.

> **Q: What is the difference between utime and stime?**
> A: `utime` = ticks your process spent executing its own code (user space). `stime` = ticks the kernel spent on behalf of your process (system calls like `read()`, `write()`, `accept()`). Both count as CPU time this process consumed.

---

## Usage

```bash
python3 top_cpu_processes.py
```

> Takes ~1 second to run (one sleep interval between snapshots).

## Requirements

- Python 3.x
- **Linux only** (requires `/proc` filesystem)
- No third-party packages needed
- Run as any user (reads are available without root for most processes)
