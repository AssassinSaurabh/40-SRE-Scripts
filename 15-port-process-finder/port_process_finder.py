#!/usr/bin/env python3
"""
Script 15 - Port Process Finder
Identifies which process is currently listening on a given TCP port.
Uses the Linux 'ss' (socket statistics) utility via subprocess.
Parses the output with a targeted regular expression to extract
the process name and PID.
No third-party libraries - uses subprocess, sys, re (all built-in).
"""
import subprocess
import sys
import re


def find_process_by_port(port):
    """
    Runs 'ss -lptn sport = :<port>' and parses the output
    to extract the process name and PID listening on that port.

    Args:
        port (str): The port number as a string (e.g. "8080").

    Returns:
        tuple: (pid, process_name) as strings, or (None, None) if not found.
    """
    try:
        # -------------------------------------------------------------------
        # THE COMMAND: ss -lptn 'sport = :<port>'
        # -------------------------------------------------------------------
        # 'ss' is the modern replacement for 'netstat' on Linux.
        # It queries the kernel's socket table directly - faster and more
        # accurate than netstat (which reads /proc/net/tcp by text parsing).
        #
        # Flag breakdown:
        #   -l  (--listening)  : Show only LISTENING sockets (not established)
        #   -p  (--processes)  : Show the process attached to each socket
        #   -t  (--tcp)        : Show TCP sockets only (not UDP, not Unix)
        #   -n  (--numeric)    : Show port numbers as numbers (not names)
        #                        Without -n, port 80 shows as "http", 443 as "https"
        #                        With -n, port 80 shows as 80. We need numbers to match.
        #
        # 'sport = :<port>' is a FILTER expression built into ss:
        #   sport = source port = the port the server is LISTENING on
        #   :<port> = colon + port number (ss syntax)
        #   This filters output to ONLY the specified port instead of all ports.
        # -------------------------------------------------------------------
        cmd = ['ss', '-lptn', f'sport = :{port}']

        # subprocess.check_output() runs the command and returns its stdout.
        # If the command exits with a non-zero return code, it raises
        # subprocess.CalledProcessError. We catch that below.
        #
        # stderr=subprocess.DEVNULL: suppress any error output from ss itself
        # (e.g. permission warnings) so only our print() calls appear.
        #
        # text=True: return stdout as a str instead of bytes.
        # Without text=True, we get b"LISTEN 0..." and need .decode().
        # With text=True, we get "LISTEN 0..." directly.
        result = subprocess.check_output(
            cmd,
            stderr=subprocess.DEVNULL,
            text=True
        )

        # -------------------------------------------------------------------
        # WHAT DOES 'ss' OUTPUT LOOK LIKE?
        # -------------------------------------------------------------------
        # The header line (always present):
        #   Netid  State   Recv-Q  Send-Q  Local Address:Port  Peer Address:Port  Process
        #
        # An actual listening socket line:
        #   tcp    LISTEN  0       128     0.0.0.0:8080        0.0.0.0:*          users:(("java",pid=1842,fd=10))
        #   |      |       |       |       |       |           |                  |
        #   |      |       |       |       |       |           |                  +-- Process info
        #   |      |       |       |       |       |           +-- Peer (always * for listeners)
        #   |      |       |       |       |       +-- Listening port number
        #   |      |       |       |       +-- Local IP (0.0.0.0 = all interfaces)
        #   |      |       |       +-- Send queue length
        #   |      |       +-- Receive queue length
        #   |      +-- Socket state (LISTEN for listening sockets)
        #   +-- Protocol (tcp)
        #
        # The "users:(("java",pid=1842,fd=10))" section is only present
        # when ss can see the owning process (same UID or run as root).
        # -------------------------------------------------------------------

        # Split the output into individual lines and check each one
        for line in result.splitlines():

            # ---------------------------------------------------------------
            # THE FILTER: Two cheap string checks before the expensive regex
            # ---------------------------------------------------------------
            # WHY CHECK BOTH CONDITIONS before running the regex?
            #
            # Condition 1: f":{port}" in line
            #   We search for ":8080" not just "8080" because:
            #   - "8080" alone might accidentally match a PID of 8080
            #   - "8080" might match a file descriptor number fd=8080
            #   - ":8080" is specific to the port column in ss output
            #   The colon pins us to the port position in the line.
            #
            # Condition 2: "users:(" in line
            #   ss only includes "users:(..." when it can see the process.
            #   If the process is owned by root and we run without sudo,
            #   the users section is ABSENT or shows as empty.
            #   No point running the regex on a line we know can't match.
            #
            # The "and" short-circuits: if the first condition is False,
            # Python never evaluates the second one. Fast and efficient.
            # ---------------------------------------------------------------
            if f":{port}" in line and "users:(" in line:

                # -----------------------------------------------------------
                # THE REGEX: Extract process name and PID
                # -----------------------------------------------------------
                # Target string we are matching against:
                #   users:(("java",pid=1842,fd=10))
                #
                # The regex pattern: r'users:\(\("([^"]+)",pid=(\d+)'
                #
                # Let's dissect it token by token:
                #
                #   users:      - literal text "users:"
                #
                #   \(\(        - two literal opening parentheses (
                #                 In regex, ( means "start a capture group"
                #                 To match a LITERAL ( we must escape it: backslash-(
                #                 Two literal (( in the string -> \\(\\( in regex
                #
                #   "           - literal double-quote character
                #
                #   ([^"]+)     - CAPTURE GROUP 1: the process name
                #                 (  = start capturing
                #                 [^"] = character class: any char EXCEPT "
                #                 +  = one or more of those chars
                #                 )  = stop capturing
                #                 This grabs "java" and stops at the closing "
                #                 [^"]+ is safer than .+ because it won't
                #                 greedily eat past the quote boundary.
                #
                #   ",pid=      - literal text '",pid='
                #
                #   (\d+)       - CAPTURE GROUP 2: the PID
                #                 (  = start capturing
                #                 \d = any digit character (0-9)
                #                 +  = one or more digits
                #                 )  = stop capturing
                #                 This grabs "1842"
                #
                # re.search() scans through the line and returns a Match
                # object on the FIRST occurrence of the pattern, or None.
                # -----------------------------------------------------------
                match = re.search(r'users:\(\("([^"]+)",pid=(\d+)', line)

                if match:
                    # match.group(0) = the entire matched string
                    # match.group(1) = first capture group  = process name
                    # match.group(2) = second capture group = PID
                    #
                    # We return (PID, process_name) in that order because
                    # our caller unpacks as: pid, process = find_process_by_port(...)
                    process_name = match.group(1)  # e.g. "java"
                    pid = match.group(2)            # e.g. "1842"
                    return pid, process_name

        # No matching line found - port may be free, or process is hidden
        return None, None

    except FileNotFoundError:
        # 'ss' binary not found in PATH.
        # ss comes from the 'iproute2' package on Debian/Ubuntu/RHEL.
        # Install with: sudo apt install iproute2 OR sudo yum install iproute
        print("Error: 'ss' utility not found. Install it: sudo apt install iproute2")
        sys.exit(1)

    except subprocess.CalledProcessError:
        # ss exited with a non-zero return code.
        # This can happen with certain kernel versions or invalid filter syntax.
        return None, None


def main():
    if len(sys.argv) != 2:
        print("Usage  : python3 port_process_finder.py <port>")
        print("Example: python3 port_process_finder.py 8080")
        sys.exit(1)

    port = sys.argv[1]

    # Validate that the argument is a numeric string (not a word like "http").
    # str.isdigit() returns True only if ALL characters are digits (0-9).
    # It rejects negative numbers (contain "-"), floats (contain "."),
    # and non-numeric strings.
    if not port.isdigit():
        print(f"Error: '{port}' is not a valid port number. Use a number like 8080.")
        sys.exit(1)

    pid, process = find_process_by_port(port)

    if pid:
        print(f"Port {port} is in use:")
        print(f"  PID     : {pid}")
        print(f"  Process : {process}")
        print(f"
To kill it  : sudo kill {pid}")
        print(f"To force-kill: sudo kill -9 {pid}")
    else:
        print(f"No process found listening on port {port}.")
        print("Note: Run with sudo if the process is owned by root or another user.")
        print("      sudo python3 port_process_finder.py " + port)


if __name__ == "__main__":
    main()
