#!/usr/bin/env python3
"""
Script 12 - HTTP Access Log Status Code Counter
Reads an HTTP access log (Apache/Nginx Combined Log Format),
counts how many requests returned each HTTP status code,
and prints a clean categorised report.
No third-party libraries - pure Python built-ins only.
"""
import sys


# ---------------------------------------------------------------------------
# WHAT DOES AN HTTP ACCESS LOG LINE LOOK LIKE?
# ---------------------------------------------------------------------------
# Apache and Nginx both use the "Combined Log Format" by default.
# Every request is written as one line. Example:
#
#  192.168.1.1 - frank [04/Sep/2024:22:01:15 +0530] "GET /index.html HTTP/1.1" 200 1524 "-" "Mozilla/5.0"
#  |           | |     |                            | |                        | |   |    |   |
#  |           | |     |                            | |                        | |   |    |   +-- User-Agent
#  |           | |     |                            | |                        | |   |    +----- Referrer
#  |           | |     |                            | |                        | |   +---------- Response size (bytes)
#  |           | |     |                            | |                        | +-------------- HTTP Status Code  <- WE WANT THIS
#  |           | |     |                            | +-------------------------------- Request line (method path protocol)
#  |           | |     +---------------------------------------------------- Timestamp
#  |           | +---------------------------------------------------------- Auth user (- = anonymous)
#  |           +------------------------------------------------------------ Ident (- = not available)
#  +------------------------------------------------------------------------ Client IP address
#
# The status code is always the FIRST field AFTER the closing quote of the request line.
# ---------------------------------------------------------------------------


def get_status_category(code_str):
    """
    Returns a human-readable category for an HTTP status code.
    This makes the report immediately useful without memorising codes.
    """
    try:
        code = int(code_str)
        if 100 <= code < 200:
            return "1xx Informational"
        elif 200 <= code < 300:
            return "2xx Success        "
        elif 300 <= code < 400:
            return "3xx Redirection    "
        elif 400 <= code < 500:
            return "4xx Client Error   "
        elif 500 <= code < 600:
            return "5xx Server Error   "
        else:
            return "Unknown            "
    except ValueError:
        # Code is not a valid integer (malformed line survived filtering)
        return "Unknown            "


def count_status_codes(filepath):
    """
    Reads an HTTP access log file line by line,
    extracts the HTTP status code from each line,
    counts occurrences per code, and prints a formatted report.

    Args:
        filepath (str): Path to the HTTP access log file.
    """
    # Dictionary to store { "200": 1523, "404": 87, "500": 3, ... }
    status_counts = {}

    # Track lines we could not parse (for transparency in output)
    skipped_lines = 0
    total_lines = 0

    try:
        with open(filepath, "r") as f:
            for line in f:
                total_lines += 1

                # Skip blank lines (some log rotations leave empty lines)
                line = line.strip()
                if not line:
                    skipped_lines += 1
                    continue

                try:
                    # -------------------------------------------------------
                    # THE PARSING TRICK: Split on double-quote character "
                    # -------------------------------------------------------
                    # The Combined Log Format always has the request wrapped in
                    # double quotes: "GET /index.html HTTP/1.1"
                    #
                    # When we split the whole line on '"', we get 3 sections:
                    #
                    # line = '1.2.3.4 - - [date] "GET /path HTTP/1.1" 200 512 "-" "Mozilla"'
                    #
                    # parts[0] = '1.2.3.4 - - [date] '        <- before opening "
                    # parts[1] = 'GET /path HTTP/1.1'          <- the request (inside quotes)
                    # parts[2] = ' 200 512 "-" "Mozilla"'      <- after closing "  <- WE WANT THIS
                    #
                    # If there are more quoted fields (referrer, user-agent),
                    # split() still gives us parts[2] as the status code section.
                    #
                    # parts[2].strip() removes the leading space -> "200 512 ..."
                    # .split()         splits on whitespace     -> ["200", "512", ...]
                    # [0]              takes the first element  -> "200"
                    #
                    # This is robust: it works whether or not referrer/UA fields exist.
                    # -------------------------------------------------------
                    parts = line.split('"')
                    status_code = parts[2].strip().split()[0]

                    # Basic sanity check: status code should be a 3-digit number.
                    # This guards against malformed lines that survived the split.
                    if not status_code.isdigit() or len(status_code) != 3:
                        skipped_lines += 1
                        continue

                    # Increment count for this status code
                    status_counts[status_code] = status_counts.get(status_code, 0) + 1

                except (IndexError, ValueError):
                    # Line did not have the expected structure.
                    # Possible causes:
                    #   - Custom log format (not Combined Log Format)
                    #   - Corrupted / truncated log line
                    #   - Log file header or comment line
                    # We skip and continue - one bad line should not crash the scan.
                    skipped_lines += 1

        # -------------------------------------------------------------------
        # PRINT THE REPORT
        # -------------------------------------------------------------------
        total_requests = sum(status_counts.values())

        print(f"\nHTTP Status Code Report")
        print(f"File: {filepath}")
        print("=" * 55)
        print(f"  {'Code':<8} {'Count':<10} {'%':>6}   Category")
        print("-" * 55)

        # Sort by status code numerically (200 before 301 before 404 before 500)
        # int(code) converts string "404" to integer 404 for correct numeric sort.
        # Without int(), "404" > "200" lexicographically but "99" > "404" would break.
        for code in sorted(status_counts.keys(), key=int):
            count = status_counts[code]
            percentage = (count / total_requests * 100) if total_requests > 0 else 0
            category = get_status_category(code)
            print(f"  {code:<8} {count:<10} {percentage:>5.1f}%  {category}")

        print("=" * 55)
        print(f"  Total requests  : {total_requests}")
        print(f"  Unique codes    : {len(status_counts)}")
        print(f"  Skipped lines   : {skipped_lines} (malformed / blank)")

    except FileNotFoundError:
        print(f"CRITICAL: Log file not found: '{filepath}'")
        print("Check the path and try again.")

    except PermissionError:
        print(f"CRITICAL: Permission denied: '{filepath}'")
        print("Try running with sudo, or check: ls -l")

    except Exception as e:
        print(f"CRITICAL: Unexpected error while processing log: {e}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage  : python3 http_status_counter.py <path_to_access_log>")
        print("Example: python3 http_status_counter.py /var/log/nginx/access.log")
        sys.exit(1)

    count_status_codes(sys.argv[1])
