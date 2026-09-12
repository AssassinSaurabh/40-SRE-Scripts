#!/usr/bin/env python3
"""
Script 16 - Configuration File Differ
Compares two configuration files and clearly reports:
  - Lines only in File A (missing from B)
  - Lines only in File B (missing from A)
  - A unified diff showing exact changed lines with context
Uses Python's built-in difflib module. No third-party libraries needed.
"""
import sys
import difflib


def read_file(filepath):
    """
    Reads a file and returns its lines as a list.
    Raises SystemExit on FileNotFoundError or PermissionError with a clear message.
    """
    try:
        # Open in read mode. Python's open() uses the system locale encoding
        # (usually UTF-8 on modern Linux). 'errors="replace"' would handle
        # unusual binary config files, but most configs are plain ASCII/UTF-8.
        with open(filepath, 'r') as f:
            # readlines() returns a list of strings, each string is one line
            # INCLUDING the trailing \n newline character.
            # Example: ["host = db.prod.internal\n", "port = 5432\n"]
            # We keep \n because difflib uses it for accurate line comparison.
            return f.readlines()

    except FileNotFoundError:
        print(f"Error: File not found: '{filepath}'")
        sys.exit(1)

    except PermissionError:
        print(f"Error: Permission denied: '{filepath}'")
        print("Try running with sudo.")
        sys.exit(1)


def compare_configs(path_a, path_b):
    """
    Reads two config files, diffs them with difflib, and prints a structured report.

    Args:
        path_a (str): Path to the first config file ("source of truth" / server A).
        path_b (str): Path to the second config file (server B to compare against).
    """
    lines_a = read_file(path_a)
    lines_b = read_file(path_b)

    # -------------------------------------------------------------------
    # FAST EQUALITY CHECK
    # -------------------------------------------------------------------
    # Before doing any diff work, check if files are identical.
    # list == list in Python compares element by element.
    # If both lists have the same lines in the same order, they are equal.
    # This short-circuits the entire diff computation for the happy path.
    # -------------------------------------------------------------------
    if lines_a == lines_b:
        print("Result  : FILES ARE IDENTICAL")
        print(f"File A  : {path_a}")
        print(f"File B  : {path_b}")
        print(f"Lines   : {len(lines_a)}")
        return

    # -------------------------------------------------------------------
    # GENERATE THE UNIFIED DIFF
    # -------------------------------------------------------------------
    # difflib.unified_diff() is Python's built-in diff engine.
    # It produces output in the same format as the Linux 'diff -u' command.
    #
    # Parameters:
    #   a          : list of lines from file A (with \n)
    #   b          : list of lines from file B (with \n)
    #   fromfile   : label shown in the --- header line (file A name)
    #   tofile     : label shown in the +++ header line (file B name)
    #   lineterm   : string appended to each output line
    #                ''  = empty string -> don't add extra newlines
    #                (lines already have \n from readlines())
    #   n          : number of context lines around each change (default 3)
    #                Context lines help you understand WHERE the change is.
    #
    # Returns: a generator (lazy) - we convert to list to allow multiple passes.
    # -------------------------------------------------------------------
    diff = list(difflib.unified_diff(
        lines_a,
        lines_b,
        fromfile=f"A: {path_a}",
        tofile=f"B: {path_b}",
        lineterm=''           # lines already have \n, don't add more
    ))

    # -------------------------------------------------------------------
    # CATEGORISE CHANGES: count added and removed lines
    # -------------------------------------------------------------------
    # In unified diff format, each non-header line starts with:
    #   '-'  : line exists in A but NOT in B (removed / missing from B)
    #   '+'  : line exists in B but NOT in A (added / missing from A)
    #   ' '  : unchanged context line (present in both)
    #
    # The first two lines are headers (--- and +++), not actual changes:
    #   --- A: server1.conf
    #   +++ B: server2.conf
    # We must skip them using startswith('---') and startswith('+++ ').
    # -------------------------------------------------------------------
    only_in_a = [l for l in diff if l.startswith('-') and not l.startswith('---')]
    only_in_b = [l for l in diff if l.startswith('+') and not l.startswith('+++ ')]

    # -------------------------------------------------------------------
    # PRINT THE SUMMARY REPORT
    # -------------------------------------------------------------------
    print("=" * 60)
    print("CONFIG DIFF REPORT")
    print("=" * 60)
    print(f"File A  : {path_a}  ({len(lines_a)} lines)")
    print(f"File B  : {path_b}  ({len(lines_b)} lines)")
    print("-" * 60)
    print(f"Lines only in A (missing from B) : {len(only_in_a)}")
    print(f"Lines only in B (missing from A) : {len(only_in_b)}")
    print("=" * 60)

    # Print the full unified diff
    # Each line is printed as-is. The \n is already included in the line string.
    # The diff format uses:
    #   @@ -start,count +start,count @@   <- hunk header showing line numbers
    #   -line                              <- line from A (red in terminals)
    #   +line                              <- line from B (green in terminals)
    #    line                              <- unchanged context line
    print("\nDETAILED DIFF (unified format):")
    print("-" * 60)
    for line in diff:
        # Strip trailing \n for cleaner print() output
        # (print() adds its own \n by default)
        print(line.rstrip('\n'))

    print("-" * 60)
    print(f"\nSummary: {len(only_in_a)} line(s) to add to B, {len(only_in_b)} line(s) to remove from B")
    print("         to make both files identical.")


def main():
    if len(sys.argv) != 3:
        print("Usage  : python3 config_diff.py <file_a> <file_b>")
        print("Example: python3 config_diff.py server1.conf server2.conf")
        sys.exit(1)

    path_a = sys.argv[1]
    path_b = sys.argv[2]

    compare_configs(path_a, path_b)


if __name__ == "__main__":
    main()
