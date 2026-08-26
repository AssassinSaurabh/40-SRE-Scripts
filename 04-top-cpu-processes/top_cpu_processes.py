#!/usr/bin/env python3
"""
Script 04 - Top CPU Consuming Processes
Identifies top CPU-consuming processes using /proc/<pid>/stat and /proc/stat.
No psutil, no "ps aux" - pure Linux /proc filesystem reads.
"""
import os
import time


def get_process_stats():
    """
    Reads /proc/<pid>/stat for every running process.
    Returns a dict: { pid_str: {"name": <name>, "total_time": <utime+stime>} }
    """
    procs = {}

    # Step 1: List everything inside /proc
    # /proc contains one numbered folder per running process (e.g. /proc/1234/)
    # It also contains non-numeric entries like /proc/cpuinfo, /proc/meminfo, etc.
    # We only want the numbered ones (PIDs).
    proc_list = os.listdir("/proc")

    # Step 2: Filter only numeric entries (those are PIDs)
    # "1234".isdigit() -> True  |  "cpuinfo".isdigit() -> False
    pids = [p for p in proc_list if p.isdigit()]

    for pid in pids:
        try:
            # Step 3: Read /proc/<pid>/stat
            # This file holds the complete CPU accounting for this one process.
            with open(f"/proc/{pid}/stat", "r") as f:
                stat_line = f.read().strip()

            # ---------------------------------------------------------------
            # WHAT DOES /proc/<pid>/stat LOOK LIKE?
            # ---------------------------------------------------------------
            # Example raw line:
            #   1234 (my process name) S 1233 1234 1234 0 -1 4194304 ...
            #
            # Field breakdown (space-separated, 1-indexed per kernel docs):
            #   Field 1  : PID           -> 1234
            #   Field 2  : comm (name)   -> (my process name)  <-- wrapped in ()
            #   Field 3  : state         -> S  (S=Sleeping, R=Running, Z=Zombie)
            #   Field 4  : ppid          -> parent PID
            #   Field 5  : pgrp          -> process group ID
            #   ...more fields...
            #   Field 14 : utime         -> CPU ticks in USER mode
            #   Field 15 : stime         -> CPU ticks in KERNEL (system) mode
            #   Field 16 : cutime        -> waited-for children user ticks
            #   Field 17 : cstime        -> waited-for children system ticks
            # ---------------------------------------------------------------

            # Step 4: Safe split to handle spaces inside process names
            # Problem: process name (field 2) can contain spaces!
            # e.g., "(Web Content)" or "(kworker/0:1H)" would break naive .split()
            #
            # TRICK: Split on " (" to separate PID from the rest.
            # stat_line = "1234 (my process) S 0 ..."
            # After split(" (", 1):
            #   pid_str = "1234"
            #   rest    = "my process) S 0 ..."
            pid_str, rest = stat_line.split(" (", 1)

            # Step 5: Now extract the process name by splitting on ") "
            # rest = "my process) S 0 ..."
            # After split(") ", 1):
            #   comm = "my process"   (the name, without parentheses)
            #   rest = "S 0 ..."      (everything after the name)
            comm, rest = rest.split(") ", 1)

            # Step 6: Split the remaining fields by space
            # rest = "S 1233 1234 1234 0 -1 ..."
            # stats[0]  = state       ("S")
            # stats[1]  = ppid
            # stats[2]  = pgrp
            # stats[3]  = session
            # stats[4]  = tty_nr
            # stats[5]  = tpgid
            # stats[6]  = flags
            # stats[7]  = minflt
            # stats[8]  = cminflt
            # stats[9]  = majflt
            # stats[10] = cmajflt
            # stats[11] = utime  <-- field 14 in kernel docs (0-indexed = 11)
            # stats[12] = stime  <-- field 15 in kernel docs (0-indexed = 12)
            stats = rest.split()

            # Step 7: Extract utime and stime
            # utime = ticks this process spent running in USER space (your code)
            # stime = ticks this process spent running in KERNEL space (syscalls)
            # Together they represent total CPU time consumed by this process.
            utime = int(stats[11])
            stime = int(stats[12])

            procs[pid] = {
                "name": comm,
                "total_time": utime + stime
            }

        except (FileNotFoundError, ProcessLookupError, IndexError):
            # Processes can die mid-read. This is normal on a busy system.
            # FileNotFoundError  -> process exited before we opened the file
            # ProcessLookupError -> PID vanished
            # IndexError         -> stat file was truncated (race condition)
            # We silently skip these - they are NOT bugs.
            pass

    return procs


def get_system_cpu_time():
    """
    Reads the first line of /proc/stat to get total CPU ticks across the whole system.
    Returns the sum of all CPU time fields.
    """
    # -----------------------------------------------------------------------
    # WHAT DOES /proc/stat LOOK LIKE?
    # -----------------------------------------------------------------------
    # The very first line always starts with "cpu" (aggregate of all cores):
    #
    #   cpu  274042 2002 79541 10493813 14350 0 1270 0 0 0
    #        |      |    |     |        |     | |    | | |
    #        user   nice sys   idle     iowait irq soft steal guest guest_nice
    #
    # All values are in "jiffies" (clock ticks, typically 100 per second on Linux).
    #
    # user      : ticks spent running user-space processes
    # nice      : ticks spent running low-priority (niced) user processes
    # system    : ticks spent in kernel mode
    # idle      : ticks spent doing absolutely nothing
    # iowait    : ticks waiting for I/O (disk, network)
    # irq       : ticks servicing hardware interrupts
    # softirq   : ticks servicing software interrupts
    # steal     : ticks stolen by hypervisor (relevant on VMs/cloud)
    # guest     : ticks spent running a virtual CPU for a guest OS
    # guest_nice: ticks spent running a niced guest OS
    #
    # To get TOTAL system ticks: sum ALL of these fields.
    # This total is our denominator when computing any process's CPU %.
    # -----------------------------------------------------------------------
    with open("/proc/stat", "r") as f:
        line = f.readline()         # Only the first line ("cpu ...") is needed

    parts = line.split()[1:]        # Drop the "cpu" label, keep only numbers
    return sum(int(x) for x in parts)


def check_process_health():
    """
    Main function: takes two snapshots 1 second apart, computes CPU % per process,
    and prints the top 5 CPU consumers.
    """
    # -----------------------------------------------------------------------
    # WHY TWO SNAPSHOTS? (The Delta Method)
    # -----------------------------------------------------------------------
    # /proc/<pid>/stat gives CUMULATIVE ticks since the process started.
    # A process that has used 10,000 ticks total over 1 hour is not necessarily
    # busy RIGHT NOW.
    #
    # By taking two readings 1 second apart and computing the DIFFERENCE,
    # we measure how many ticks the process used in THAT SPECIFIC SECOND.
    # This is the same method used by top, htop, pidstat, etc.
    # -----------------------------------------------------------------------

    print("Gathering Snapshot 1...")
    sys_time_1 = get_system_cpu_time()   # Total system ticks at T=0
    procs_1    = get_process_stats()     # Per-process ticks at T=0

    time.sleep(1)                        # Wait exactly 1 second

    print("Gathering Snapshot 2...\n")
    sys_time_2 = get_system_cpu_time()   # Total system ticks at T=1
    procs_2    = get_process_stats()     # Per-process ticks at T=1

    # How many total system ticks elapsed in the 1-second window?
    sys_time_diff = sys_time_2 - sys_time_1

    # Get the number of logical CPU cores.
    # /proc/stat's "cpu" line is the SUM across all cores.
    # A process using 1 full core on a 4-core machine = 25% of system total.
    # Multiplying by num_cores gives the "per-process as % of one core" view,
    # which matches what top/htop shows (can exceed 100% on multi-core).
    num_cores = os.cpu_count() or 1

    results = []

    for pid, data2 in procs_2.items():
        # Only consider processes that existed in BOTH snapshots
        if pid in procs_1:
            # How many ticks did THIS process consume during the 1-second window?
            proc_diff = data2["total_time"] - procs_1[pid]["total_time"]

            if proc_diff > 0 and sys_time_diff > 0:
                # ---------------------------------------------------------------
                # THE CORE FORMULA
                # ---------------------------------------------------------------
                # cpu_percent = (process_ticks_delta / system_ticks_delta) * 100 * cores
                #
                # Example:
                #   system_ticks_delta = 400   (4 cores x 100 ticks/sec)
                #   process_ticks_delta = 100  (process used 100 ticks)
                #   Without core multiplier: (100/400)*100 = 25%  <- system-wide share
                #   With core multiplier:    25% * 4 = 100%       <- means 1 full core
                # ---------------------------------------------------------------
                cpu_percent = (proc_diff / sys_time_diff) * 100 * num_cores
                results.append((pid, data2["name"], cpu_percent))

    # Sort descending by CPU usage (x[2] = cpu_percent)
    results.sort(key=lambda x: x[2], reverse=True)

    # Print top 5 results in a formatted table
    print(f"{\"PID\":<8} {\"PROCESS\":<20} {\"CPU %\"}")
    print("-" * 40)
    for res in results[:5]:
        # res[1][:18] truncates long names to fit the column
        print(f"{res[0]:<8} {res[1][:18]:<20} {res[2]:.1f}%")


if __name__ == "__main__":
    check_process_health()
