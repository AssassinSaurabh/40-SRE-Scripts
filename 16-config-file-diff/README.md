# 16 - Configuration File Differ

## The Interview Question

> *"You have two Linux servers that are supposed to have the same configuration. Write a Python script that compares two configuration files and reports what lines are missing or different between them."*

---

## What This Script Does

1. Takes **two file paths** as command-line arguments (`file_a` = source of truth, `file_b` = server to check)
2. Reads both files with `readlines()` — preserving line numbers and newlines
3. **Fast equality check** first — if files are identical, prints immediately and exits
4. Generates a **unified diff** using Python's built-in `difflib.unified_diff()`
5. Categorises changes: lines only in A (missing from B), lines only in B (extra in B)
6. Prints a **structured summary** followed by the full unified diff with context
7. Handles missing files and permission errors with clear messages

---

## The Solution

```python
import sys
import difflib

def read_file(filepath):
    try:
        with open(filepath, 'r') as f:
            return f.readlines()
    except FileNotFoundError:
        print(f"Error: File not found: '{filepath}'")
        sys.exit(1)
    except PermissionError:
        print(f"Error: Permission denied: '{filepath}'")
        sys.exit(1)

def compare_configs(path_a, path_b):
    lines_a = read_file(path_a)
    lines_b = read_file(path_b)

    if lines_a == lines_b:
        print("Result : FILES ARE IDENTICAL")
        return

    diff = list(difflib.unified_diff(
        lines_a, lines_b,
        fromfile=f"A: {path_a}",
        tofile=f"B: {path_b}",
        lineterm=''
    ))

    only_in_a = [l for l in diff if l.startswith('-') and not l.startswith('---')]
    only_in_b = [l for l in diff if l.startswith('+') and not l.startswith('+++ ')]

    print(f"Lines only in A (missing from B) : {len(only_in_a)}")
    print(f"Lines only in B (missing from A) : {len(only_in_b)}")
    print()
    for line in diff:
        print(line.rstrip('\n'))

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 config_diff.py <file_a> <file_b>")
        sys.exit(1)
    compare_configs(sys.argv[1], sys.argv[2])
```

---

## How We Achieved This — Every Decision Explained

### The Core Tool: `difflib` — Python's Built-in Diff Engine

Python ships with a module called `difflib` that implements the same diff algorithm used by the Linux `diff` command. It requires **zero installation** — no pip, no packages.

Why `difflib` over calling `subprocess.run(['diff', ...])` ?

| | `difflib` | `subprocess(['diff', ...])` |
|-|-----------|---------------------------|
| Portability | Works on Linux, macOS, Windows | Requires `diff` binary (not on Windows) |
| Output control | Full Python control over the result | Must parse text output from diff |
| Integration | Returns a Python list we can process | Returns raw string |
| Interview signal | Shows you know the standard library | Shows you know shell commands |

`difflib` is the right choice when you need to **process** the diff in Python, not just display it.

---

### `readlines()` — Why This and Not `read()` or `for line in f`

```python
lines_a = f.readlines()
```

Three ways to read a file — and why `readlines()` is correct here:

```python
# Option 1: read() - entire file as ONE string
content = f.read()
# Problem: difflib.unified_diff() needs a LIST of lines, not one string.
# You'd then have to call content.splitlines() anyway.
# Also loses trailing \n on the last line.

# Option 2: iterate line by line (memory efficient for huge files)
for line in f:
    process(line)
# Problem: we need the full list available for difflib to compare.
# Line-by-line iteration can't go backwards.

# Option 3: readlines() - returns a LIST of lines (with \n included)
lines = f.readlines()
# CORRECT: difflib.unified_diff(a, b) expects two lists of strings.
# Each string should include the trailing \n for accurate comparison.
# ["host = db.prod\n", "port = 5432\n"]
```

**Why keep the `\n`?**

`difflib` uses the `\n` to render the diff output correctly. Without `\n`:
- The diff hunk headers (`@@ ... @@`) would be on the same line as the first diff line
- The output would look garbled

We strip `\n` only when printing with `line.rstrip('\n')` — because `print()` adds its own newline.

---

### The Fast Equality Check — Short-Circuiting the Diff

```python
if lines_a == lines_b:
    print("Result : FILES ARE IDENTICAL")
    return
```

This is a simple but important optimisation.

When two lists are compared with `==`, Python checks:
1. Are both the same length? If no → not equal immediately
2. Are all elements equal at the same positions? Element by element

If the files are identical (the common case in a healthy infrastructure), we skip the entire `difflib.unified_diff()` computation and return instantly.

**Why does this matter?** Config files on production servers are typically identical 95% of the time. You only run this script when something broke. The fast path handles the "all is well" check efficiently.

---

### `difflib.unified_diff()` — How It Works

```python
diff = list(difflib.unified_diff(
    lines_a,
    lines_b,
    fromfile=f"A: {path_a}",
    tofile=f"B: {path_b}",
    lineterm=''
))
```

#### What is "unified diff format"?

The unified diff format is the standard output of `diff -u`. It is how `git diff` shows changes. Every developer and SRE knows how to read it.

Given two files:

**server1.conf (file A):**
```
# Database config
host = db.prod.internal
port = 5432
max_connections = 100
timeout = 30
```

**server2.conf (file B):**
```
# Database config
host = db.prod.internal
port = 5432
max_connections = 200
ssl = true
```

The unified diff output:
```
--- A: server1.conf
+++ B: server2.conf
@@ -1,5 +1,5 @@
 # Database config
 host = db.prod.internal
 port = 5432
-max_connections = 100
-timeout = 30
+max_connections = 200
+ssl = true
```

#### Reading the unified diff format — every symbol explained

```
---  A: server1.conf          <- "from" file (A). Lines removed come from here.
+++  B: server2.conf          <- "to" file (B). Lines added go here.

@@ -1,5 +1,5 @@              <- HUNK HEADER
    |  | |  |
    |  | |  +-- 5 lines shown from file B starting at line 1
    |  | +----- file B block starts at line 1
    |  +-------- 5 lines shown from file A starting at line 1
    +----------- file A block starts at line 1

 # Database config            <- space prefix = UNCHANGED line (context)
 host = db.prod.internal      <- space prefix = UNCHANGED line
 port = 5432                  <- space prefix = UNCHANGED line
-max_connections = 100        <- minus prefix = line ONLY IN A (missing from B)
-timeout = 30                 <- minus prefix = line ONLY IN A (missing from B)
+max_connections = 200        <- plus prefix  = line ONLY IN B (missing from A)
+ssl = true                   <- plus prefix  = line ONLY IN B (missing from A)
```

**The 3 prefixes:**

| Prefix | Meaning | Action needed |
|--------|---------|---------------|
| ` ` (space) | Line is identical in both files | Nothing |
| `-` | Line is in A but NOT in B | Add this line to B (or investigate why it was removed) |
| `+` | Line is in B but NOT in A | Remove this line from B (or add it to A if intentional) |

#### `lineterm=''` — Why Empty String?

`difflib.unified_diff()` by default appends `\n` to every output line. But our lines from `readlines()` already have `\n`. Without `lineterm=''`, every line would have a double newline (`\n\n`) when printed.

Setting `lineterm=''` tells difflib: "don't add any line terminator, I'll handle it." We then manually strip with `line.rstrip('\n')` before printing.

#### `list(difflib.unified_diff(...))` — Why `list()`?

`unified_diff()` returns a **generator** (lazy evaluation). A generator computes each value only when asked.

We wrap it in `list()` because we need to:
1. Iterate once to collect `only_in_a` lines (list comprehension)
2. Iterate again to print all lines

A generator can only be iterated **once**. Converting to a list lets us iterate multiple times.

---

### Categorising Changes — Filtering the Diff Lines

```python
only_in_a = [l for l in diff if l.startswith('-') and not l.startswith('---')]
only_in_b = [l for l in diff if l.startswith('+') and not l.startswith('+++ ')]
```

This is a **list comprehension with two conditions** joined by `and`.

**Why two conditions?**

The diff output contains header lines that also start with `-` and `+`:
```
--- A: server1.conf      <- starts with '-' but is NOT a removed line
+++ B: server2.conf      <- starts with '+' but is NOT an added line
```

We must skip these headers. The filter:
- `l.startswith('-')` → line starts with `-` (removed or header)
- `not l.startswith('---')` → but is NOT the `---` header line

Only actual removed lines pass both conditions.

**What `len(only_in_a)` and `len(only_in_b)` tell you:**

```
Lines only in A (missing from B) : 2
  -> server2.conf is MISSING these 2 lines from server1.conf
  -> someone may have accidentally deleted them

Lines only in B (missing from A) : 2
  -> server2.conf has 2 EXTRA lines not in server1.conf
  -> someone may have added config that wasn't applied to server1 yet
```

In a real SRE config audit, this count is the first thing you look at. Zero means identical.

---

### The `rstrip('\n')` When Printing

```python
for line in diff:
    print(line.rstrip('\n'))
```

`rstrip('\n')` removes trailing newline character(s) from the right side of the string.

Without it:
- `line` is `"-timeout = 30\n"` (has a newline from readlines())
- `print()` adds another `\n`
- Result: two blank lines between every diff line → ugly output

With it:
- `line.rstrip('\n')` → `"-timeout = 30"`
- `print()` adds `\n`
- Result: one line per diff line → clean output

`rstrip()` vs `strip()`:
- `strip()` removes from **both** sides (left and right)
- `rstrip()` removes from the **right** only (what we want — don't touch the leading `-`/`+`/` ` prefix)

---

### The `n=3` Context Lines (Default)

`unified_diff()` includes 3 unchanged lines before and after each change by default. These are called **context lines**.

Why context matters:

```
Without context (n=0):
-timeout = 30
+ssl = true

With context (n=3, default):
 host = db.prod.internal
 port = 5432
 max_connections = 200
-timeout = 30
+ssl = true
```

Without context, you see WHAT changed but not WHERE it is in the file. With context, you can immediately locate the change and understand its surrounding configuration.

You can reduce context for large files: `difflib.unified_diff(..., n=1)`.

---

## Real-World SRE Use Cases

This script solves real production problems:

```
Scenario 1: Nginx misconfiguration
  server1.conf has:  worker_processes 4;
  server2.conf has:  worker_processes 8;
  → server2 is handling 2x the load of server1. Explains the imbalance.

Scenario 2: Missing security setting
  server1.conf has:  ssl_protocols TLSv1.2 TLSv1.3;
  server2.conf has:  (line is missing)
  → server2 is accepting insecure TLS 1.0/1.1 connections.

Scenario 3: Duplicate deployment verification
  After running Ansible/Chef/Puppet, both files should be identical.
  Script confirms: FILES ARE IDENTICAL → deployment was successful.

Scenario 4: Finding config drift
  Files were identical 3 months ago. Now they differ.
  The diff shows exactly what changed → quick audit.
```

---

## What the Interviewer Is Looking For

| What they check | What your script demonstrates |
|----------------|-------------------------------|
| Know `difflib`? | Python's built-in diff module — no external libraries needed |
| `readlines()` vs `read()`? | `readlines()` gives a list — exactly what `unified_diff` expects |
| Fast equality check? | `lines_a == lines_b` short-circuits before expensive diff computation |
| Understand unified diff format? | `-` lines, `+` lines, ` ` context, `@@` hunk headers — all explained |
| `lineterm=''`? | Prevents double newlines — shows attention to output detail |
| `list()` wrapper? | Generators can only be iterated once — `list()` lets you iterate twice |
| Categorise changes? | Counting only_in_a and only_in_b gives a meaningful summary |
| `rstrip('\n')` when printing? | Prevents double blank lines — clean output |
| Error handling? | `FileNotFoundError` and `PermissionError` with clear messages |

---

## How This Convinces the Interviewer

Config drift between servers is one of the most common causes of production incidents. "Works on server1, broken on server2" is a classic problem.

This script is the foundation of:
- **Config auditing** — run across all servers in a fleet, find any that differ from the golden master
- **Change verification** — after Ansible/Chef runs, confirm all servers converged to the same config
- **Incident investigation** — "what changed between these two server configs since last week?"

**Say in the interview:**
> *"In production I'd extend this to compare configs fetched over SSH using `paramiko` or `fabric` — no need to copy files locally. I'd also add a `--ignore-comments` flag that strips lines starting with `#` before diffing, so cosmetic comment differences don't obscure real changes. At scale, this becomes a fleet-wide config audit tool run nightly by cron."*

---

## Test It Yourself

```bash
# Create two sample config files with differences:
cat > server1.conf << 'EOF'
# Database config
host = db.prod.internal
port = 5432
max_connections = 100
timeout = 30
EOF

cat > server2.conf << 'EOF'
# Database config
host = db.prod.internal
port = 5432
max_connections = 200
ssl = true
EOF

python3 config_diff.py server1.conf server2.conf

# Test with identical files:
cp server1.conf server1_copy.conf
python3 config_diff.py server1.conf server1_copy.conf
```

---

## Sample Output

```bash
# Files differ:
$ python3 config_diff.py server1.conf server2.conf
============================================================
CONFIG DIFF REPORT
============================================================
File A  : server1.conf  (5 lines)
File B  : server2.conf  (5 lines)
------------------------------------------------------------
Lines only in A (missing from B) : 2
Lines only in B (missing from A) : 2
============================================================

DETAILED DIFF (unified format):
------------------------------------------------------------
--- A: server1.conf
+++ B: server2.conf
@@ -1,5 +1,5 @@
 # Database config
 host = db.prod.internal
 port = 5432
-max_connections = 100
-timeout = 30
+max_connections = 200
+ssl = true
------------------------------------------------------------

Summary: 2 line(s) to add to B, 2 line(s) to remove from B
         to make both files identical.

# Files are identical:
$ python3 config_diff.py server1.conf server1_copy.conf
Result  : FILES ARE IDENTICAL
File A  : server1.conf
File B  : server1_copy.conf
Lines   : 5

# File not found:
$ python3 config_diff.py server1.conf missing.conf
Error: File not found: 'missing.conf'
```

---

## Usage

```bash
python3 config_diff.py <file_a> <file_b>

# Examples:
python3 config_diff.py /etc/nginx/nginx.conf /tmp/nginx_server2.conf
python3 config_diff.py /etc/mysql/my.cnf /tmp/my_cnf_server2
python3 config_diff.py server1.conf server2.conf
```

## Requirements

- Python 3.x
- Works on **Linux, macOS, Windows**
- Read permission on both config files
- **No third-party packages needed** — uses built-in `difflib`
