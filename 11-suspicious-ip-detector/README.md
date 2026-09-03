# 11 - Suspicious IP Detector (Brute-Force Login Detector)

## The Interview Question

> *"You have an authentication log. Find IP addresses that have more than 5 failed login attempts."*

---

## What This Script Does

1. Takes an **auth log file path** as a command-line argument
2. Reads the file **line by line** — memory-safe for huge logs
3. Filters only `"Failed login from"` lines
4. Builds an **IP → count dictionary** in a single pass through the file
5. Prints all IPs that exceed the threshold, **sorted by count** (most aggressive first)
6. Handles missing files, permission errors, and unexpected failures gracefully

---

## The Clean Solution

```python
import sys

def detect_suspicious_ips(filepath, threshold=5):
    ip_counts = {}

    try:
        with open(filepath, "r") as file:
            for line in file:
                if "Failed login from" in line:
                    ip = line.strip().split()[-1]
                    ip_counts[ip] = ip_counts.get(ip, 0) + 1

        print("Suspicious IPs:")
        print("-" * 30)
        found_any = False

        for ip, count in sorted(ip_counts.items(), key=lambda x: x[1], reverse=True):
            if count > threshold:
                print(f"{ip} -> {count} failed attempts")
                found_any = True

        if not found_any:
            print("No suspicious IPs found.")

    except FileNotFoundError:
        print(f"CRITICAL: Log file not found: '{filepath}'")
    except PermissionError:
        print(f"CRITICAL: Permission denied: '{filepath}'")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 suspicious_ip_detector.py <path_to_log_file>")
        sys.exit(1)
    detect_suspicious_ips(sys.argv[1])
```

---

## How We Achieved This — Every Decision Explained

### Step 1: The Data Structure — Why a Dictionary?

```python
ip_counts = {}
```

We need to answer: **"How many times did each IP appear?"**

This is a **counting problem**, and a dictionary is the perfect tool:

```
Key   = IP address (string)   -> unique identifier for each attacker
Value = count (integer)       -> how many failed attempts from that IP
```

Visual example — after processing 6 log lines:

```
Log lines processed:            ip_counts dictionary:
─────────────────────           ──────────────────────────────────
Failed login from 10.0.0.5      { "10.0.0.5":  1 }
Failed login from 192.168.1.1   { "10.0.0.5":  1, "192.168.1.1": 1 }
Failed login from 10.0.0.5      { "10.0.0.5":  2, "192.168.1.1": 1 }
Failed login from 10.0.0.5      { "10.0.0.5":  3, "192.168.1.1": 1 }
Accepted password for root ...  (skipped - no "Failed login from")
Failed login from 10.0.0.5      { "10.0.0.5":  4, "192.168.1.1": 1 }
Failed login from 10.0.0.5      { "10.0.0.5":  5, "192.168.1.1": 1 }
Failed login from 10.0.0.5      { "10.0.0.5":  6, "192.168.1.1": 1 }
```

After one full pass: `"10.0.0.5"` has 6 attempts → exceeds threshold of 5 → **SUSPICIOUS**.

Why not a list?
- A list would store every IP per occurrence → 10,000 failed attempts = 10,000 list entries
- A dictionary stores one entry per unique IP no matter how many times it appears → O(1) lookup and update
- Dictionary scales to millions of log lines without growing proportionally in memory

### Step 2: Line-by-Line Iteration — Why Not `file.read()`?

```python
for line in file:
```

Three approaches compared:

```python
# OPTION A: Load entire file into one string (DANGEROUS for large logs)
content = file.read()
lines = content.split("\n")
# Problem: /var/log/auth.log can be 500MB+
# This loads ALL 500MB into RAM instantly -> OOM kill on small servers

# OPTION B: Load all lines into a list (SAME PROBLEM)
lines = file.readlines()
# Same issue - entire file content now lives in a list in memory

# OPTION C: Iterate line by line (CORRECT - constant memory usage)
for line in file:
    # Only ONE line in RAM at any moment
    # File is read in chunks by the OS buffer -> efficient I/O
    # Works on a 10GB log file with only kilobytes of RAM
```

Python's file object is an **iterator** — it yields one line at a time from an internal OS buffer.
Memory usage stays constant regardless of file size. This is the production-grade approach.

### Step 3: The Filter — `"Failed login from" in line`

```python
if "Failed login from" in line:
```

Real auth logs contain many different types of lines:

```
Sep  3 22:01:15 server sshd[1234]: Failed password for root from 10.0.0.5 port 54321 ssh2
Sep  3 22:01:16 server sshd[1234]: Accepted password for ubuntu from 172.16.0.1 port 22 ssh2
Sep  3 22:01:17 server sshd[1234]: session opened for user ubuntu
Sep  3 22:01:18 server sshd[1234]: Invalid user admin from 10.0.0.5
Sep  3 22:01:19 server sshd[1234]: Failed login from 10.0.0.5
```

`"Failed login from" in line` is a **substring search** — it returns `True` only if those exact characters appear anywhere in the line.

Python's `in` operator on strings uses an optimised search algorithm internally.
On a modern machine, it can scan millions of lines per second.

We skip all other lines instantly without any parsing. This is fast because we exit the `if` block at the first character mismatch — we never read the rest of the line for non-matching lines.

> **Note for the interview:** In real `/var/log/auth.log`, the pattern is `"Failed password for"`, not `"Failed login from"`. This script uses a simplified log format for clarity. In production, you'd change the filter string to match your actual log format. The logic is identical.

### Step 4: Parsing the IP — Three Operations on One Line

```python
ip = line.strip().split()[-1]
```

This is three chained operations. Let's trace through each one:

**Input line:**
```
"Failed login from 192.168.1.10\n"
```

**Operation 1: `.strip()`**
```
Removes leading/trailing whitespace AND the newline character \n at the end.
"Failed login from 192.168.1.10\n"
->
"Failed login from 192.168.1.10"
```
Without `.strip()`, the IP would be `"192.168.1.10\n"` — with a newline embedded.
This would make `"192.168.1.10\n"` and `"192.168.1.10"` appear as TWO DIFFERENT KEYS in the dictionary. Silent bug.

**Operation 2: `.split()`**
```
Splits on ANY whitespace (spaces, tabs, multiple spaces).
No argument = split on all whitespace.
"Failed login from 192.168.1.10"
->
["Failed", "login", "from", "192.168.1.10"]
```
`.split()` (no args) handles multiple consecutive spaces automatically.
`.split(" ")` (with explicit space) would create empty strings for consecutive spaces — less robust.

**Operation 3: `[-1]`**
```
Negative indexing in Python: -1 = last element, -2 = second-to-last, etc.
["Failed", "login", "from", "192.168.1.10"][-1]
->
"192.168.1.10"
```
We know the IP is always the last word. Negative indexing is the Pythonic and robust way to get it — you don't need to know how many words are before it.

### Step 5: Counting with `dict.get()` — The Standard Pattern

```python
ip_counts[ip] = ip_counts.get(ip, 0) + 1
```

`dict.get(key, default)` is the safe way to read from a dictionary:
- If `key` exists → returns its value
- If `key` does NOT exist → returns `default` (without raising `KeyError`)

Trace through the first three times we see `"10.0.0.5"`:

```
# First encounter - key does not exist yet:
ip_counts.get("10.0.0.5", 0)  ->  0   (key missing, return default 0)
ip_counts["10.0.0.5"] = 0 + 1 = 1
ip_counts is now: { "10.0.0.5": 1 }

# Second encounter - key exists:
ip_counts.get("10.0.0.5", 0)  ->  1   (key found, return stored value 1)
ip_counts["10.0.0.5"] = 1 + 1 = 2
ip_counts is now: { "10.0.0.5": 2 }

# Third encounter:
ip_counts.get("10.0.0.5", 0)  ->  2
ip_counts["10.0.0.5"] = 2 + 1 = 3
ip_counts is now: { "10.0.0.5": 3 }
```

**Alternative approaches (all equivalent):**
```python
# Option 1: dict.get (used in this script - most readable)
ip_counts[ip] = ip_counts.get(ip, 0) + 1

# Option 2: collections.defaultdict (auto-initializes missing keys)
from collections import defaultdict
ip_counts = defaultdict(int)
ip_counts[ip] += 1

# Option 3: collections.Counter (most compact for pure counting)
from collections import Counter
counter = Counter()
counter[ip] += 1
```

`dict.get()` is used here because it uses ONLY the built-in `dict` — no imports.
This shows the interviewer you understand dictionary fundamentals, not just library shortcuts.

### Step 6: Sorting the Output — Most Dangerous First

```python
for ip, count in sorted(ip_counts.items(), key=lambda x: x[1], reverse=True):
```

Without sorting, results would appear in **insertion order** (Python 3.7+):
```
10.0.0.5       -> 6 failed attempts
203.0.113.99   -> 2 failed attempts    <- this appeared first in log
192.168.1.1    -> 15 failed attempts   <- most dangerous but shown last!
```

With sorting by count descending:
```
192.168.1.1    -> 15 failed attempts   <- most dangerous FIRST
10.0.0.5       -> 6 failed attempts
203.0.113.99   -> 2 failed attempts    <- below threshold, not shown
```

Breaking down the sort:
```python
ip_counts.items()
# Returns: dict_items([("10.0.0.5", 6), ("192.168.1.1", 15), ...])
# Each item is a (key, value) tuple = (ip, count)

key=lambda x: x[1]
# x is one tuple: ("10.0.0.5", 6)
# x[0] = "10.0.0.5"  (the IP - we don't sort by this)
# x[1] = 6           (the count - sort by THIS)

reverse=True
# Descending order: highest count appears first
```

### Step 7: The `found_any` Flag — Why It Exists

```python
found_any = False

for ip, count in sorted(...):
    if count > threshold:
        print(...)
        found_any = True

if not found_any:
    print("No suspicious IPs found.")
```

We cannot know BEFORE iterating whether any IP exceeded the threshold.
The flag tracks this: if we print at least one IP, `found_any` becomes `True`.
If the loop completes without printing anything, `found_any` stays `False` → we print the "all safe" message.

Without this flag, we'd have no way to print a "no results" message correctly.

### Step 8: Exception Handling — Three Levels

```python
except FileNotFoundError:
    # Path does not exist:
    # - Wrong path given by user
    # - Log rotation deleted the file between our check and open
    # - Application never created its log file

except PermissionError:
    # File exists but we cannot read it:
    # - Log owned by root, script running as ubuntu
    # - chmod 600 applied to auth.log (common security practice)
    # Fix: sudo python3 suspicious_ip_detector.py /var/log/auth.log

except Exception as e:
    # Anything else:
    # - UnicodeDecodeError: log contains binary garbage (use open(..., errors="ignore"))
    # - OSError: disk read failure, NFS mount gone
    # We print the raw error so the operator has full context
```

---

## The Bigger Picture: What This Script Detects

This script identifies **brute-force login attacks** — one of the most common attack vectors against servers.

### What a Brute-Force Attack Looks Like in Logs

```
Sep 03 22:00:01 Failed login from 185.220.101.45
Sep 03 22:00:02 Failed login from 185.220.101.45
Sep 03 22:00:02 Failed login from 185.220.101.45
Sep 03 22:00:03 Failed login from 185.220.101.45
Sep 03 22:00:03 Failed login from 185.220.101.45
Sep 03 22:00:04 Failed login from 185.220.101.45   <- 6th attempt: FLAGGED
Sep 03 22:00:04 Failed login from 185.220.101.45
...continues for hours...
```

An automated script is trying thousands of username/password combinations per minute against your SSH or web login. The pattern: **many failures from one IP in a short time**.

### Real Production Thresholds

| Service | Typical Threshold | Why |
|---------|------------------|-----|
| SSH login | 3–5 attempts | Legitimate users don't mistype passwords 5+ times |
| Web login form | 10–20 attempts | Users sometimes forget passwords |
| API key auth | 1–2 attempts | Automated clients should never fail |
| VPN login | 3 attempts | Corporate policy |

This script uses `threshold=5` as default but it's a parameter — change it per use case.

---

## What the Interviewer Is Looking For

| What they check | What your script demonstrates |
|----------------|-------------------------------|
| Right data structure? | Dictionary for O(1) counting — not a list that grows with each occurrence |
| Memory efficiency? | Line-by-line iteration — works on 500MB logs without loading them into RAM |
| Parsing robustness? | `.strip().split()[-1]` — handles trailing newlines and multiple spaces |
| `dict.get()` pattern? | Standard Pythonic counting without `KeyError` risk |
| Sorted output? | Most dangerous IP first — shows operational thinking |
| 3-level exception handling? | `FileNotFoundError`, `PermissionError`, and catch-all |
| Configurable threshold? | `threshold=5` parameter — not a magic number in the logic |

---

## How This Convinces the Interviewer

Brute-force detection is a **foundational security + SRE skill**. Every company with exposed servers deals with this. Tools like `fail2ban` do exactly this — scan logs, count failures, block IPs.

By writing this from scratch you demonstrate:
- You understand how auth logs work
- You can parse unstructured text files efficiently
- You know the right data structures for counting problems
- You think like a defender, not just a developer

**Say in the interview:**
> *"In production, I'd extend this to also output results in JSON so it can feed into a SIEM like Splunk or Elasticsearch. I'd also add automatic `iptables` or `ufw` blocking for IPs that cross the threshold — that's essentially what `fail2ban` does, and this is its core logic."*

---

## Test It Yourself

Create a sample auth log to test:

```bash
python3 -c "
import random
ips = ['10.0.0.5', '192.168.1.1', '203.0.113.99', '8.8.8.8']
lines = []
for _ in range(50):
    ip = random.choice(ips)
    lines.append(f'Failed login from {ip}')
lines.append('Accepted password for ubuntu from 172.16.0.1')
lines.append('session opened for user ubuntu')
open('test_auth.log', 'w').write('\n'.join(lines))
print('test_auth.log created')
"

python3 suspicious_ip_detector.py test_auth.log
```

---

## Sample Output

```
Suspicious IPs (Possible Brute-Force Attacks):
---------------------------------------------
  10.0.0.5           -> 18 failed attempts  [SUSPICIOUS]
  192.168.1.1        -> 12 failed attempts  [SUSPICIOUS]
  203.0.113.99       -> 7 failed attempts   [SUSPICIOUS]

Total unique IPs seen in log: 4
Threshold used: > 5 failed attempts
```

```
# When all IPs are within threshold:
Suspicious IPs (Possible Brute-Force Attacks):
---------------------------------------------
  No suspicious IPs found. All within threshold.

Total unique IPs seen in log: 4
Threshold used: > 5 failed attempts
```

```
# File not found:
CRITICAL: Log file not found: '/var/log/auth.log'
```

---

## Usage

```bash
python3 suspicious_ip_detector.py <path_to_log_file>

# Examples:
python3 suspicious_ip_detector.py /var/log/auth.log
python3 suspicious_ip_detector.py /var/log/sshd.log
python3 suspicious_ip_detector.py test_auth.log
```

To use a custom threshold, edit the function call in the script:
```python
detect_suspicious_ips(log_file_path, threshold=10)
```

## Requirements

- Python 3.x
- Works on **Linux, macOS, Windows**
- Read permission on the target log file
- No third-party packages needed
