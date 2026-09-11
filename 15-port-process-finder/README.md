# 15 - Port Process Finder

## The Interview Question

> *"An application is failing to start because port 8080 is already in use. Write a small Python script that identifies which process is listening on that port."*

---

## What This Script Does

1. Takes a **port number** as a command-line argument
2. Runs `ss -lptn 'sport = :<port>'` via `subprocess` to query the kernel's socket table
3. Filters output lines with two cheap string checks before touching the regex
4. Extracts the **process name** and **PID** using a targeted regular expression
5. Prints the owning process with ready-to-run `kill` commands
6. Handles missing `ss` binary, non-numeric input, and permission issues

---

## The Solution

```python
import subprocess
import sys
import re

def find_process_by_port(port):
    try:
        cmd = ['ss', '-lptn', f'sport = :{port}']
        result = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True)

        for line in result.splitlines():
            if f":{port}" in line and "users:(" in line:
                match = re.search(r'users:\(\("([^"]+)",pid=(\d+)', line)
                if match:
                    return match.group(2), match.group(1)   # (PID, process_name)

        return None, None

    except FileNotFoundError:
        print("Error: 'ss' utility not found. Install: sudo apt install iproute2")
        sys.exit(1)
    except subprocess.CalledProcessError:
        return None, None

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 port_process_finder.py <port>")
        sys.exit(1)

    port = sys.argv[1]
    if not port.isdigit():
        print(f"Error: '{port}' is not a valid port number.")
        sys.exit(1)

    pid, process = find_process_by_port(port)

    if pid:
        print(f"Port {port} is in use:")
        print(f"  PID     : {pid}")
        print(f"  Process : {process}")
        print(f"\nTo kill it   : sudo kill {pid}")
        print(f"To force-kill: sudo kill -9 {pid}")
    else:
        print(f"No process found listening on port {port}.")
        print("Note: Run with sudo if the process is owned by root.")

if __name__ == "__main__":
    main()
```

---

## How We Achieved This — Every Decision Explained

### Why `ss` and Not `netstat`?

Two tools can show listening ports on Linux. Here is why `ss` is the right choice:

| | `ss` | `netstat` |
|-|------|-----------|
| Source | Queries kernel directly via **Netlink socket** | Reads `/proc/net/tcp` (text file) |
| Speed | Extremely fast — O(1) kernel call | Slower — file I/O + text parsing |
| Availability | Installed by default on all modern Linux (iproute2) | **Deprecated**, often not installed by default |
| Filter support | Built-in filter expressions (`sport = :8080`) | No built-in port filter, you need `grep` |
| Process info | Shows full process details with `-p` | Shows with `-p` but needs root more often |

`ss` is part of **iproute2** — the same package that provides `ip`, `tc`, and `bridge`. If you use `ip addr` you already have `ss`.

---

### The `ss` Command: Every Flag Explained

```bash
ss -lptn 'sport = :8080'
```

Broken down flag by flag:

```
-l   --listening     Show only LISTENING sockets
                     Excludes established connections (client sessions)
                     We only care about which process OWNS the port

-p   --processes     Show process info for each socket
                     Output includes: users:(("java",pid=1842,fd=10))
                     Requires same UID as process OR root for other users

-t   --tcp           Show TCP sockets only
                     Excludes: UDP (-u), Unix domain sockets (-x), raw (-w)
                     Port conflicts are always TCP or UDP — we target TCP

-n   --numeric       Show port numbers as numbers, not service names
                     Without -n: port 80 shows as "http", 443 as "https"
                     With -n:    port 80 shows as "80"
                     We MUST use -n because we match f":{port}" (e.g. :8080)
                     Without it, ":8080" might show as ":http-alt" and not match

'sport = :8080'      ss filter expression
                     sport = source port = the port the server listens ON
                     Without this filter: ss shows ALL listening ports
                     With it: output contains only the one port we want
                     The quotes are necessary in shell but not in our list cmd
```

---

### What `ss` Output Looks Like

**With no filter (all ports):**
```
Netid  State    Recv-Q  Send-Q  Local Address:Port   Peer Address:Port  Process
tcp    LISTEN   0       128     0.0.0.0:22            0.0.0.0:*          users:(("sshd",pid=812,fd=3))
tcp    LISTEN   0       511     0.0.0.0:80            0.0.0.0:*          users:(("nginx",pid=1234,fd=6))
tcp    LISTEN   0       50      0.0.0.0:8080          0.0.0.0:*          users:(("java",pid=1842,fd=10))
tcp    LISTEN   0       128     0.0.0.0:3306          0.0.0.0:*          users:(("mysqld",pid=987,fd=21))
```

**With `sport = :8080` filter:**
```
Netid  State    Recv-Q  Send-Q  Local Address:Port   Peer Address:Port  Process
tcp    LISTEN   0       50      0.0.0.0:8080          0.0.0.0:*          users:(("java",pid=1842,fd=10))
```

The column we need is the last one: `users:(("java",pid=1842,fd=10))`

Structure of that field:
```
users:(("java",pid=1842,fd=10))
       ||     |    |        |
       ||     |    |        +-- fd=10 = file descriptor number (not needed)
       ||     |    +----------- pid=1842 = the Process ID  <-- WE WANT THIS
       ||     +---------------- "java" = process name      <-- WE WANT THIS
       |+----- (( = double opening paren (ss uses double paren for the outer list)
       +------ users: = keyword
```

---

### Step 1: `subprocess.check_output()` — Running External Commands

```python
result = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True)
```

**Why `check_output` and not `os.system()`?**

| | `os.system()` | `subprocess.check_output()` |
|-|--------------|---------------------------|
| Returns | Exit code only | The actual **stdout output** as a string |
| We can parse it? | No | Yes |
| Error handling | Have to check return code manually | Raises `CalledProcessError` automatically |
| Capture stderr? | No | Yes, controllable |

`check_output` returns stdout as a string (because `text=True`), which we then parse line by line.

**`stderr=subprocess.DEVNULL`** redirects ss's stderr to `/dev/null`.

Why? When run as a non-root user, `ss -p` prints permission warnings like:
```
netid   state   recv-q  send-q  ...
(No info could be read, you need to be root to see it all)
```
These are not errors — they are informational. We suppress them so our output stays clean. We handle the real consequence (no process info) by checking `"users:("` in the line.

**`text=True`** means decode bytes to `str` automatically using the system locale. Alternative: `result.decode('utf-8')` manually.

---

### Step 2: The Filter — Two Cheap Checks Before the Regex

```python
if f":{port}" in line and "users:(" in line:
```

**Why two conditions and not just the regex?**

Running `re.search()` on every line is more expensive than a simple `in` string check. We use the two cheap guards to skip lines that can't possibly match before invoking regex.

**Condition 1: `f":{port}" in line`**

We search for `":8080"` not `"8080"` for a critical reason:

```
Example line:
tcp  LISTEN  0  50  0.0.0.0:8080  0.0.0.0:*  users:(("java",pid=8080,fd=10))
                          ^^^^                              ^^^^
                     port is here                    PID happens to be 8080 too!
```

If we just searched for `"8080"`, we might match a line where PID=8080 but the port is something different. Adding the colon (`:8080`) anchors us to the port column position.

**Condition 2: `"users:(" in line`**

`ss -p` only shows the `users:(...)` section if it has permission to see the process.

```
# As non-root user checking a root-owned process:
tcp  LISTEN  0  128  0.0.0.0:8080  0.0.0.0:*
                                              ^-- no users:( section!

# As root or same-user process:
tcp  LISTEN  0  128  0.0.0.0:8080  0.0.0.0:*  users:(("java",pid=1842,fd=10))
```

Without this check, our regex would run on a line that can never match, wasting time.

The `and` operator **short-circuits**: if `f":{port}" in line` is `False`, Python never evaluates `"users:(" in line`. Only lines passing both checks reach the regex.

---

### Step 3: The Regular Expression — Full Breakdown

```python
match = re.search(r'users:\(\("([^"]+)",pid=(\d+)', line)
```

Target string:
```
users:(("java",pid=1842,fd=10))
```

Let's dissect the pattern `r'users:\(\("([^"]+)",pid=(\d+)'` token by token:

```
Token           What it means                           Matches
────────────────────────────────────────────────────────────────────────────
users:          Literal text                            users:
\(             Escaped literal (                       (
\(             Escaped literal (                       (
"              Literal double-quote                    "
([^"]+)        CAPTURE GROUP 1                         java
  (             Start capturing — save this part
  [^"]         Character class: any char EXCEPT "
  +             One or more of those chars
  )             Stop capturing
"              Literal double-quote                    "
,pid=           Literal text                            ,pid=
(\d+)          CAPTURE GROUP 2                         1842
  (             Start capturing
  \d           Any digit character (0-9)
  +             One or more digits
  )             Stop capturing
```

**Why `[^"]+` instead of `.+` for the process name?**

`.+` is **greedy** — it matches as much as possible:
```
Input:    "java",pid=1842,fd=10))
Pattern:  .+"  (greedy)
Match:    java",pid=1842,fd=10))"  <- overshoots!
```

`[^"]+` stops **exactly** at the first double-quote:
```
Input:    "java",pid=1842,fd=10))
Pattern:  [^"]+  (stops at first ")
Match:    java  <- precise
```

**`re.search()` vs `re.match()`:**
- `re.match()` only matches at the START of the string
- `re.search()` scans through the string to find the pattern ANYWHERE

We use `re.search()` because `users:(...)` is not at the start of the line — it comes after IP addresses, port numbers, and state columns.

---

### Step 4: `match.group()` — Extracting the Results

```python
if match:
    process_name = match.group(1)   # First capture group  = "java"
    pid          = match.group(2)   # Second capture group = "1842"
    return pid, process_name
```

| `match.group(n)` | What it returns |
|-----------------|----------------|
| `match.group(0)` | The entire matched substring: `users:(("java",pid=1842` |
| `match.group(1)` | First `()` group = process name: `java` |
| `match.group(2)` | Second `()` group = PID: `1842` |

Both are returned as **strings** (not integers). PIDs stay as strings here since we only print them — no arithmetic needed.

We return `(pid, process_name)` in that order because the caller unpacks:
```python
pid, process = find_process_by_port(port)
```

---

### Input Validation: `port.isdigit()`

```python
if not port.isdigit():
    print(f"Error: '{port}' is not a valid port number.")
    sys.exit(1)
```

`str.isdigit()` returns `True` only if every character is a digit (0–9):

```python
"8080".isdigit()   -> True   ✅
"80.5".isdigit()   -> False  (contains .)
"-80".isdigit()    -> False  (contains -)
"http".isdigit()   -> False  (contains letters)
"".isdigit()       -> False  (empty string)
```

This prevents passing a service name like `"http"` to the ss command which would cause unexpected behavior. We validate before calling subprocess.

---

### The Two Exception Cases

**`FileNotFoundError`**

Raised by `subprocess.check_output()` when the binary (`ss`) is not found in `PATH`.

On minimal Docker containers or very stripped-down systems, iproute2 may not be installed.

```
Fix: sudo apt install iproute2   (Debian/Ubuntu)
     sudo yum install iproute    (RHEL/CentOS)
```

**`subprocess.CalledProcessError`**

Raised when `ss` exits with a non-zero return code. Rare — can happen if ss encounters a kernel version mismatch or unsupported filter syntax. We return `(None, None)` and let the caller handle it gracefully.

---

### Why Show `kill` Commands in Output?

```python
print(f"To kill it   : sudo kill {pid}")
print(f"To force-kill: sudo kill -9 {pid}")
```

In a production incident, the operator's next step after finding the PID is always to kill the process. Printing the exact command saves 30 seconds of typing and eliminates typos under pressure.

**`kill <pid>`** (SIGTERM, signal 15): Asks the process to shut down gracefully. It can save state, close connections, flush buffers. This is the correct first choice.

**`kill -9 <pid>`** (SIGKILL, signal 9): Forces immediate termination by the kernel. The process has no chance to clean up. Use only if SIGTERM did not work.

---

### What Happens When Run Without `sudo`

If the port is owned by a root process and you run as a non-root user:

```
ss output line (no users section):
tcp   LISTEN   0   128   0.0.0.0:8080   0.0.0.0:*

Our check: "users:(" in line -> False -> skip this line
Result: return None, None
Output: "No process found listening on port 8080."
        "Note: Run with sudo if the process is owned by root."
```

The port IS in use but we lack permission to see who owns it. The note tells the operator exactly what to do — `sudo python3 port_process_finder.py 8080`.

---

## What the Interviewer Is Looking For

| What they check | What your script demonstrates |
|----------------|-------------------------------|
| Know `ss` over `netstat`? | `ss` is the modern standard — kernel Netlink vs deprecated /proc parsing |
| All 4 ss flags explained? | `-l` (listen) `-p` (process) `-t` (TCP) `-n` (numeric) — each with a reason |
| `subprocess.check_output`? | Returns stdout for parsing, auto-raises on error — correct choice |
| Smart pre-filter before regex? | `":{port}" in line` prevents PID false-match; `"users:("` skips permission-hidden lines |
| Regex group understanding? | `[^"]+` stops at quote boundary; `\d+` for digits; `group(1)` vs `group(2)` |
| Input validation? | `isdigit()` rejects non-numeric port arguments before touching subprocess |
| Practical output? | Exact `kill` and `kill -9` commands printed — zero friction for the oncall engineer |
| Sudo awareness? | Explains the permission gap and tells user exactly how to fix it |

---

## How This Convinces the Interviewer

"Port already in use" is one of the most common startup failures in production:

- A previous deployment crashed mid-shutdown — old process still holds the port
- Two services misconfigured to use the same port
- A zombie/leaked process from a failed restart
- Blue-green deploy where the old version was not cleanly stopped

This is the FIRST thing an SRE runs when a deployment fails with `Address already in use`.

**Say in the interview:**
> *"In production I'd extend this to also check UDP ports (add `-u` to the ss flags) and show the full command line of the process using `/proc/<pid>/cmdline` — that way you know it's `java -jar myapp.jar` and not just `java`. I'd also cross-reference with `lsof -i :<port>` as a fallback if ss isn't available."*

---

## Sample Output

```bash
# Port 8080 is in use by Java:
$ python3 port_process_finder.py 8080
Port 8080 is in use:
  PID     : 1842
  Process : java

To kill it   : sudo kill 1842
To force-kill: sudo kill -9 1842

# Port is free:
$ python3 port_process_finder.py 9999
No process found listening on port 9999.
Note: Run with sudo if the process is owned by root.
      sudo python3 port_process_finder.py 9999

# Invalid input:
$ python3 port_process_finder.py http
Error: 'http' is not a valid port number. Use a number like 8080.

# Wrong number of arguments:
$ python3 port_process_finder.py
Usage  : python3 port_process_finder.py <port>
Example: python3 port_process_finder.py 8080

# Process owned by root (run as non-root):
$ python3 port_process_finder.py 22
No process found listening on port 22.
Note: Run with sudo if the process is owned by root.
      sudo python3 port_process_finder.py 22

$ sudo python3 port_process_finder.py 22
Port 22 is in use:
  PID     : 812
  Process : sshd

To kill it   : sudo kill 812
To force-kill: sudo kill -9 812
```

---

## Usage

```bash
python3 port_process_finder.py <port>

# Examples:
python3 port_process_finder.py 8080   # Common app server port
python3 port_process_finder.py 3000   # Node.js / React dev server
python3 port_process_finder.py 5432   # PostgreSQL

# For root-owned processes:
sudo python3 port_process_finder.py 80
sudo python3 port_process_finder.py 443
sudo python3 port_process_finder.py 22
```

## Requirements

- Python 3.x
- **Linux only** (uses `ss` from the `iproute2` package)
- `ss` must be installed: `sudo apt install iproute2`
- Run with `sudo` for processes owned by root or other users
- No third-party Python packages needed
