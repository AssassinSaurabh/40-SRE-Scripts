#!/usr/bin/env python3
"""
Script 11 - Suspicious IP Detector (Brute-Force Login Detector)
Scans an authentication log file and finds IP addresses with
more than N failed login attempts (default: 5).
No third-party libraries - pure Python built-ins only.
"""
import sys


def detect_suspicious_ips(filepath, threshold=5):
    """
    Reads an auth log file, counts failed login attempts per IP,
    and prints IPs that exceed the threshold.

    Args:
        filepath  (str): Path to the authentication log file.
        threshold (int): Number of failures above which an IP is flagged.
                         Default is 5.
    """
    # ip_counts is a dictionary that maps each IP address to its failure count.
    # Structure: { "192.168.1.10": 3, "10.0.0.5": 7, ... }
    # We start with an empty dict and build it as we scan the file.
    ip_counts = {}

    try:
        # Open the log file using a context manager.
        # "r" = read-only mode (text, not binary).
        # "with" ensures the file is closed automatically when the block ends,
        # even if an exception is raised. No file handle leaks.
        with open(filepath, "r") as file:

            # Iterate line by line.
            # We do NOT use file.read() or file.readlines() because auth logs
            # on busy servers can be several hundred MB.
            # Line-by-line iteration keeps RAM usage constant regardless of file size -
            # only one line lives in memory at any moment.
            for line in file:

                # FILTER: only process lines that contain "Failed login from".
                # We skip all other lines (INFO, WARNING, successful logins, etc.)
                # without any processing. This is fast because Python's "in"
                # operator on strings is O(len(line)) - very quick substring search.
                #
                # Example log line we are looking for:
                # "Failed login from 192.168.1.10"
                #
                # Lines we skip (no "Failed login from"):
                # "Accepted password for root from 10.0.0.1 port 22"
                # "session opened for user ubuntu"
                if "Failed login from" in line:

                    # PARSE: Extract the IP address from the matching line.
                    #
                    # How it works, step by step:
                    #
                    # 1. line.strip()
                    #    Removes any leading/trailing whitespace and the trailing 
.
                    #    "Failed login from 192.168.1.10
"
                    #    -> "Failed login from 192.168.1.10"
                    #
                    # 2. .split()
                    #    Splits the string on ANY whitespace (spaces, tabs).
                    #    No argument to split() means split on ALL whitespace.
                    #    "Failed login from 192.168.1.10"
                    #    -> ["Failed", "login", "from", "192.168.1.10"]
                    #
                    # 3. [-1]
                    #    Negative indexing: -1 is the LAST element of a list.
                    #    ["Failed", "login", "from", "192.168.1.10"][-1]
                    #    -> "192.168.1.10"
                    #
                    # This assumes the IP is always the last word on the line.
                    # That is the standard format for this simplified log format.
                    ip = line.strip().split()[-1]

                    # COUNT: Update the dictionary.
                    #
                    # dict.get(key, default) returns the value for "key" if it exists,
                    # or "default" if the key is not in the dictionary yet.
                    #
                    # First time we see "192.168.1.10":
                    #   ip_counts.get("192.168.1.10", 0) -> 0 (not in dict yet)
                    #   ip_counts["192.168.1.10"] = 0 + 1 = 1
                    #
                    # Second time we see "192.168.1.10":
                    #   ip_counts.get("192.168.1.10", 0) -> 1 (already stored)
                    #   ip_counts["192.168.1.10"] = 1 + 1 = 2
                    #
                    # This is the standard Pythonic way to count items.
                    # Alternative using collections.Counter would also work,
                    # but .get() shows you understand dict fundamentals.
                    ip_counts[ip] = ip_counts.get(ip, 0) + 1

        # REPORT: Print the results.
        print("
Suspicious IPs (Possible Brute-Force Attacks):")
        print("-" * 45)

        # Flag to track whether we found any suspicious IPs.
        # We cannot know before iterating whether any IP exceeded the threshold.
        found_any = False

        # Sort by count descending so the most aggressive attacker appears first.
        # sorted() returns a new sorted list. key=lambda x: x[1] sorts by the
        # value (count), not the key (IP). reverse=True = highest count first.
        for ip, count in sorted(ip_counts.items(), key=lambda x: x[1], reverse=True):
            if count > threshold:
                print(f"  {ip:<18} -> {count} failed attempts  [SUSPICIOUS]")
                found_any = True

        if not found_any:
            print("  No suspicious IPs found. All within threshold.")

        print(f"
Total unique IPs seen in log: {len(ip_counts)}")
        print(f"Threshold used: > {threshold} failed attempts")

    except FileNotFoundError:
        # The path does not exist on the filesystem.
        print(f"CRITICAL: Log file not found: '{filepath}'")

    except PermissionError:
        # File exists but we lack read access.
        print(f"CRITICAL: Permission denied: '{filepath}'")
        print("Try running with sudo, or check: ls -l {filepath}")

    except Exception as e:
        # Catch-all: unexpected errors (encoding issues, disk failure, etc.)
        print(f"CRITICAL: Unexpected error while processing log: {e}")


if __name__ == "__main__":
    # Validate command-line arguments.
    # sys.argv[0] = script name
    # sys.argv[1] = log file path (required)
    if len(sys.argv) != 2:
        print("Usage  : python3 suspicious_ip_detector.py <path_to_log_file>")
        print("Example: python3 suspicious_ip_detector.py /var/log/auth.log")
        sys.exit(1)

    log_file_path = sys.argv[1]
    detect_suspicious_ips(log_file_path)
