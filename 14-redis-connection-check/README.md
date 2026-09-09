# 14 - Redis Connection Health Checker

## The Interview Question

> *"Your application is intermittently failing to connect to Redis. Write a small Python script that checks whether Redis is reachable on localhost:6379 and reports the failure clearly."*

---

## What This Script Does

1. Takes **host** and **port** as optional command-line arguments (defaults to `localhost:6379`)
2. Records **start time** before connecting — to measure true round-trip latency
3. Opens a TCP socket using a **context manager** (`with socket.socket(...) as s`)
4. Sends a real **Redis PING command** encoded in the **RESP protocol**
5. Reads and validates the **`+PONG`** response
6. Prints `UP` with latency in ms, or `DOWN` with the root cause and a fix command

> **The upgrade over a plain TCP check:** We send an actual Redis command (`PING`) and verify the response (`+PONG`). This confirms Redis is processing commands — not just that port 6379 is open.

---

## The Solution

```python
#!/usr/bin/env python3
import socket
import sys
import time

REDIS_DEFAULT_HOST = "localhost"
REDIS_DEFAULT_PORT = 6379


def check_redis(host=REDIS_DEFAULT_HOST, port=REDIS_DEFAULT_PORT, timeout_sec=2):
    start_time = time.time()

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout_sec)
            s.connect((host, port))
            s.sendall(b"*1\r\n$4\r\nPING\r\n")
            response = s.recv(128)

        latency_ms = (time.time() - start_time) * 1000

        if response.startswith(b"+PONG"):
            print("Redis  : UP")
            print(f"Host   : {host}:{port}")
            print(f"Ping   : PONG received")
            print(f"RTT    : {latency_ms:.1f} ms")
        else:
            print("Redis  : UNCERTAIN")
            print(f"Host   : {host}:{port}")
            print(f"Note   : Unexpected response: {response[:50]}")

    except ConnectionRefusedError:
        print("Redis  : DOWN")
        print(f"Host   : {host}:{port}")
        print("Reason : Connection refused — Redis is not running.")
        print("Fix    : sudo systemctl start redis")

    except socket.timeout:
        print("Redis  : DOWN")
        print(f"Host   : {host}:{port}")
        print(f"Reason : Timeout — no response in {timeout_sec}s.")

    except OSError as e:
        print("Redis  : DOWN")
        print(f"Host   : {host}:{port}")
        print(f"Reason : {e}")


if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else REDIS_DEFAULT_HOST
    port = int(sys.argv[2]) if len(sys.argv) > 2 else REDIS_DEFAULT_PORT
    print(f"Checking Redis at {host}:{port} ...")
    print("-" * 40)
    check_redis(host, port)
```

---

## How We Achieved This — Every Decision Explained

### Why Not Just Check TCP Port 6379?

The basic version just does:
```python
s.connect((host, 6379))
print("UP")
```

This is **misleading** in two real production scenarios:

```
Scenario 1: Redis is starting up
  TCP connect  : succeeds (kernel bound the port)
  Redis ready? : NO (still loading dataset from RDB/AOF file)
  A PING here would timeout or return nothing -> we catch it correctly

Scenario 2: A proxy / stunnel / Envoy sidecar is on port 6379
  TCP connect  : succeeds (the proxy answers)
  Redis ready? : UNKNOWN — maybe the backend Redis is down
  Our PING propagates through the proxy to Redis -> PONG confirms end-to-end
```

Sending a PING and reading PONG gives you **application-level confirmation**, not just network-level.

---

### The RESP Protocol — How Redis Speaks

**RESP** = **RE**dis **S**erialization **P**rotocol.

Every single command you send to Redis and every response you receive from Redis uses RESP. It is simple, text-based, and designed to be easy to parse.

#### RESP Data Types (the 5 types you need to know)

```
+<string>\r\n          Simple String   e.g. +PONG\r\n  +OK\r\n
-<error>\r\n           Error           e.g. -ERR wrong number of args
:<integer>\r\n         Integer         e.g. :42\r\n  (used for INCR, LLEN, etc.)
$<len>\r\n<data>\r\n  Bulk String     e.g. $5\r\nhello\r\n
*<count>\r\n...        Array           e.g. *2\r\n$3\r\nGET\r\n$3\r\nfoo\r\n
```

The first character tells you the type:
- `+` = simple string (success messages, PONG)
- `-` = error
- `:` = integer
- `$` = bulk string (binary-safe, used for values)
- `*` = array (used for commands with multiple arguments)

#### How the PING Command Is Encoded

PING is an array command with 1 element — the word "PING".

```
*1\r\n         <- '*' means array, '1' means 1 element, \r\n is CRLF terminator
$4\r\n         <- '$' means bulk string, '4' means 4 bytes follow
PING\r\n       <- the 4-byte string "PING", followed by CRLF
```

In Python bytes literal:
```python
ping_command = b"*1\r\n$4\r\nPING\r\n"
```

Breaking it down character by character:
```
b"  *  1  \r  \n  $  4  \r  \n  P  I  N  G  \r  \n  "
    |  |   |    |  |  |   |    |  |  |  |  |   |    |
    |  |   CRLF   |  |  CRLF  |  command letters   CRLF
    |  |          |  |        |
    |  1 element  $  4 bytes  P-I-N-G
    array marker
```

#### The PONG Response

Redis replies to PING with a Simple String:
```
+PONG\r\n
```

- `+` = Simple String type
- `PONG` = the value
- `\r\n` = CRLF terminator

In bytes: `b"+PONG\r\n"` (7 bytes total)

We validate with:
```python
if response.startswith(b"+PONG"):
```

`startswith` instead of `==` because we don't care about trailing whitespace or extra bytes — we just confirm the PONG arrived.

---

### Why `with socket.socket(...) as s` — The Context Manager

```python
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.settimeout(timeout_sec)
    s.connect((host, port))
    s.sendall(ping_command)
    response = s.recv(128)
# Socket is automatically closed here, guaranteed
```

`socket.socket` supports the context manager protocol (`__enter__` / `__exit__`). When the `with` block exits — for any reason, including exceptions — `s.close()` is called automatically.

Compare to the manual approach:
```python
# Without context manager (risky):
s = socket.socket(...)
s.connect((host, port))          # If exception here...
response = s.recv(128)
s.close()                        # ...this line is NEVER reached -> fd leak
```

This is identical to why we use `with open(...)` for files. Same principle, same guarantee.

**Note:** The latency calculation happens OUTSIDE the `with` block intentionally:
```python
with socket.socket(...) as s:
    s.connect(...)
    s.sendall(b"*1\r\n$4\r\nPING\r\n")
    response = s.recv(128)
# <-- socket closed here

latency_ms = (time.time() - start_time) * 1000  # computed after with block
```

The socket is closed before we compute latency. This is fine — we already have `response` stored. The `with` block closes the socket as soon as we are done reading, which is the right thing to do.

---

### Latency Measurement — Why It Matters

```python
start_time = time.time()    # BEFORE connect()

# ... connect, send PING, recv PONG ...

latency_ms = (time.time() - start_time) * 1000
```

**`time.time()`** returns the current Unix timestamp as a float with sub-millisecond precision.

The latency we measure includes:
1. TCP 3-way handshake time
2. Network round-trip time (RTT)
3. Time to send PING bytes
4. Time Redis took to process and reply
5. Time to receive PONG bytes

This is the **exact same latency your application experiences** when connecting to Redis. It is far more useful than just "UP/DOWN".

**Typical latency values:**

| Scenario | Expected latency |
|----------|-----------------|
| Redis on same server (localhost) | 0.1 – 1.0 ms |
| Redis on same LAN (1 Gbps) | 0.5 – 5 ms |
| Redis on same datacenter (different rack) | 1 – 10 ms |
| Redis on different region (cross-AZ/region) | 10 – 100+ ms |

**SRE rule of thumb:** If your application has a 100ms timeout on Redis operations and your latency is 80ms, you are one network hiccup away from a timeout cascade.

---

### `s.sendall()` vs `s.send()`

```python
s.sendall(ping_command)   # Used in this script
```

`s.send(data)` sends data but may only send **part of it** if the kernel buffer is full. It returns the number of bytes actually sent, which you must check in a loop.

`s.sendall(data)` keeps calling `send()` internally until **all bytes are sent** or raises an exception. For a 15-byte PING command this is trivially the same, but `sendall` is the correct, safe choice for production code. It never silently sends a partial command.

---

### `s.recv(128)` — Why 128 Bytes?

```python
response = s.recv(128)
```

`recv(n)` reads **up to** `n` bytes. It may return fewer (the OS delivers what arrived).

The PONG response is exactly 7 bytes: `b"+PONG\r\n"`.

We use 128 because:
- It is more than enough for PONG (7 bytes) with headroom
- If Redis is in AUTH-required mode, the error response might be longer (e.g. `b"-NOAUTH Authentication required\r\n"` = 35 bytes)
- 128 bytes is a negligible allocation — no memory concern

---

### The `UNCERTAIN` State — When Redis Answers But Not With PONG

```python
else:
    print("Redis  : UNCERTAIN")
    print(f"Note   : Unexpected response: {response[:50]}")
    print("        If Redis requires a password, AUTH is needed.")
```

Redis can be configured to require authentication (`requirepass` in `redis.conf`). In that mode, any command before `AUTH` returns:

```
-NOAUTH Authentication required\r\n
```

Our PING gets this error response instead of PONG. The connection succeeded (TCP works, Redis is running), but we cannot confirm command processing without credentials.

Printing `UNCERTAIN` with the raw response is more honest than either `UP` (we didn't confirm) or `DOWN` (Redis IS running). This shows operational maturity — you do not guess.

---

### The Three Failure Modes

#### `ConnectionRefusedError`
```
Client SYN  ──> Server OS
            <── RST (nothing listening on 6379)
```
Redis service is stopped. OS kernel sent RST immediately.

**Output:**
```
Reason : Connection refused — Redis is not running.
Fix    : sudo systemctl start redis
```

#### `socket.timeout`
```
Client SYN  ──> Firewall (packet dropped, no reply)
(waiting 2 seconds)
socket.timeout raised
```
Port is firewalled. Could also mean wrong host/IP.

**Output:**
```
Reason : Timeout — no response in 2s.
Check  : Is a firewall blocking port 6379?
```

#### `OSError`
DNS resolution failure, no route to host, NIC down.

**Output:**
```
Reason : [Errno -2] Name or service not known
```

---

### Port 6379 — Where Does This Number Come From?

Port 6379 is Redis's default port. Salvatore Sanfilippo (Redis creator) has noted it was chosen because it corresponds to **MERZ** on a phone keypad — an inside joke referencing an Italian character from a TV show he liked.

It is now an IANA-registered port: officially "Redis key-value store".

All Redis-compatible databases use 6379 by default:
- Redis → 6379
- Valkey (Redis fork) → 6379
- KeyDB → 6379
- Amazon ElastiCache (Redis mode) → 6379
- AWS MemoryDB → 6379

---

## What the Interviewer Is Looking For

| What they check | What your script demonstrates |
|----------------|-------------------------------|
| Why TCP check isn't enough? | PING/PONG proves Redis processes commands, not just that port 6379 is open |
| RESP protocol knowledge? | You know Redis's wire protocol — `*1\r\n$4\r\nPING\r\n` encoded correctly |
| Context manager for sockets? | `with socket.socket() as s` — guaranteed close, no fd leaks |
| Latency measurement? | `time.time()` before connect, millisecond output — operational metric |
| `sendall` vs `send`? | You chose `sendall` — shows you understand partial writes |
| UNCERTAIN state? | AUTH-required Redis gives unexpected response — you handle it honestly |
| 3 failure modes? | `ConnectionRefused`, `timeout`, `OSError` — each with cause + fix |
| Flexible CLI defaults? | No args needed for local Redis — zero friction for the 90% case |

---

## How This Convinces the Interviewer

Redis is used in almost every modern production stack — caching, sessions, rate limiting, pub/sub, queues. "Intermittent Redis failures" is one of the most common on-call escalation types.

This script shows:
- You understand **Redis internals** (RESP protocol, PING/PONG)
- You measure **latency** — because intermittent failures often show up as latency spikes first
- You handle **AUTH** — production Redis is always password-protected
- You give **actionable output** — not just DOWN, but *why* and *how to fix it*

**Say in the interview:**
> *"In production I'd extend this to also check Redis INFO replication to verify we are talking to the primary and not a read replica — because writes to a replica silently fail. I'd also check `used_memory` vs `maxmemory` to warn before Redis hits its memory limit and starts evicting keys. Those two checks together with PING form a complete Redis health check."*

---

## Sample Output

```bash
# Redis is running and healthy:
$ python3 redis_connection_check.py
Checking Redis at localhost:6379 ...
----------------------------------------
Redis  : UP
Host   : localhost:6379
Ping   : PONG received (Redis is accepting commands)
RTT    : 0.4 ms

# Redis is stopped:
$ python3 redis_connection_check.py
Checking Redis at localhost:6379 ...
----------------------------------------
Redis  : DOWN
Host   : localhost:6379
Reason : Connection refused — Redis is not running on this port.
Fix    : sudo systemctl start redis

# Firewall blocking:
$ python3 redis_connection_check.py 10.0.0.50
Checking Redis at 10.0.0.50:6379 ...
----------------------------------------
Redis  : DOWN
Host   : 10.0.0.50:6379
Reason : Timeout — no response in 2s.
Check  : Is a firewall blocking port 6379?
         sudo ufw status | grep 6379

# Redis requires AUTH password:
$ python3 redis_connection_check.py
Checking Redis at localhost:6379 ...
----------------------------------------
Redis  : UNCERTAIN
Host   : localhost:6379
RTT    : 0.5 ms
Note   : Unexpected response: b'-NOAUTH Authentication required\r\n'
         If Redis requires a password, AUTH is needed.

# Wrong hostname:
$ python3 redis_connection_check.py redis.doesnotexist.internal
Checking Redis at redis.doesnotexist.internal:6379 ...
----------------------------------------
Redis  : DOWN
Host   : redis.doesnotexist.internal:6379
Reason : [Errno -2] Name or service not known
```

---

## Usage

```bash
# Check local Redis (most common — no args needed):
python3 redis_connection_check.py

# Check a remote Redis host:
python3 redis_connection_check.py redis.prod.internal

# Check a remote Redis on a custom port:
python3 redis_connection_check.py redis.prod.internal 6380

# Check using IP address:
python3 redis_connection_check.py 10.0.0.50 6379
```

## Requirements

- Python 3.x
- Works on **Linux, macOS, Windows**
- Network access to the Redis host and port
- **No third-party packages needed** (no `redis-py`)
- Does not require Redis credentials for basic PING check
  (AUTH-required Redis returns UNCERTAIN state, not an error)
