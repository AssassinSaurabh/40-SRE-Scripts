# 01 - Disk Usage Check

## What This Script Does

This script monitors the **disk usage of the root filesystem (`/`)** on a Linux/macOS system.
It uses Python's built-in `shutil` module — no external libraries required.

## How It Works

1. Calls `shutil.disk_usage("/")` to get total, used, and free disk space.
2. Calculates usage percentage: `(used / total) * 100`
3. Compares against an **80% threshold**:
   - Above 80% → prints a **WARNING**
   - At or below 80% → prints **Disk is healthy**
4. Catches any unexpected exceptions gracefully without crashing.

## SRE Relevance

Disk exhaustion is one of the most common production incidents. SREs monitor disk usage to:
- Prevent services from failing due to "No space left on device" errors
- Trigger cleanup jobs or alerts before hitting 100%
- This script is the simplest building block of any disk monitoring pipeline

## Interview Insight

> **Q: How do you check disk usage programmatically in Python?**
> A: Use `shutil.disk_usage(path)` which returns a named tuple with `total`, `used`, and `free` in bytes.

## Usage

```bash
python3 disk_usage_check.py
```

## Sample Output

```
Disk is healthy. Current usage: 63.45%
# or
WARNING: Disk usage is high at 85.23%!
```

## Requirements

- Python 3.x
- Works on **Linux and macOS**
- No third-party packages needed
