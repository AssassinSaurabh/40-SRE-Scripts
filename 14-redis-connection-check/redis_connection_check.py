#!/usr/bin/env python3
"""
Script 14 - Redis Connection Health Checker
Checks whether Redis is reachable on a given host and port.
Goes beyond a TCP check by sending a real Redis PING command
and verifying the PONG response via the RESP protocol.
Measures round-trip latency in milliseconds.
No third-party libraries (no redis-py) - pure Python socket only.
"""
import socket
import sys
import time


# Redis defaults — well-known port registered by Redis / Salvatore Sanfilippo
REDIS_DEFAULT_HOST = "localhost"
REDIS_DEFAULT_PORT = 6379


def check_redis(host=REDIS_DEFAULT_HOST, port=REDIS_DEFAULT_PORT, timeout_sec=2):
    """
    Connects to Redis, sends a PING command via the RESP protocol,
    reads the PONG response, and reports latency.

    Why send a PING and not just check TCP?
    A TCP connection to port 6379 only confirms SOMETHING is listening.
    It could be a proxy, a different service, or Redis mid-restart.
    Sending a PING and verifying the PONG response confirms Redis itself
    is alive and processing commands — end to end.
    """
    # Record the start time BEFORE connecting so latency includes
    # the full round-trip: connect + send PING + receive PONG.
    # This is the real-world latency your application experiences.
    start_time = time.time()

    try:
        # Use "with socket.socket(...) as s" — a context manager.
        # This guarantees s.close() is called when the block exits,
        # even if an exception is raised inside.
        # This is the same guarantee "with open(...)" gives for files.
        # No file descriptor leaks.
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:

            # Set connection timeout.
            # Without this, the OS may wait up to 75-127 seconds before
            # giving up on an unreachable host. 2 seconds is a reasonable
            # SRE threshold for a local or LAN Redis instance.
            s.settimeout(timeout_sec)

            # Step 1: TCP connect (3-way handshake)
            # If Redis is not running -> ConnectionRefusedError (instant RST)
            # If firewall blocks port -> socket.timeout (waits 2s then fails)
            # If DNS fails           -> OSError (Name not known)
            s.connect((host, port))

            # -----------------------------------------------------------
            # Step 2: Send PING in the RESP protocol format.
            #
            # RESP = REdis Serialization Protocol
            # Redis uses RESP for ALL communication (commands and responses).
            # It is a simple, text-based, line-oriented protocol.
            #
            # RESP command format (for a command with N arguments):
            #   *N
          <- number of arguments
            #   $<len>
      <- length of next argument in bytes
            #   <argument>
  <- the argument itself
            #
            # PING has 1 argument ("PING" itself):
            #   *1
          <- 1 argument total
            #   $4
          <- "PING" is 4 bytes long
            #   PING
        <- the command name
            #
            # 
 is the CRLF line terminator that RESP requires.
            # Redis ignores case, so PING, ping, Ping all work,
            # but the byte count ($4) must match exactly.
            # -----------------------------------------------------------
            ping_command = b"*1
$4
PING
"
            s.sendall(ping_command)

            # Step 3: Receive the PONG response.
            # recv(128) reads up to 128 bytes.
            # The PONG response is tiny: "+PONG
" = 7 bytes.
            # 128 bytes is more than enough and still negligible overhead.
            response = s.recv(128)

        # -------------------------------------------------------------------
        # Step 4: Calculate latency.
        # time.time() returns seconds as a float.
        # (time.time() - start_time) = seconds elapsed.
        # Multiply by 1000 to convert to milliseconds.
        # :.1f formats to 1 decimal place (e.g. 0.8 ms, 12.3 ms).
        # -------------------------------------------------------------------
        latency_ms = (time.time() - start_time) * 1000

        # -------------------------------------------------------------------
        # Step 5: Validate the PONG response.
        #
        # RESP simple string response format:  +<message>

        # A successful PONG response is:       +PONG

        #
        # response.startswith(b"+PONG") is True only for a valid PONG.
        # We use startswith instead of == because some Redis versions
        # may include extra whitespace or line endings.
        # -------------------------------------------------------------------
        if response.startswith(b"+PONG"):
            print("Redis  : UP")
            print(f"Host   : {host}:{port}")
            print(f"Ping   : PONG received (Redis is accepting commands)")
            print(f"RTT    : {latency_ms:.1f} ms")
        else:
            # Connected and something responded, but it was not a PONG.
            # Could be: Redis with AUTH required, a proxy that answered, or
            # a different service running on port 6379.
            print("Redis  : UNCERTAIN")
            print(f"Host   : {host}:{port}")
            print(f"RTT    : {latency_ms:.1f} ms")
            print(f"Note   : Unexpected response: {response[:50]}")
            print("        If Redis requires a password, AUTH is needed.")

    except ConnectionRefusedError:
        # Server OS sent TCP RST — nothing listening on port 6379.
        # Redis service is stopped or never started.
        print("Redis  : DOWN")
        print(f"Host   : {host}:{port}")
        print("Reason : Connection refused — Redis is not running on this port.")
        print("Fix    : sudo systemctl start redis")

    except socket.timeout:
        # No response within timeout_sec seconds.
        # Firewall is silently dropping packets, or host is unreachable.
        print("Redis  : DOWN")
        print(f"Host   : {host}:{port}")
        print(f"Reason : Timeout — no response in {timeout_sec}s.")
        print("Check  : Is a firewall blocking port 6379?")
        print("         sudo ufw status | grep 6379")

    except OSError as e:
        # DNS failure, no route to host, network interface down, etc.
        print("Redis  : DOWN")
        print(f"Host   : {host}:{port}")
        print(f"Reason : {e}")


if __name__ == "__main__":
    # Flexible argument handling with sensible defaults.
    # No args  -> check localhost:6379 (most common case: local Redis)
    # 1 arg    -> check <host>:6379
    # 2 args   -> check <host>:<port>
    host = sys.argv[1] if len(sys.argv) > 1 else REDIS_DEFAULT_HOST
    port = int(sys.argv[2]) if len(sys.argv) > 2 else REDIS_DEFAULT_PORT

    print(f"Checking Redis at {host}:{port} ...")
    print("-" * 40)
    check_redis(host, port)
