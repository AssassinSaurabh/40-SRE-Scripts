# 06 - Log File Error Counter with Alerting

## The Interview Question

> *"You have an application log file. Write a Python script that counts ERROR messages and alerts if the number of errors exceeds a threshold."*

---

## What This Script Does

1. Opens a log file (e.g., `app.log`) safely
2. Reads it **line by line** (memory-efficient — works on 100GB log files too)
3. Counts every line containing the word `ERROR`
4. If the count exceeds a **configurable threshold**, prints an **ALERT**
5. Handles all failure cases: file not found, permission denied, unexpected errors

---

## The Clean Solution

```python
import os

def check_error_spike(log_file_path, threshold=10):
    error_count = 0
    try:
        with open(log_file_path, "r") as log_file:
            for line in log_file:
                if "ERROR" in line:
                    error_count += 1

        print(f"ERROR count: {error_count}")

        if error_count > threshold:
            print("ALERT: High number of errors detected!")
        else:
            print("OK: Error count is within acceptable limits.")

    except FileNotFoundError:
        print(f"CRITICAL: Log file not found: {log_file_path}")
    except PermissionError:
        print(f"CRITICAL: Permission denied reading: {log_file_path}")
    except Exception as e:
        print(f"CRITICAL: Unexpected error: {e}")

if __name__ == "__main__":
    check_error_spike("app.log", threshold=10)
```

---

## How We Achieved This — Every Decision Explained

### Why `with open(...)` and NOT `f = open(...)` + `f.close()`?

```python
# BAD way (risky)
f = open("app.log", "r")
data = f.read()
f.close()   # If an exception happens above, this NEVER runs -> file handle leak!

# GOOD way (safe)
with open("app.log", "r") as f:
    data = f.read()
# File is GUARANTEED to close here, even if an exception occurs inside the block
```

The `with` statement is a **context manager**. It runs `f.__exit__()` automatically at the end of the block — no matter what happens inside. In production, unclosed file handles accumulate and eventually crash the process with "Too many open files".

### Why iterate line by line instead of `f.read()` or `f.readlines()`?

```python
# MEMORY PROBLEM - loads the ENTIRE file into RAM
content = f.read()                # 10GB log file? 10GB RAM used instantly
lines = f.readlines()             # Same problem, but now its a 10GB list

# MEMORY EFFICIENT - reads one line at a time, discards it, reads next
for line in log_file:             # Only 1 line in RAM at any moment
    if "ERROR" in line:
        error_count += 1
```

On a production server, log files can be **gigabytes**. A script that loads the whole file into RAM will crash the server or get OOM-killed. Iterating line by line uses a constant small amount of memory regardless of file size.

### Why `"ERROR" in line` and not `.startswith("ERROR")` or regex?

Real log files have different formats:

```
2024-01-15 10:30:00 ERROR Database connection failed     <- ERROR is in the middle
[ERROR] Disk quota exceeded                              <- ERROR is at the start (with [])
LEVEL=ERROR msg="Service timeout"                        <- ERROR is in a key=value pair
{"level":"ERROR","msg":"panic"}                          <- JSON log format
```

Using `"ERROR" in line` catches ALL of these because Python's `in` operator checks if the substring exists **anywhere** in the string. This is both simple and maximally compatible.

If you wanted case-insensitive matching (e.g. `error` or `Error`):
```python
if "ERROR" in line.upper():
```

### Why three different `except` blocks?

```python
except FileNotFoundError:   # The path is wrong or the file was deleted
except PermissionError:     # The file exists but you don't have read rights
except Exception as e:      # Catch-all for anything else (disk error, encoding error)
```

Each exception has a **different root cause** and a **different fix**:

| Exception | Root Cause | What to do in production |
|-----------|-----------|--------------------------|
| `FileNotFoundError` | Wrong path, log rotation deleted the file | Alert oncall, check log rotation config |
| `PermissionError` | Script running as wrong user | Fix file permissions or run as correct user |
| `Exception` | Disk failure, encoding issue, etc. | Escalate, unknown problem |

Printing `CRITICAL` for all three tells the operations team this is not a warning — it needs human attention.

### Why a configurable `threshold` parameter and not a hardcoded number?

```python
def check_error_spike(log_file_path, threshold=10):
```

Different services have different error budgets:
- A payment service: threshold = 1 (zero tolerance)
- A retry-heavy microservice: threshold = 100 (expected retries show as errors)
- A batch job: threshold = 500 (batch failures are normal up to a point)

Making it a parameter means you can call the same function for different services with different rules — no code duplication.

---

## What the Interviewer Is Looking For

| What they check | What your script demonstrates |
|-----------------|-------------------------------|
| File handling knowledge | `with open()` context manager, not bare `open()`/`close()` |
| Memory awareness | Line-by-line iteration, not `.read()` or `.readlines()` |
| Exception handling | Three specific, meaningful `except` blocks |
| Configurable design | `threshold` as a parameter with a sensible default |
| Operational thinking | `CRITICAL` vs `ALERT` vs `OK` severity levels |

A candidate who uses `f.read()` shows they never worked with large files.
A candidate who has one `except Exception` shows they don't understand failure modes.
**This script shows you think like an SRE, not just a developer.**

---

## How This Script Helps You Convince the Interviewer

This is the foundation of **log-based alerting** — one of the most fundamental SRE tools.
Every real-world monitoring system (Datadog, Splunk, ELK Stack) does exactly this at its core:

1. Parse log lines
2. Count patterns that indicate problems
3. Alert when count exceeds a threshold

By writing this from scratch with proper error handling, you demonstrate:
- You understand how log monitoring actually works under the hood
- You can write production-grade scripts (not "works on my machine" code)
- You think about **file sizes, permissions, and failure modes** — not just the happy path

In interviews, you can extend this naturally:
> *"In production I would also tail the file in real-time using `seek()` and `tell()`, and send alerts to PagerDuty or Slack via webhooks instead of just printing."*

That kind of answer wins offers.

---

## Test It Yourself

Generate a sample log file to test:

```bash
# Create app.log with 15 errors (above threshold of 10)
python3 -c "
lines = []
for i in range(50):
    if i % 3 == 0:
        lines.append(f\"2024-01-15 10:{i:02d}:00 ERROR Something went wrong\")
    else:
        lines.append(f\"2024-01-15 10:{i:02d}:00 INFO Request processed OK\")
open(\"app.log\", \"w\").write(\"\n\".join(lines))
"

python3 log_error_counter.py
```

---

## Sample Output

```
# When errors are within limit:
Scan complete. ERROR count: 7 / threshold: 10
OK: Error count is within acceptable limits.

# When errors exceed threshold:
Scan complete. ERROR count: 17 / threshold: 10
ALERT: High error rate detected! 17 errors found (threshold=10)

# When file is missing:
CRITICAL: Log file not found: app.log
```

---

## Usage

```bash
python3 log_error_counter.py
```

To check a different file or threshold, edit the last line:
```python
check_error_spike("/var/log/nginx/error.log", threshold=50)
```

## Requirements

- Python 3.x
- Works on **Linux, macOS, Windows**
- No third-party packages needed
- Read permission on the target log file
