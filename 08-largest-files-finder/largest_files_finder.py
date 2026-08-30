#!/usr/bin/env python3
"""
Script 08 - Top 5 Largest Files Finder
Recursively scans a directory and finds the 5 largest files.
Helps SREs diagnose disk space issues on production servers.
No third-party libraries needed - uses built-in os module.
"""
import os


def get_top_5_largest_files(directory):
    """
    Recursively walks a directory tree and returns the 5 largest files.
    Returns a list of up to 5 tuples: [(size_in_bytes, filepath), ...]
    Sorted by size descending (largest first).
    """
    file_list = []

    # os.walk() traverses the entire directory tree recursively.
    # Every folder, subfolder, and sub-subfolder - no manual recursion needed.
    #
    # On each iteration it yields a 3-tuple:
    #   root  -> the current folder path being visited (string)
    #   dirs  -> list of subfolder names inside root (we do not use this)
    #   files -> list of filenames (NOT full paths) inside root
    #
    # Example for /var/log:
    #   Iter 1: root="/var/log",       dirs=["apt","nginx"], files=["syslog","auth.log"]
    #   Iter 2: root="/var/log/apt",   dirs=[],              files=["history.log"]
    #   Iter 3: root="/var/log/nginx", dirs=[],              files=["access.log","error.log"]
    for root, dirs, files in os.walk(directory):
        for file in files:

            # os.path.join() builds the full absolute path.
            # "file" is only the filename (e.g. "access.log").
            # We need root + filename to get the usable path.
            # root="/var/log/nginx"  +  file="access.log"
            # -> filepath="/var/log/nginx/access.log"
            filepath = os.path.join(root, file)

            try:
                # SYMLINK CHECK - critical, often missed by beginners.
                # A symlink is a shortcut pointing to another file.
                # Problems if we follow symlinks:
                # 1. Count same file TWICE (symlink + real file both appear in results)
                # 2. /proc or /sys symlinks return garbage/huge sizes
                # 3. Circular symlinks cause infinite loops
                # os.path.islink() returns True if filepath is a symlink -> we skip it.
                if not os.path.islink(filepath):

                    # os.path.getsize() returns file size in BYTES.
                    # Reads from filesystem metadata (inode), NOT file content.
                    # Extremely fast even for 100GB files.
                    file_size = os.path.getsize(filepath)

                    # Store as tuple (size, path).
                    # Size is first so Python can sort tuples by default (first element).
                    file_list.append((file_size, filepath))

            except OSError:
                # OSError covers all real-world failure modes:
                # - PermissionError    : no read access to this file
                # - FileNotFoundError  : file deleted between walk() listing and getsize() call
                # - Stale NFS mount    : network file vanished mid-scan
                # Silently skip - crashing on one bad file ruins the whole scan.
                pass

    # Sort by file_size (x[0]) descending - largest file first.
    # Python sort is stable, O(n log n) - handles millions of files efficiently.
    file_list.sort(key=lambda x: x[0], reverse=True)

    # Slice to return only the top 5
    return file_list[:5]


if __name__ == "__main__":
    target_directory = "/var/log"  # Change this path as needed
    print(f"Scanning: {target_directory}")
    print("Looking for the 5 largest files...
")

    top_5 = get_top_5_largest_files(target_directory)

    if not top_5:
        print("No files found (directory may be empty or unreadable).")
    else:
        print(f"{'Rank':<6} {'Size (MB)':<12} File Path")
        print("-" * 60)
        for rank, (size, path) in enumerate(top_5, start=1):
            size_mb = size / (1024 * 1024)
            print(f"{rank:<6} {size_mb:<12.2f} {path}")
