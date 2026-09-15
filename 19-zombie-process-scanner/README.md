# 19 - Zombie Process Scanner

## The Interview Question

> *"Write a small Python script that scans Linux processes and reports any zombie processes."*

---

## What This Script Does

1. Lists all numeric subdirectories in `/proc` — each one is a running process PID
2. For each PID, reads `/proc/<pid>/stat` to get the **process state character**
3. Uses `rfind(')')` to safely parse the stat line even when process names contain spaces
4. Checks if the state character is **`Z`** — the zombie state
5. Reports the PID and name of every zombie found, plus the fix command

---

## The Solution

```python
import os

def find_zombies():
    zombies = []
    for entry in os.listdir('/proc'):
        if not entry.isdigit():
            continue
        try:
            with open(f'/proc/{entry}/stat', 'r') as f:
                data = f.read()

            last_paren = data.rfind(')')
            state = data[last_paren + 2]

            if state == 'Z':
                name = data[data.find('(') + 1 : last_paren]
                zombies.append((entry, name))

        except (FileNotFoundError, IOError):
            continue

    return zombies

def main():
    zombies = find_zombies()
    if not zombies:
        print("No zombie processes found.")
        return
    print(f"Found {len(zombies)} zombie(s):")
    for pid, name in zombies:
        print(f"  PID: {pid}  Name: {name}")
        print(f"  Fix: ps -o ppid= -p {pid}  (find parent, then restart it)")

if __name__ == "__main__":
    main()
```

---

## How We Achieved This — Every Decision Explained

### What IS a Zombie Process?

This is the concept the interviewer cares most about. Get this right.

When a process finishes, it does not disappear immediately. It enters the **zombie state** — a dead process that is waiting for its parent to collect its exit status.

Here is the exact sequence:

```
Child process runs and finishes
         |
         v
Child calls exit(0)    <- process code stops running
         |
         v
Kernel keeps a small "process table entry" for the child
with: PID, exit code, CPU time used
         |
         v
Child is now a ZOMBIE  <- state = 'Z', no code running, barely any memory
         |
         v
Parent calls wait()    <- parent reads the child's exit code
         |
         v
Kernel removes the process table entry entirely
         |
         v
Process is truly gone
```

A zombie exists **between** the child dying and the parent calling `wait()`.

#### Key zombie facts

| Property | Value |
|----------|-------|
| Is it running? | **No** — zombie has no running code |
| Does it use CPU? | **No** — consumes zero CPU |
| Does it use memory? | **Barely** — only a tiny process table entry |
| Can you kill it with `kill -9`? | **No** — it is already dead. `kill` has nothing to send signals to |
| How do you remove it? | Fix or restart the **parent process** so it calls `wait()` |
| When is it a problem? | When thousands accumulate → PID table fills up → no new processes can start |

#### The real danger of zombies

Each zombie occupies one slot in the kernel's **process ID table**. Linux has a maximum PID limit (default 32768 on most systems). If a buggy process creates thousands of children and never calls `wait()`, the PID table can fill up. At that point:

```
fork(): Resource temporarily unavailable
```

New processes cannot be created. The system cannot start new programs. Even `ls` fails.

---

### `/proc/<pid>/stat` — The Source File

Every Linux process has a directory `/proc/<pid>/` containing files that describe it. The `stat` file contains the most important process metadata in a single line.

#### What `/proc/<pid>/stat` looks like

```
28750 (bash) S 28742 28750 28742 34816 28751 4194304 1234 5678 0 0 12 8 0 0 20 0 1 0 ...
```

All fields are space-separated, but **field 2 (the name) can contain spaces and parentheses**:

```
Field 1  : 28750          PID
Field 2  : (bash)         Process name, ALWAYS wrapped in parentheses
                          Examples: (bash), (my web app), (python3)
Field 3  : S              STATE CHARACTER  <-- WE NEED THIS
Field 4  : 28742          PPID (parent process ID)
Field 5  : 28750          Process group ID
Field 6  : 28742          Session ID
... (41 fields total)
```

#### All Linux process state characters

| State | Character | Meaning |
|-------|-----------|---------|
| Running | `R` | Actively using CPU right now |
| Sleeping | `S` | Waiting for an event (most processes are here) |
| Uninterruptible sleep | `D` | Waiting for I/O — cannot be interrupted (even by kill -9!) |
| Stopped | `T` | Paused by SIGSTOP or being traced by a debugger |
| **Zombie** | **`Z`** | **Dead but not yet reaped by parent** ← WE CHECK THIS |
| Dead | `X` | Being cleaned up, very transient — you rarely see this |

---

### `entry.isdigit()` — Filtering PID Directories

```python
for entry in os.listdir('/proc'):
    if not entry.isdigit():
        continue
```

`os.listdir('/proc')` returns ALL entries in `/proc` — not just PID directories:

```
/proc contents (sample):
  1          <- PID directory ✅
  812        <- PID directory ✅
  28750      <- PID directory ✅
  cpuinfo    <- NOT a PID ❌
  meminfo    <- NOT a PID ❌
  loadavg    <- NOT a PID ❌
  stat       <- NOT a PID ❌
  net        <- NOT a PID ❌
  sys        <- NOT a PID ❌
```

`str.isdigit()` returns `True` only if every character is a digit (0–9):
```python
"28750".isdigit()   -> True   ✅ (PID — keep it)
"cpuinfo".isdigit() -> False  ❌ (skip)
"net".isdigit()     -> False  ❌ (skip)
```

This single filter selects only PID directories, avoiding any attempt to open `/proc/cpuinfo/stat` (which would fail).

---

### The `rfind(')')` Trick — Safe Parsing Despite Spaces in Names

This is the most important technical detail in the script. It is what separates a correct solution from a broken one.

#### Why simple `split()` breaks

If we naively split on spaces:
```python
fields = data.split()
state = fields[2]   # WRONG for names with spaces
```

This works for simple names like `bash`:
```
"28750 (bash) S 28742 ..."
split() -> ["28750", "(bash)", "S", "28742", ...]
fields[2] -> "S"  ✅
```

But **breaks** for names with spaces (which DO exist on Linux):
```
"28750 (my web app) S 28742 ..."
split() -> ["28750", "(my", "web", "app)", "S", "28742", ...]
fields[2] -> "web"  ❌  WRONG
```

Real examples of process names with spaces:
- `(My Application)`
- `(kworker/0:1)`
- `(gmain)` → the GNOME main loop
- `(dbus-daemon)`

#### The `rfind` solution

```python
last_paren = data.rfind(')')    # Find the index of the LAST ')' in the line
state = data[last_paren + 2]    # Skip ')' and the space, land on state char
```

The process name is ALWAYS wrapped in the FIRST `(` and the LAST `)` on the line. After the last `)` comes exactly: `' '` (space) then the state character.

Visual breakdown:
```
"28750 (my web app) S 28742 ..."
        ^          ^
        |          |
  first (        last )   <- data.rfind(')')
                     ^
                     last_paren = 18  (index of last ')')
                      ^
                      last_paren + 1 = 19 -> ' ' (space)
                       ^
                       last_paren + 2 = 20 -> 'S'  ← state character
```

Works perfectly regardless of how many spaces or parentheses the name contains.

#### Extracting the name

```python
first_paren = data.find('(')           # Index of the opening '('
name = data[first_paren + 1 : last_paren]  # Slice between ( and last )
```

```
"28750 (my web app) S ..."
        ^          ^
  first_paren=6   last_paren=18

data[7:18] = "my web app"  ✅
```

`data.find('(')` = scan left-to-right, return index of FIRST `(`.
`data.rfind(')')` = scan right-to-left, return index of LAST `)`.
Slice between them gives the exact process name.

---

### `(FileNotFoundError, IOError)` — The Race Condition

```python
except (FileNotFoundError, IOError):
    continue
```

Between `os.listdir('/proc')` and our `open(f'/proc/{pid}/stat')`, time passes. During that time, the process with that PID might have exited. If it did:

```
os.listdir() returns: [..., "28750", ...]
                             ^
                    process 28750 exists at this moment

# Time passes (microseconds)
# Process 28750 finishes and exits

open('/proc/28750/stat')
                     ^
                     FileNotFoundError! The directory is gone.
```

This is a **race condition** — a timing-dependent situation that is completely normal in process management. The fix is to silently `continue` to the next PID. We do not crash, we do not print an error — we just skip it and move on.

We catch both `FileNotFoundError` (file does not exist) and `IOError` (broader I/O errors, e.g. permission denied on some systems).

---

### Why You Cannot `kill -9` a Zombie

This is a classic trick interview question:

```bash
kill -9 28750   # Try to kill a zombie

# Result:
bash: kill: (28750) - No such process
# OR the command succeeds but the zombie remains
```

`kill` works by sending a **signal** to a running process. Signals are handled by the process's code. A zombie has NO running code — it is dead. There is nothing to receive the signal.

The only way to remove a zombie is to fix the **parent process**:

```
Option 1: Find the parent -> ps -o ppid= -p <zombie_pid>
          Restart the parent -> it calls wait() -> zombie cleaned up

Option 2: If the parent itself has crashed or is stuck,
          kill the parent -> orphaned zombie is adopted by init (PID 1)
          -> init calls wait() automatically -> zombie cleaned up

Option 3: If all else fails -> reboot (clears the entire process table)
```

Our script prints `ps -o ppid= -p {pid}` to give the operator the exact next command.

---

## What the Interviewer Is Looking For

| What they check | What your script demonstrates |
|----------------|-------------------------------|
| What IS a zombie? | Dead process waiting for parent to call `wait()` — not just "a bad process" |
| Why can't you kill -9 a zombie? | No running code = no signal receiver |
| How to actually fix it? | Fix or restart the parent; init adopts orphans |
| `/proc/<pid>/stat` format? | 41 fields, field 3 = state char, names can have spaces |
| Why `rfind(')')` not `split()`? | Process names with spaces break naive split — rfind is the correct parse |
| Race condition handling? | `FileNotFoundError` catch for process-ended-during-scan |
| `isdigit()` filter? | Know that /proc has non-PID entries too |
| When are zombies dangerous? | PID table exhaustion — `fork()` fails when table is full |

---

## How This Convinces the Interviewer

Zombie processes are a real production issue. They appear when:

- A service spawns worker subprocesses but has a bug in its cleanup code (doesn't call `wait()` or `waitpid()`)
- A container orchestrator has a bug in how it handles child process exit (Kubernetes had this — hence `tini` as PID 1 in containers)
- A CI/CD pipeline script launches jobs and crashes before collecting their exit codes

**Say in the interview:**
> *"In production I'd also check for processes in 'D' state — uninterruptible sleep. A handful of D-state processes usually means an I/O problem (NFS hang, disk failure). Unlike zombies which are harmless individually, D-state processes hold kernel locks and can cause the system to hang. This script is one check away from being a full process health scanner."*

---

## Sample Output

```bash
# No zombies (healthy system):
$ python3 zombie_process_scanner.py
Scanning for zombie processes...
----------------------------------------
No zombie processes found. System is clean.

# Zombies found:
$ python3 zombie_process_scanner.py
Scanning for zombie processes...
----------------------------------------
Found 2 zombie process(es):

  PID  : 14823
  Name : defunct_worker
  Fix  : Find parent -> ps -o ppid= -p 14823
         Then restart the parent process to clear the zombie.

  PID  : 14829
  Name : python3
  Fix  : Find parent -> ps -o ppid= -p 14829
         Then restart the parent process to clear the zombie.
```

---

## Usage

```bash
# Run directly — no arguments needed:
python3 zombie_process_scanner.py

# Also visible via shell:
ps aux | grep 'Z'
ps -eo pid,stat,comm | grep ' Z'
```

## Requirements

- Python 3.x
- **Linux only** (reads `/proc` filesystem)
- No root/sudo required — `/proc/<pid>/stat` is readable by all users
- No third-party packages needed
