#!/usr/bin/env python3
"""
Script 10 - Stale Log File Checker
Checks whether an application log file has been updated recently.
If the log has not been modified for more than 5 minutes, prints a warning.
No third-party libraries - uses built-in os, sys, time modules.
"""
import os
import sys
import time


def check_stale_log(file_path):
    """
    Checks the last modification time of a log file.
    Warns if the file has not been written to in more than 5 minutes.

    Args:
        file_path (str): Path to the log file to check.
    """
    # 5 minutes expressed in seconds.
    # This is the threshold beyond which we consider the log "stale".
    # Making it a named constant (not a magic number) makes the code readable
    # and easy to change without hunting through the logic.
    THRESHOLD_SECONDS = 300

    try:
        # Step 1: Get the file's last modification time.
        #
        # os.path.getmtime() returns the time the file was LAST WRITTEN TO.
        # The return value is a Unix timestamp (float):
        #   - Number of seconds since January 1, 1970 00:00:00 UTC (the Unix epoch)
        #   - Example: 1725000000.0 = some point in August 2024
        #   - Fractions of a second are possible (e.g., 1725000000.456)
        #
        # This reads from the file's INODE METADATA on the filesystem.
        # It does NOT open or read the file contents. Extremely fast.
        #
        # Linux tracks THREE timestamps per file (visible with ls -l --full-time):
        #   atime  (access time)       -> last time file was READ
        #   mtime  (modification time) -> last time file CONTENT was changed  <- we use this
        #   ctime  (change time)       -> last time file METADATA changed (permissions, owner)
        #
        # For log monitoring, mtime is the right choice:
        #   - A running application writes log lines -> mtime updates
        #   - If mtime is old -> application stopped logging -> something is wrong
        mtime = os.path.getmtime(file_path)

        # Step 2: Get the current time as a Unix timestamp.
        # time.time() returns the same format as getmtime() - seconds since epoch.
        # Using both in the same unit lets us subtract directly.
        current_time = time.time()

        # Step 3: Calculate how many seconds ago the file was last modified.
        # Both values are Unix timestamps (seconds since epoch), so subtraction
        # gives elapsed seconds. If file was modified 90 seconds ago: 90.0
        time_diff = current_time - mtime

        # Step 4: Format the time difference for human-readable output.
        # Raw seconds like "324 seconds" are hard to read quickly.
        # We convert to minutes if >= 60 seconds for better UX.
        #   time_diff = 324 seconds
        #   324 // 60 = 5 minutes (integer division, floor)
        #   324 % 60  = 24 seconds remainder (but we don't show this)
        if time_diff >= 60:
            time_str = f"{int(time_diff // 60)} minutes ago"
        else:
            time_str = f"{int(time_diff)} seconds ago"

        # Step 5: Compare against our threshold and print the result.
        if time_diff > THRESHOLD_SECONDS:
            # File has not been written to in more than 5 minutes.
            # This is the "stale" condition - application may have crashed,
            # frozen, or stopped producing output.
            print(f"Log status  : STALE")
            print(f"File        : {file_path}")
            print(f"Last write  : {time_str}")
            print(f"WARNING     : Application may have stopped writing logs!")
        else:
            # File was written recently - application is actively logging.
            print(f"Log status  : HEALTHY")
            print(f"File        : {file_path}")
            print(f"Last write  : {time_str}")

    except FileNotFoundError:
        # The path given does not exist on this system.
        # Could mean: wrong path, log rotation deleted the file, or
        # the application never created the log file (misconfiguration).
        print(f"CRITICAL: File not found: '{file_path}'")
        print("Check the path or verify the application created the log file.")

    except PermissionError:
        # File exists but our user does not have read permission.
        # Fix: run as root/sudo or adjust file permissions (chmod).
        print(f"CRITICAL: Permission denied: '{file_path}'")
        print("Try running with sudo, or check file permissions with: ls -l")


if __name__ == "__main__":
    # Validate command-line arguments.
    # sys.argv[0] = script name
    # sys.argv[1] = log file path (required)
    if len(sys.argv) != 2:
        print("Usage: python3 stale_log_checker.py <path_to_log_file>")
        print("Example: python3 stale_log_checker.py /var/log/myapp/app.log")
        sys.exit(1)

    log_file = sys.argv[1]
    check_stale_log(log_file)
