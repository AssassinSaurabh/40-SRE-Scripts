# 20 - Memory Leak Detector

## The Interview Question

> *"Write a small Python script that reads a file containing timestamped memory usage and detects whether memory usage has continuously increased across the last 3 measurements."*

---

## What This Script Does

1. Takes a **log file path** as a command-line argument
2. Reads every line and extracts the **last token** on each line (the memory value)
3. Skips blank lines — does not care about timestamp format
4. Guards against fewer than 3 readings
5. Slices `values[-3:]` to get the most recent 3 measurements
6. Uses a **chained comparison** `a < b < c` to check for strict continuous increase
7. Prints `WARNING` if memory is rising, `OK` if not

---

## The Solution

```python
import sys

def check_memory_trend(filepath):
    values = []
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                values.append(float(line.split()[-1]))
    except FileNotFoundError:
        print(f"Error: File not found: '{filepath}'")
        sys.exit(1)

    if len(values) < 3:
        print(f"Not enough data: {len(values)} reading(s), need at least 3.")
        return

    last3 = values[-3:]
    print(f"Last 3 values : {last3[0]} MB -> {last3[1]} MB -> {last3[2]} MB")

    if last3[0] < last3[1] < last3[2]:
        print("Status : WARNING — Memory is continuously increasing! Possible leak.")
    else:
        print("Status : OK — Memory is not continuously increasing.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 memory_leak_detector.py <log_file>")
        sys.exit(1)
    check_memory_trend(sys.argv[1])
```

---

## How We Achieved This — Every Decision Explained

### The Log File Format — What We Expect

```
2024-01-15 10:00:00 512
2024-01-15 10:05:00 520
2024-01-15 10:10:00 535
2024-01-15 10:15:00 548
```

Each line: timestamp (one or two words) + memory value (last word).

The script does **not care about the timestamp format**. It always reads `line.split()[-1]` — the last token. This means it works for:

```
2024-01-15 10:00:00 512       <- date + time + value
10:00:00 512                  <- time only + value
1705312200 512                <- Unix epoch + value
measurement_1 512             <- any label + value
512                           <- value alone (no timestamp)
```

All of the above produce `[-1]` = `"512"`. One parsing rule, all formats handled.

---

### `line.split()[-1]` — Getting the Last Token

```python
line = "2024-01-15 10:00:00 512"
parts = line.split()          # ["2024-01-15", "10:00:00", "512"]
value = parts[-1]             # "512"  (last element)
float(value)                  # 512.0
```

`split()` with no argument splits on **any whitespace** (spaces, tabs) and removes empty strings. No delimiter needed.

`[-1]` in Python means **the last element** of a list. Negative indices count from the right:
```
list  = ["2024-01-15", "10:00:00", "512"]
index =  [    0             1         2  ]  (positive)
index =  [   -3            -2        -1  ]  (negative)
```

`[-1]` always gives the last item regardless of how many tokens are on the line.

`float()` handles both `"512"` (integer string → 512.0) and `"512.4"` (decimal string → 512.4). Using `int()` would crash on `"512.4"`. `float()` is the safe, general choice.

---

### `values[-3:]` — Getting the Last 3 Elements

```python
values = [512, 495, 520, 535, 548]
last3  = values[-3:]            # [520, 535, 548]
```

`values[-3:]` is a **slice**. It means: start from index `-3` (3rd from the end) and go to the end of the list.

Why the last 3 and not all values?

- Old readings may be from before a service restart — not relevant to current behaviour
- A continuous rise in the **most recent** 3 points is a strong, immediate signal
- The question specifically says "across the last 3 measurements"

If the list has exactly 3 elements, `values[-3:]` returns all 3. If it has 100, it returns only the last 3. Safe in all cases.

---

### The Chained Comparison — `last3[0] < last3[1] < last3[2]`

```python
if last3[0] < last3[1] < last3[2]:
```

This is Python's **chained comparison** — a feature not found in most languages. It is equivalent to:

```python
if last3[0] < last3[1] and last3[1] < last3[2]:
```

Both conditions must be `True`. The middle value (`last3[1]`) is evaluated only once.

**What "continuously increasing" means — all four cases:**

```
Reading 1 → Reading 2 → Reading 3     Result
─────────────────────────────────────────────
512       →   520     →   535         True  ✅  (both steps UP)
512       →   520     →   510         False ❌  (step 2 went DOWN)
512       →   512     →   535         False ❌  (step 1 FLAT, not strictly greater)
535       →   520     →   512         False ❌  (both steps DOWN)
```

`<` is **strict** less-than. Equal values (`512 < 512`) are `False` — a flat reading is not a leak signal.

---

### `if not line` — Skipping Blank Lines

```python
line = line.strip()
if not line:
    continue
```

`line.strip()` removes leading/trailing whitespace and `\n` newlines. If a line was blank (just `\n` or spaces), after stripping it becomes an empty string `""`.

In Python, an empty string is **falsy**: `bool("") == False`. So `if not line` catches empty strings and skips them with `continue`.

Without this guard, `"".split()` returns `[]` (empty list), and `[][-1]` raises `IndexError`. The guard protects against crashes on blank lines.

---

### The `< 3` Guard — Minimum Data Check

```python
if len(values) < 3:
    print(f"Not enough data: {len(values)} reading(s), need at least 3.")
    return
```

Checking a trend requires at least 3 data points — you cannot have "continuously increasing" with 1 or 2 values. Without this guard, `values[-3:]` on a 2-element list returns both elements, and `last3[0] < last3[1] < last3[2]` would raise `IndexError`.

`return` (not `sys.exit(1)`) because "not enough data" is not an error — it's just insufficient input. The script ran correctly; we just cannot draw a conclusion yet.

---

### Why Last 3 and Not Last 5 or 10?

The question specifies 3. In practice:

| Window size | Signal quality | Latency to detect |
|-------------|---------------|-------------------|
| 3 readings | Fast detection, more noise | Low |
| 5 readings | Balanced | Medium |
| 10 readings | High confidence, slow detection | High |

For an interview: 3 is the specified requirement. In production, you might use 5 with exponential moving average to filter noise. The code structure is identical — just change the `3` in `values[-3:]`.

---

## What the Interviewer Is Looking For

| What they check | What your script demonstrates |
|----------------|-------------------------------|
| `line.split()[-1]`? | Last-token extraction — works for any timestamp format |
| `float()` not `int()`? | Handles decimal memory values without crashing |
| Blank line guard? | `if not line: continue` — defensive parsing |
| `values[-3:]` slice? | Last 3 of N values, not hardcoded indices |
| `< 3` guard? | Handles edge case: not enough data |
| Chained comparison? | `a < b < c` — Python idiom, strictly increasing |
| `return` vs `sys.exit`? | Distinguishes insufficient data (normal) from error (file missing) |

---

## How This Convinces the Interviewer

Memory leak detection is a real SRE problem. Applications that leak memory cause:
- Gradual slowdown as the OS swaps to disk
- OOM (Out of Memory) killer events — the kernel kills the process suddenly
- Service restarts with no visible root cause in app logs

This pattern — read metrics file, check last N readings for a trend — is the core of many monitoring tools.

**Say in the interview:**
> *"In production I'd extend this to also calculate the rate of increase — MB per minute — to distinguish a slow steady leak from a sudden spike. I'd also use a longer window (last 5 or 10 readings) and require a threshold like 'each step must increase by at least 10 MB' to avoid false alarms from normal fluctuation. This is how Prometheus alerting rules work: `increase(memory[5m]) > threshold`."*

---

## Test It Yourself

```bash
# Create a test log file with a memory leak pattern:
cat > memory_usage.log << 'EOF'
2024-01-15 10:00:00 512
2024-01-15 10:05:00 520
2024-01-15 10:10:00 535
2024-01-15 10:15:00 548
EOF
python3 memory_leak_detector.py memory_usage.log

# Create a log file without a leak (memory drops in middle):
cat > memory_ok.log << 'EOF'
2024-01-15 10:00:00 548
2024-01-15 10:05:00 530
2024-01-15 10:10:00 520
2024-01-15 10:15:00 525
EOF
python3 memory_leak_detector.py memory_ok.log
```

---

## Sample Output

```bash
# Memory is leaking (last 3 all rising):
$ python3 memory_leak_detector.py memory_usage.log
Total readings : 4
Last 3 values  : 520.0 MB -> 535.0 MB -> 548.0 MB
---------------------------------------------
Status : WARNING — Memory is continuously increasing!
         Possible memory leak. Investigate the application.

# Memory is stable / fluctuating:
$ python3 memory_leak_detector.py memory_ok.log
Total readings : 4
Last 3 values  : 530.0 MB -> 520.0 MB -> 525.0 MB
---------------------------------------------
Status : OK — Memory is not continuously increasing.

# Not enough data:
$ python3 memory_leak_detector.py two_readings.log
Not enough data: 2 reading(s), need at least 3.

# File not found:
$ python3 memory_leak_detector.py missing.log
Error: File not found: 'missing.log'
```

---

## Usage

```bash
python3 memory_leak_detector.py <log_file>

# Examples:
python3 memory_leak_detector.py memory_usage.log
python3 memory_leak_detector.py /var/log/app/memory_stats.log
```

## Requirements

- Python 3.x
- Works on **Linux, macOS, Windows**
- Log file must have memory value as the **last token** on each line
- **No third-party packages needed**
