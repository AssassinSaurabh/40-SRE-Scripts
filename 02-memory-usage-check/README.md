# 02 - Memory Usage Check

## What This Script Does

This script monitors **system RAM usage** on a Linux system by directly reading the `/proc/meminfo` virtual file.
It uses only Python built-ins — no `psutil` or any external library.

## How It Works

1. Opens and reads `/proc/meminfo` line by line.
2. Parses key-value pairs into a dictionary (e.g., `MemTotal`, `MemAvailable`).
3. Calculates used memory: `MemTotal - MemAvailable`
4. Calculates usage percentage: `(used / total) * 100`
5. Compares against an **80% threshold**:
   - Above 80% → prints a **WARNING**
   - At or below 80% → prints **Memory is healthy**
6. Handles `FileNotFoundError` (non-Linux systems) and all other exceptions.

## Why /proc/meminfo?

`/proc/meminfo` is a Linux kernel virtual file that exposes real-time memory statistics.
Reading it directly (without any library) is a core SRE skill demonstrating understanding of the Linux proc filesystem.

## Key Fields Used

| Field | Meaning |
|---|---|
| `MemTotal` | Total installed RAM (kB) |
| `MemAvailable` | Memory available for new processes (kB) |

> Note: `MemAvailable` is preferred over `MemFree` because it accounts for reclaimable cache.

## SRE Relevance

Memory pressure leads to OOM (Out Of Memory) kills, which crash services. SREs monitor RAM to:
- Detect memory leaks early
- Trigger alerts before the OOM killer fires
- Understand system headroom before scaling events

## Interview Insight

> **Q: How do you check memory usage in Python without psutil?**
> A: Read `/proc/meminfo` directly and parse `MemTotal` and `MemAvailable`.

## Usage

```bash
python3 memory_usage_check.py
```

## Sample Output

```
Memory is healthy. Current usage: 58.72%
# or
WARNING: Memory usage is high at 87.11%!
```

## Requirements

- Python 3.x
- **Linux only** (requires `/proc/meminfo`)
- No third-party packages needed
