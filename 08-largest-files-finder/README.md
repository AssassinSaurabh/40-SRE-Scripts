# 08 - Top 5 Largest Files Finder

## The Interview Question

> *"A server's disk is filling up. Write a Python script that finds the 5 largest files inside a given directory."*

---

## What This Script Does

1. Recursively walks an entire directory tree (every subfolder, every depth)
2. Gets the size of every file it finds
3. Skips symlinks safely (avoids double-counting and infinite loops)
4. Handles permission errors and race conditions without crashing
5. Sorts and returns the **Top 5 largest files** with sizes in MB

---

## The Clean Solution

```python
import os

def get_top_5_largest_files(directory):
    file_list = []

    for root, dirs, files in os.walk(directory):
        for file in files:
            filepath = os.path.join(root, file)
            try:
                if not os.path.islink(filepath):
                    file_size = os.path.getsize(filepath)
                    file_list.append((file_size, filepath))
            except OSError:
                pass

    file_list.sort(key=lambda x: x[0], reverse=True)
    return file_list[:5]

if __name__ == '__main__':
    top_5 = get_top_5_largest_files("/var/log")
    for size, path in top_5:
        print(f"{size / (1024*1024):.2f} MB  -  {path}")
```

---

## How We Achieved This — Every Decision Explained

### The Core: `os.walk()` — How Recursive Traversal Works

`os.walk()` is one of the most powerful functions in Python's standard library.
It traverses a directory tree for you — no manual recursion needed.

```
os.walk("/var/log")
```

Imagine your directory looks like this:
```
/var/log/
├── syslog           <- file
├── auth.log         <- file
├── apt/
│   └── history.log  <- file
└── nginx/
    ├── access.log   <- file
    └── error.log    <- file
```

`os.walk()` visits each folder ONE AT A TIME and gives you a **3-tuple** for each:

```
Iteration 1:  root = "/var/log"         dirs = ["apt", "nginx"]  files = ["syslog", "auth.log"]
Iteration 2:  root = "/var/log/apt"     dirs = []                files = ["history.log"]
Iteration 3:  root = "/var/log/nginx"   dirs = []                files = ["access.log", "error.log"]
```

- `root` = the folder we are currently inside (full path string)
- `dirs` = names of subfolders inside `root` (we don't need these)
- `files` = names of files inside `root` — just names, NOT full paths

This is how it visits every single file no matter how deep the tree goes.

### Why `os.path.join(root, file)` and not just `file`?

```python
filepath = os.path.join(root, file)
```

`file` from `os.walk()` is **only the filename** — no path information:
```
file = "access.log"                            <- just the name
filepath = "/var/log/nginx/access.log"         <- usable full path
```

`os.path.join()` correctly handles the `/` separator regardless of OS.
Never do `root + "/" + file` — it breaks on Windows and looks amateurish.

### The Symlink Problem — Why `os.path.islink()` Matters

A **symlink** (symbolic link) is a file that is just a pointer to another file.

```bash
# Example symlinks on Linux:
/var/log/syslog.1 -> /var/log/syslog     # Log rotation creates these
/etc/resolv.conf  -> /run/systemd/resolve/stub-resolv.conf
```

**What goes wrong if we DON'T check for symlinks:**

Problem 1 — **Double counting:**
```
/var/log/syslog      -> 500 MB  (real file)
/var/log/syslog.1    -> 500 MB  (symlink to syslog - same file!)
```
Both appear in our list, but it's the SAME 500 MB counted twice.

Problem 2 — **Dangerous /proc symlinks:**
```
/proc/1/exe -> /usr/bin/systemd
```
Following proc symlinks gives garbage sizes or can hang.

Problem 3 — **Circular symlinks:**
```
/tmp/a -> /tmp/b
/tmp/b -> /tmp/a    <- infinite loop!
```

**The fix:**
```python
if not os.path.islink(filepath):
    # Only process real files, skip all symlinks
```

`os.path.islink()` returns `True` for symlinks — we skip those with `not`.

### Why `os.path.getsize()` — Not Reading the File

```python
file_size = os.path.getsize(filepath)
```

`os.path.getsize()` reads the size from the **filesystem's inode (metadata)**.
It does NOT open or read the file content.

This means:
- It works on a 1TB file in microseconds
- It does not use any RAM proportional to file size
- It is safe for binary files, locked files, actively-written log files

### The Exception: `OSError` — Why Not `PermissionError`?

```python
except OSError:
    pass
```

We catch `OSError` (not the more specific `PermissionError`) because multiple things can go wrong:

| Exception | When it happens |
|-----------|----------------|
| `PermissionError` | We don't have read access to this file |
| `FileNotFoundError` | File was deleted between `os.walk()` listing it and our `getsize()` call |
| `OSError` (general) | Stale NFS mount, bad disk sector, network file system timeout |

`PermissionError` and `FileNotFoundError` are both subclasses of `OSError`.
Catching `OSError` catches all of them in one line.

**Why `pass` and not print a warning?**
On `/var/log` there can be hundreds of files. Printing a warning for every unreadable file would flood the output. We silently skip and continue scanning.

**Why `pass` and NOT `continue`?**
`pass` inside an `except` block is fine — `continue` would also work here but is redundant since there's no more code in the `try` block after the `except`. `pass` is the conventional "do nothing" signal.

### Sorting with `lambda` — How It Works

```python
file_list.sort(key=lambda x: x[0], reverse=True)
```

`file_list` is a list of tuples: `[(size1, path1), (size2, path2), ...]`

`key=lambda x: x[0]` tells Python: "to sort these tuples, compare by the first element (x[0]) of each tuple" — which is the file size.

`reverse=True` means descending order — biggest first.

Without `key=lambda x: x[0]`, Python would sort by first element anyway (default tuple comparison). The lambda makes the intent **explicit and readable**.

```
Before sort: [(500, "/a"), (9000, "/b"), (100, "/c")]
After sort:  [(9000, "/b"), (500, "/a"), (100, "/c")]
```

### Converting Bytes to MB for Display

```python
size_mb = size / (1024 * 1024)
```

```
1 KB  = 1,024 bytes
1 MB  = 1,024 KB = 1,048,576 bytes
1 GB  = 1,024 MB = 1,073,741,824 bytes
```

We divide bytes by `1024 * 1024` to get MB.
`f"{size_mb:.2f}"` formats it to 2 decimal places.

> Note: This uses MiB (mebibytes, base-1024), which matches what `ls -lh` and `du` show on Linux. Some tools use base-1000 (where 1 MB = 1,000,000 bytes) — the difference is about 5%.

---

## What the Interviewer Is Looking For

| What they check | What your script demonstrates |
|----------------|-------------------------------|
| Do you know recursive traversal? | `os.walk()` — Python's idiomatic directory walker |
| Symlink awareness? | `os.path.islink()` check shows production awareness |
| Memory efficiency? | Never load file content — `os.path.getsize()` reads metadata only |
| Race condition handling? | `OSError` catch for files deleted during scan |
| Clean sorting? | `lambda` with `sort()` — Pythonic and readable |

A candidate who uses `os.listdir()` in a manual recursive function shows they don't know `os.walk()`.
A candidate who skips the symlink check shows they haven't dealt with real Linux filesystems.

---

## How This Convinces the Interviewer

Disk filling up is a **top-3 production incident type**. SREs deal with it constantly.

Real-world uses of this script pattern:
- **Incident response**: Server at 95% disk — run this, find the culprit in 5 seconds
- **Scheduled audit**: Cron job that emails the top 10 largest files weekly
- **Log rotation verification**: Confirm no single log file grew beyond a threshold
- **Pre-deploy check**: Ensure disk has enough free space before deploying

**Say in the interview:**
> *"In production I'd extend this to also check file modification time so I can find large files that are also OLD — those are often safe to archive or delete. I'd also add a size threshold alert, so it only pages oncall if a file exceeds, say, 10GB."*

---

## Test It Yourself

```bash
# Scan /tmp (always accessible):
# Edit the last line: target_directory = "/tmp"
python3 largest_files_finder.py

# Scan your home directory:
# target_directory = os.path.expanduser("~")

# Scan current directory:
# target_directory = "."
```

---

## Sample Output

```
Scanning: /var/log
Looking for the 5 largest files...

Rank   Size (MB)    File Path
------------------------------------------------------------
1      847.23       /var/log/syslog
2      412.05       /var/log/nginx/access.log
3      203.11       /var/log/journal/abc123/system.journal
4      98.67        /var/log/mysql/mysql-slow.log
5      45.32        /var/log/apt/history.log
```

---

## Usage

```bash
python3 largest_files_finder.py
```

Edit `target_directory` in the script to point to the path you want to scan.

## Requirements

- Python 3.x
- Works on **Linux and macOS**
- Read permission on the target directory
- No third-party packages needed
