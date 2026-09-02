#!/usr/bin/env python3
"""
Script 09 - TCP Port Reachability Checker
Checks whether a given TCP port on a host is OPEN or CLOSED.
No third-party libraries - uses Python built-in socket module.
Host and port are passed as command-line arguments.
"""
import socket
import sys


def check_tcp_port(host, port):
    """
    Attempts a TCP connection to (host, port).
    Prints OPEN if connection succeeds, CLOSED otherwise.
    """
    # Step 1: Create a TCP socket object.
    #
    # socket.socket() takes two arguments:
    #   AF_INET      -> Address Family INET = IPv4 (use AF_INET6 for IPv6)
    #   SOCK_STREAM  -> Socket type STREAM = TCP (use SOCK_DGRAM for UDP)
    #
    # TCP (SOCK_STREAM) is connection-oriented:
    #   - Guarantees delivery, ordering, and error-checking
    #   - Requires a 3-way handshake (SYN -> SYN-ACK -> ACK)
    #   - This handshake is EXACTLY what we use to test if a port is open
    #
    # UDP (SOCK_DGRAM) is connectionless - no handshake, fire-and-forget.
    # You cannot use UDP to "test" a port the same way. TCP is the right choice.
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Step 2: Set a timeout of 3 seconds.
    #
    # Without this, the OS will wait up to ~2 minutes for a response
    # before giving up. This is called the system default TCP timeout.
    # In a health check script, waiting 2 minutes per port is unacceptable.
    #
    # s.settimeout(3.0) means:
    #   "If the connect() call does not complete within 3 seconds, raise socket.timeout"
    #
    # 3 seconds is a reasonable SRE default:
    #   - Too short (< 1s): Can cause false CLOSED on slow/loaded networks
    #   - Too long (> 10s): Makes the script slow when checking many hosts
    s.settimeout(3.0)

    try:
        # Step 3: Attempt a TCP connection.
        #
        # s.connect((host, port)) triggers the TCP 3-way handshake:
        #
        #   Client (us)          Server (them)
        #   ----------           -------------
        #   SYN          ->      (port is OPEN: server receives SYN)
        #                <-      SYN-ACK
        #   ACK          ->
        #   CONNECTION ESTABLISHED -> port is OPEN
        #
        # If the port is CLOSED, the server's OS immediately sends back:
        #   RST (Reset) packet -> Python raises ConnectionRefusedError instantly
        #
        # If the host is unreachable (firewall, wrong IP), we get:
        #   No response at all -> after 3 seconds: socket.timeout
        #
        # Note: connect() takes a TUPLE (host, port), not two separate args.
        s.connect((host, port))

        # If we reach this line, the handshake succeeded -> port is OPEN
        print(f"{host}:{port} -> OPEN")

    except socket.timeout:
        # The connect() call did not complete within 3 seconds.
        # This usually means:
        #   - A firewall is silently dropping our SYN packets (no RST, no reply)
        #   - The host is unreachable (wrong IP, host is down)
        #   - The network is congested
        # From our perspective: port is NOT reachable -> CLOSED
        print(f"{host}:{port} -> CLOSED (timeout - no response in 3s)")

    except ConnectionRefusedError:
        # The server OS instantly sent back a TCP RST (Reset) packet.
        # This means the host is reachable but NOTHING is listening on this port.
        # Very fast response - no waiting for timeout.
        # Common cause: service is down, wrong port number.
        print(f"{host}:{port} -> CLOSED (connection refused - nothing listening)")

    except OSError as e:
        # Catch-all for other network-level errors:
        #   - Host unreachable (EHOSTUNREACH) - routing failure
        #   - Network unreachable (ENETUNREACH) - no route to host
        #   - DNS resolution failure (socket.gaierror - subclass of OSError)
        #     e.g., hostname "myapp.internal" does not resolve
        print(f"{host}:{port} -> CLOSED (error: {e})")

    finally:
        # Step 5: ALWAYS close the socket.
        #
        # "finally" runs regardless of whether try succeeded or an exception occurred.
        # This is critical because:
        #   - Open sockets consume OS file descriptors (fd)
        #   - Linux has a limit (ulimit -n, typically 1024-65535)
        #   - A script checking 1000 ports without closing sockets = fd leak = crash
        # s.close() sends TCP FIN and releases the fd immediately.
        s.close()


if __name__ == "__main__":
    # sys.argv is the list of command-line arguments.
    # sys.argv[0] = script name ("portcheck.py")
    # sys.argv[1] = host (e.g., "google.com")
    # sys.argv[2] = port (e.g., "80")
    # len(sys.argv) != 3 means wrong number of arguments given.
    if len(sys.argv) != 3:
        print("Usage: python3 tcp_port_checker.py <host> <port>")
        print("Example: python3 tcp_port_checker.py google.com 443")
        sys.exit(1)

    host_arg = sys.argv[1]

    # Port must be an integer. sys.argv gives strings, so we convert.
    # Valid port range: 1-65535 (0 is reserved, >65535 is invalid)
    port_arg = int(sys.argv[2])

    check_tcp_port(host_arg, port_arg)
