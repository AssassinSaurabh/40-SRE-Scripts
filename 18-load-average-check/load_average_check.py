#!/usr/bin/env python3
"""
Script 18 - Linux System Load Average Checker
Reads the 1-minute, 5-minute, and 15-minute load averages from /proc/loadavg.
Warns if the 1-minute load average exceeds the number of available CPU cores.
No third-party libraries - uses built-in os module only.
Linux only (reads /proc/loadavg).
"""
import os


def check_load_average():
    """
    Reads /proc/loadavg and os.cpu_count() to assess system load health.
    Prints all three load averages, core count, and a clear HEALTHY/OVERLOADED verdict.
    """

    # -------------------------------------------------------------------
    # STEP 1: Read /proc/loadavg
    # -------------------------------------------------------------------
    # /proc/loadavg is a virtual file maintained by the Linux kernel.
    # It is updated every 5 seconds by the kernel scheduler.
    #
    # The file contains exactly ONE LINE. Example content:
    #   0.52 0.38 0.21 1/412 28750
    #
    # Field breakdown:
    #   Field 1 : 0.52  -> 1-minute  load average  <- THE MAIN ALERT METRIC
    #   Field 2 : 0.38  -> 5-minute  load average
    #   Field 3 : 0.21  -> 15-minute load average
    #   Field 4 : 1/412 -> running_tasks/total_tasks
    #                       1   = processes currently ON CPU right now
    #                       412 = total processes/threads existing on the system
    #   Field 5 : 28750 -> PID of the most recently created process
    #
    # We only need fields 1, 2, 3 for this check.
    # -------------------------------------------------------------------
    with open('/proc/loadavg', 'r') as f:
        content = f.read()          # e.g. "0.52 0.38 0.21 1/412 28750
"

    # split() with no arguments splits on ANY whitespace (spaces, tabs, newlines)
    # and discards empty strings. Returns a list of tokens.
    # ["0.52", "0.38", "0.21", "1/412", "28750"]
    parts = content.split()

    # Convert string tokens to floats for numeric comparison.
    # "0.52" -> 0.52  (float)
    # We cannot compare strings: "0.52" > "8" is True (lexicographic!) — WRONG.
    # float() gives us the correct numeric value.
    load_1min  = float(parts[0])   # 1-minute  load average
    load_5min  = float(parts[1])   # 5-minute  load average
    load_15min = float(parts[2])   # 15-minute load average

    # -------------------------------------------------------------------
    # STEP 2: Get the number of CPU cores
    # -------------------------------------------------------------------
    # os.cpu_count() returns the number of LOGICAL CPUs (threads) visible
    # to the OS. This includes hyperthreaded cores.
    #
    # Examples:
    #   4-core CPU (no hyperthreading)   -> os.cpu_count() = 4
    #   4-core CPU (with hyperthreading) -> os.cpu_count() = 8
    #   2-socket, 16-core CPU each       -> os.cpu_count() = 32
    #
    # WHY compare load against CPU count and NOT a fixed threshold?
    # Load average measures the queue of processes waiting for CPU time.
    # A load of 4.0 on a 1-core machine = severe overload (queue of 4 processes).
    # A load of 4.0 on an 8-core machine = perfectly idle (each core handles 0.5).
    #
    # The correct threshold is ALWAYS = number of cores.
    # load > cores  -> system is overloaded (queue is backing up)
    # load <= cores -> system has capacity to handle all runnable processes
    #
    # Returns None if it cannot be determined (very rare). Default to 1 to be safe.
    # -------------------------------------------------------------------
    cpu_count = os.cpu_count() or 1

    # -------------------------------------------------------------------
    # STEP 3: Print the report
    # -------------------------------------------------------------------
    print("=" * 50)
    print("System Load Average Report")
    print("=" * 50)
    print(f"  Load (1 min)  : {load_1min}")
    print(f"  Load (5 min)  : {load_5min}")
    print(f"  Load (15 min) : {load_15min}")
    print(f"  CPU Cores     : {cpu_count}")
    print("-" * 50)

    # -------------------------------------------------------------------
    # THE ALERT LOGIC
    # -------------------------------------------------------------------
    # Primary check: 1-minute load vs CPU count.
    # The 1-minute average reacts fastest to sudden spikes.
    # The 5-minute and 15-minute averages give trend context.
    # -------------------------------------------------------------------
    ratio = load_1min / cpu_count   # How "full" the CPU queue is (0.0 to ∞)

    if load_1min > cpu_count:
        print(f"  Status  : OVERLOADED")
        print(f"  Detail  : 1-min load ({load_1min}) > CPU cores ({cpu_count})")
        print(f"  Load %  : {ratio * 100:.0f}% of capacity")
        print(f"  Action  : Run 'top' or check Script 04 (top CPU processes).")
    else:
        print(f"  Status  : HEALTHY")
        print(f"  Detail  : 1-min load ({load_1min}) <= CPU cores ({cpu_count})")
        print(f"  Load %  : {ratio * 100:.0f}% of capacity")

    print("=" * 50)

    # Trend analysis using all three averages
    if load_1min > load_5min > load_15min:
        print("  Trend   : RISING  — load is increasing over time.")
    elif load_1min < load_5min < load_15min:
        print("  Trend   : FALLING — load is decreasing, recovering from a spike.")
    else:
        print("  Trend   : STABLE  — no significant trend detected.")


if __name__ == "__main__":
    check_load_average()
