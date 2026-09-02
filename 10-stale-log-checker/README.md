# 10 - Stale Log File Checker

## The Interview Question

> *"Write a Python script that checks whether an application's log file has been updated recently. If the log hasn't been modified for more than 5 minutes, print a warning."*

---

## What This Script Does

1. Takes a **log file path** as a command-line argument
2. Reads the file's **last modification timestamp** from filesystem metadata
3. Calculates how many seconds have passed since the last write
4. Prints `HEALTHY` if updated within 5 minutes, `STALE` with a warning if not
5. Handles missing files and permission errors gracefully

---

## The Clean Solution

```python
import os
import sys
import time

def check_stale_log(file_path):
    THRESHOLD_SECONDS = 300

    try:
        mtime = os.path.getmtime(file_path)
        current_time = time.time()
        time_diff = current_time - mtime

        if time_diff >= 60:
            time_str = f"{int(time_diff // 60)} minutes ago"
        else:
            time_str = f"{int(time_diff)} seconds ago"

        if time_diff > THRESHOLD_SECONDS:
            print(f"Log status : STALE")
            print(f"Last write : {time_str}")
            print("WARNING    : Application may have stopped writing logs!")
        else:
            print(f"Log status : HEALTHY")
            print(f"Last write : {time_str}")

    except FileNotFoundError:
        print(f"CRITICAL: File not found: '{file_path}'")
    except PermissionError:
        print(f"CRITICAL: Permission denied: '{file_path}'")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 stale_log_checker.py <path_to_log_file>")
        sys.exit(1)
    check_stale_log(sys.argv[1])
```

---

## How We Achieved This — Every Decision Explained

### The Core Concept: Unix Timestamps

Everything in this script revolves around **Unix timestamps**.

A Unix timestamp is simply:
> **The number of seconds that have elapsed since January 1, 1970 at 00:00:00 UTC**

This date is called the **Unix Epoch** — the moment Unix clocks started ticking.

```
January 1, 1970  00:00:00 UTC  ->  timestamp = 0
January 1, 1970  00:00:01 UTC  ->  timestamp = 1
...
September 2, 2024 08:00:00 UTC ->  timestamp = 1725264000  (approximately)
```

Both functions we use — `os.path.getmtime()` and `time.time()` — return Unix timestamps as Python floats.
Since they are in the same unit (seconds), we subtract them directly.

```python
time_diff = current_time - mtime
# If current_time = 1725264360.5 and mtime = 1725264000.0
# time_diff = 360.5 seconds = 6 minutes -> STALE (> 300s threshold)
```

### `os.path.getmtime()` — Reading a File's Modification Time

```python
mtime = os.path.getmtime(file_path)
```

`getmtime()` = "get modification time"

**What it reads:** The file's **inode metadata** on the filesystem — NOT the file content.

An inode is the filesystem's record for a file. It stores:

```
Inode for /var/log/myapp/app.log
├── File size         : 45,231,872 bytes
├── Owner             : www-data (UID 33)
├── Permissions       : 644 (rw-r--r--)
├── atime (access)    : 1725264355  <- last time file was READ
├── mtime (modified)  : 1725264000  <- last time file CONTENT changed  ← we use this
└── ctime (changed)   : 1725264000  <- last time METADATA changed
```

**Why `mtime` (not `atime` or `ctime`)?**

| Timestamp | Updates when... | Why not use it |
|-----------|----------------|----------------|
| `atime` | File is **read** | Reading a log with `cat` or `tail` would reset it — misleading |
| `mtime` | File **content changes** (new bytes written) | ✅ Correct — updates only when the app writes a new log line |
| `ctime` | File **metadata changes** (chmod, chown) | `chmod app.log` would reset it — misleading |

For monitoring whether an application is **writing** to its log, `mtime` is always the right choice.

`os.path.getmtime()` internally calls the `stat()` system call — it reads inode data directly from the kernel.
This is **instant** regardless of file size. No file is opened. No content is read.

### `time.time()` — The Current Moment

```python
current_time = time.time()
```

`time.time()` returns the current time as a Unix timestamp (float).

It calls the kernel's `gettimeofday()` or `clock_gettime()` system call — the most accurate clock available.

The fractional part (e.g., `1725264000.456`) represents sub-second precision. For our 5-minute threshold, this precision doesn't matter — but it's free.

### `THRESHOLD_SECONDS = 300` — Why a Named Constant?

```python
THRESHOLD_SECONDS = 300   # 5 minutes × 60 seconds/minute
```

Compare:
```python
# Bad - magic number, hard to understand and maintain:
if time_diff > 300:

# Good - self-documenting, easy to change:
THRESHOLD_SECONDS = 300
if time_diff > THRESHOLD_SECONDS:
```

In production, different log files may need different thresholds:
```
Payment service log    -> threshold = 60s   (should write every second)
Batch job log          -> threshold = 3600s (runs hourly)
Audit log              -> threshold = 300s  (standard 5 min)
```

A named constant at the top of the function makes this trivially adjustable.

### Time Formatting — Human-Readable Output

```python
if time_diff >= 60:
    time_str = f"{int(time_diff // 60)} minutes ago"
else:
    time_str = f"{int(time_diff)} seconds ago"
```

Raw seconds are hard to parse quickly in an alert:
```
❌  Last write: 324 seconds ago     <- requires mental math to understand
✅  Last write: 5 minutes ago       <- immediately understood
```

`//` is **integer division** (floor division) — discards the remainder:
```
324 // 60 = 5   (not 5.4 — we floor it to whole minutes)
324 % 60  = 24  (remainder seconds — we discard this for cleanliness)
```

`int()` wraps the result to remove Python's decimal point: `int(5.0)` → `5`.

### The Two Exception Cases

```python
except FileNotFoundError:
    print(f"CRITICAL: File not found: '{file_path}'")
```

**When this fires:** The path doesn't exist on the system.
**Real causes:**
- Wrong path in the script argument
- Log rotation just deleted the file (e.g., `logrotate` midnight rotation)
- Application never started so it never created its log file
- Mounted filesystem was unmounted

**Production action:** Check if the application is running, check logrotate config.

```python
except PermissionError:
    print(f"CRITICAL: Permission denied: '{file_path}'")
```

**When this fires:** The file exists but our process user cannot access it.
**Real causes:**
- Log file owned by `root`, script running as `ubuntu` or `ec2-user`
- File permissions set to `600` (owner-only read)
- SELinux / AppArmor policy blocking access

**Production action:** `ls -l /path/to/logfile` to check permissions, run with `sudo`, or add script user to the appropriate group.

### Why No `except Exception` Catch-All?

We only catch two specific exceptions, not a generic `except Exception`.

The rule: **catch what you can handle, let the rest propagate.**

- `FileNotFoundError` — we have a specific, meaningful message for this
- `PermissionError` — we have a specific, meaningful message for this
- Anything else (disk failure, NFS timeout) — we DON'T know what happened,
  so letting it crash with a full Python traceback gives the operator MORE information, not less

A bare `except Exception: pass` hides bugs. Specific exceptions expose them.

---

## The Big Picture: Why Log Staleness Matters

A healthy application constantly writes to its log. Consider:

```
10:00:01  INFO  Request received from 10.0.0.5
10:00:01  INFO  Processing order #12345
10:00:02  INFO  Order processed successfully
10:00:02  INFO  Response sent: 200 OK
...
10:05:00  (silence - nothing written for 5 minutes)
```

If the log goes quiet, something happened:
1. **Application crashed silently** — no more code running, no more logs
2. **Application froze** — stuck on a lock, infinite loop, waiting for a resource
3. **Disk full** — application tried to write but got "No space left on device" error
4. **Log rotation misconfigured** — app still writes to old rotated file, new one is empty

None of these show up as an obvious ERROR. Staleness is the only signal.
This is why log-staleness monitoring is a real production alerting category.

---

## What the Interviewer Is Looking For

| What they check | What your script demonstrates |
|----------------|-------------------------------|
| Do you know `os.path.getmtime()`? | The right tool — reads mtime from inode, not file content |
| Do you understand Unix timestamps? | Both `getmtime()` and `time.time()` return the same unit → simple subtraction |
| Do you know the 3 file timestamps? | atime vs mtime vs ctime — and why mtime is the right one |
| Named constants over magic numbers? | `THRESHOLD_SECONDS = 300` — not hardcoded `300` |
| Human-readable output? | Minutes vs seconds formatting shows UX thinking |
| Specific exception handling? | `FileNotFoundError` and `PermissionError` separately — different root causes |
| CLI-ready tool? | `sys.argv` — works for any log file path |

---

## How This Convinces the Interviewer

Stale log detection is a real, production SRE monitoring pattern. It catches silent failures that no other metric catches:

- CPU and memory may look fine (zombie process)
- No HTTP errors (app died before a request came in)
- No crash log (app froze, not crashed)
- **But the log goes quiet → stale log monitor fires → oncall investigates**

Real-world usage:
- Cron job: run every minute, alert if STALE
- Nagios/Icinga: plug this into a check plugin
- Kubernetes: sidecar container monitoring the main container's log volume

**Say in the interview:**
> *"In production, I'd also check that the mtime is not in the FUTURE — that indicates a clock sync problem (NTP issue) which is its own incident. I'd also alert with the exact mtime formatted in ISO 8601 so the oncall engineer doesn't have to do timestamp math."*

---

## Test It Yourself

```bash
# Create a fresh log file and check it (should be HEALTHY):
echo "2024-09-02 INFO Application started" > /tmp/test.log
python3 stale_log_checker.py /tmp/test.log

# Simulate a stale log (set mtime to 10 minutes ago using touch):
touch -m -t $(date -d '10 minutes ago' '+%Y%m%d%H%M.%S') /tmp/test.log
python3 stale_log_checker.py /tmp/test.log

# Test FileNotFoundError:
python3 stale_log_checker.py /tmp/does_not_exist.log
```

---

## Sample Output

```bash
# Log file is fresh (written 23 seconds ago):
Log status  : HEALTHY
File        : /var/log/myapp/app.log
Last write  : 23 seconds ago

# Log file is stale (not written for 7 minutes):
Log status  : STALE
File        : /var/log/myapp/app.log
Last write  : 7 minutes ago
WARNING     : Application may have stopped writing logs!

# File does not exist:
CRITICAL: File not found: '/var/log/myapp/app.log'
Check the path or verify the application created the log file.

# Permission denied:
CRITICAL: Permission denied: '/var/log/auth.log'
Try running with sudo, or check file permissions with: ls -l
```

---

## Usage

```bash
python3 stale_log_checker.py <path_to_log_file>

# Examples:
python3 stale_log_checker.py /var/log/nginx/access.log
python3 stale_log_checker.py /var/log/myapp/app.log
python3 stale_log_checker.py /tmp/test.log
```

## Requirements

- Python 3.x
- Works on **Linux and macOS** (Windows paths work too)
- Read permission on the target log file
- No third-party packages needed
