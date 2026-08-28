#!/usr/bin/env python3
"""
Script 06 - Log File Error Counter with Alerting
Scans an application log file, counts lines containing ERROR,
and alerts if the count exceeds a configurable threshold.
"""
import os


def check_error_spike(log_file_path, threshold=10):
    """
    Reads a log file line by line, counts occurrences of ERROR,
    and raises an alert if the count exceeds the threshold.

    Args:
        log_file_path (str): Path to the application log file.
        threshold (int): Number of errors above which an alert is raised.
    """
    error_count = 0

    try:
        # "with open" ensures the file is properly closed after reading,
        # even if an exception occurs mid-read.
        # This is memory-safe for very large log files because we iterate
        # line by line - the whole file is never loaded into RAM at once.
        with open(log_file_path, "r") as log_file:
            for line in log_file:
                # Case-sensitive check: "ERROR" must appear anywhere in the line.
                # This catches patterns like:
                #   2024-01-15 10:30:00 ERROR Database connection failed
                #   [ERROR] Disk quota exceeded
                #   ERROR: Service timeout after 30s
                if "ERROR" in line:
                    error_count += 1

        print(f"Scan complete. ERROR count: {error_count} / threshold: {threshold}")

        if error_count > threshold:
            print(f"ALERT: High error rate detected! {error_count} errors found (threshold={threshold})")
        else:
            print(f"OK: Error count is within acceptable limits.")

    except FileNotFoundError:
        # Log file does not exist at the given path
        print(f"CRITICAL: Log file not found: {log_file_path}")
    except PermissionError:
        # Script lacks read permissions on the file
        print(f"CRITICAL: Permission denied reading: {log_file_path}")
    except Exception as e:
        # Catch-all for any other unexpected error
        print(f"CRITICAL: Unexpected error: {e}")


if __name__ == "__main__":
    check_error_spike("app.log", threshold=10)
