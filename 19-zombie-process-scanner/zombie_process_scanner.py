#!/usr/bin/env python3
"""
Script 19 - Zombie Process Scanner
Scans all running Linux processes and reports any zombie processes.
Reads /proc/<pid>/stat for each process to check its state character.
A state of 'Z' means zombie.
No third-party libraries - uses built-in os module only.
Linux only (reads /proc filesystem).
"""
import os


def find_zombies():
    """
    Walks /proc, reads each process's stat file, and returns a list
    of (pid, name) tuples for every zombie process found.
    """
    zombies = []

    # -------------------------------------------------------------------
    # STEP 1: List all entries in /proc
    # -------------------------------------------------------------------
    # /proc is a virtual filesystem maintained by the Linux kernel.
    # Every running process gets a subdirectory named after its PID.
    # For example: /proc/1, /proc/812, /proc/28750
    #
    # /proc also contains non-PID entries like:
    #   /proc/cpuinfo, /proc/meminfo, /proc/loadavg, /proc/stat, etc.
    #
    # entry.isdigit() filters to ONLY the numeric PID directories.
    # "cpuinfo".isdigit() = False  (skipped)
    # "1234".isdigit()    = True   (kept - it's a PID)
    # -------------------------------------------------------------------
    for entry in os.listdir('/proc'):
        if not entry.isdigit():
            continue   # Skip non-PID entries like /proc/cpuinfo

        pid = entry

        try:
            # ---------------------------------------------------------------
            # STEP 2: Read /proc/<pid>/stat
            # ---------------------------------------------------------------
            # /proc/<pid>/stat is a single-line file containing key process
            # information that the kernel updates in real time.
            #
            # Example line:
            # 28750 (bash) S 28742 28750 28742 34816 28751 4194304 ...
            #
            # Field breakdown (space-separated):
            #   Field 1  : 28750       -> PID (process ID)
            #   Field 2  : (bash)      -> Process name, in parentheses
            #                            CAN contain spaces and parentheses
            #                            e.g. (my app) or (bash (test))
            #   Field 3  : S           -> STATE CHARACTER  <- WE NEED THIS
            #   Field 4  : 28742       -> PPID (parent PID)
            #   Field 5+ : ...         -> more fields (priority, memory, etc.)
            #
            # State character meanings:
            #   R  = Running          (actively using CPU)
            #   S  = Sleeping         (waiting for event, most common)
            #   D  = Uninterruptible sleep (waiting for I/O, cannot be killed)
            #   T  = Stopped          (SIGSTOP sent, paused)
            #   Z  = Zombie           <- THE ONE WE ARE LOOKING FOR
            #   X  = Dead             (being cleaned up, very transient)
            # ---------------------------------------------------------------
            stat_path = f'/proc/{pid}/stat'
            with open(stat_path, 'r') as f:
                data = f.read()

            # ---------------------------------------------------------------
            # STEP 3: Parse the state character safely
            # ---------------------------------------------------------------
            # The process name field (between parentheses) can contain spaces,
            # so we CANNOT just split on whitespace to find field 3.
            #
            # Example of a tricky process name:
            #   28750 (my web app) S 28742 ...
            #   split() would give: ["28750", "(my", "web", "app)", "S", ...]
            #   split()[2] would give "web" -- WRONG
            #
            # Safe approach: find the LAST closing parenthesis.
            # The process name always ends at the last ')' on the line.
            # After that last ')' comes: a space, then the state character.
            #
            # data.rfind(')') returns the index of the LAST ')' in the string.
            # rfind = "reverse find" = scan from the RIGHT side.
            # ---------------------------------------------------------------
            last_paren = data.rfind(')')

            # data[last_paren + 2] skips the closing ')' and the space after it.
            # last_paren     -> position of ')'
            # last_paren + 1 -> position of ' ' (space)
            # last_paren + 2 -> position of the STATE character
            state = data[last_paren + 2]

            # ---------------------------------------------------------------
            # STEP 4: Check if state is 'Z' (Zombie)
            # ---------------------------------------------------------------
            if state == 'Z':
                # Extract the process name from between the parentheses.
                # data.find('(') = index of the first '('
                # data[first_open + 1 : last_paren] = everything between ( and last )
                first_paren = data.find('(')
                name = data[first_paren + 1 : last_paren]
                zombies.append((pid, name))

        except (FileNotFoundError, IOError):
            # The process ended between our os.listdir() scan and our open().
            # This is completely normal -- processes start and stop constantly.
            # We silently skip these and continue.
            continue

    return zombies


def main():
    print("Scanning for zombie processes...")
    print("-" * 40)

    zombies = find_zombies()

    if not zombies:
        print("No zombie processes found. System is clean.")
        return

    print(f"Found {len(zombies)} zombie process(es):
")

    for pid, name in zombies:
        print(f"  PID  : {pid}")
        print(f"  Name : {name}")
        # A zombie cannot be killed directly (it has no code running).
        # The FIX is to find and restart the PARENT process so it calls wait()
        # to collect the zombie's exit status, which removes it from the table.
        print(f"  Fix  : Find parent -> ps -o ppid= -p {pid}")
        print(f"         Then restart the parent process to clear the zombie.")
        print()


if __name__ == "__main__":
    main()
