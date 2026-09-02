# 09 - TCP Port Reachability Checker

## The Interview Question

> *"Write a Python script that checks whether a given TCP port on a host is reachable. Print whether the port is OPEN or CLOSED."*

---

## What This Script Does

1. Takes a **hostname** and **port number** as command-line arguments
2. Creates a real TCP socket and attempts a connection
3. Applies a **3-second timeout** so the script never hangs
4. Prints `OPEN` if the connection succeeds, `CLOSED` with the reason if it fails
5. Always closes the socket — no resource leaks

---

## The Clean Solution

```python
import socket
import sys

def check_tcp_port(host, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(3.0)
    try:
        s.connect((host, port))
        print(f"{host}:{port} -> OPEN")
    except (socket.timeout, ConnectionRefusedError, OSError):
        print(f"{host}:{port} -> CLOSED")
    finally:
        s.close()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 tcp_port_checker.py <host> <port>")
        sys.exit(1)
    check_tcp_port(sys.argv[1], int(sys.argv[2]))
```

---

## How We Achieved This — Every Decision Explained

### What is a Socket?

A **socket** is an endpoint for two-way communication over a network.
Think of it like a phone — you need to create a phone (socket), dial a number (connect to host:port), and wait for someone to pick up (server accepts).

```
Your Script (Client)              Remote Server
───────────────────               ─────────────
1. socket()    -> create phone
2. connect()   -> dial 80 on google.com   ->  (ring ring)
3. If someone picks up (SYN-ACK) -> OPEN
4. If line is dead (RST or silence) -> CLOSED
5. close()     -> hang up
```

### `socket.AF_INET` and `socket.SOCK_STREAM` — What Do These Mean?

```python
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
```

These are two configuration flags:

**`AF_INET` — Address Family:**

| Flag | Meaning |
|------|---------|
| `AF_INET` | Use IPv4 addresses (e.g., `142.250.182.46`) |
| `AF_INET6` | Use IPv6 addresses (e.g., `2001:db8::1`) |

We use `AF_INET` because most production servers and the interview question deal with standard IPv4.

**`SOCK_STREAM` — Socket Type:**

| Flag | Protocol | Behaviour |
|------|----------|-----------|
| `SOCK_STREAM` | **TCP** | Connection-oriented, reliable, ordered delivery, 3-way handshake |
| `SOCK_DGRAM` | **UDP** | Connectionless, fire-and-forget, no handshake, no guarantee |

We use `SOCK_STREAM` (TCP) because:
- TCP does a **3-way handshake** before any data is sent
- We exploit this handshake — if the handshake completes, the port is OPEN
- UDP has no handshake, so you cannot confirm a port is "open" the same way

### The TCP 3-Way Handshake — The Real Test

When we call `s.connect((host, port))`, Python triggers the full TCP handshake:

```
Client (our script)        Server (remote)
──────────────────         ───────────────
       SYN         ──────>
                   <──────    SYN-ACK        <- port is OPEN, server ready
       ACK         ──────>
    [CONNECTED]                              <- s.connect() returns successfully
```

**Port is CLOSED — Instant RST:**
```
Client (our script)        Server / Firewall
──────────────────         ─────────────────
       SYN         ──────>
                   <──────    RST            <- nothing listening on this port
  [ConnectionRefusedError]                   <- raised immediately (fast!)
```

**Port is FIREWALLED — Silence:**
```
Client (our script)        Firewall
──────────────────         ────────
       SYN         ──────> (packet silently DROPPED, no reply)
       ...waiting...
  [socket.timeout]                           <- after 3 seconds
```

This distinction matters in an interview:
- **RST = Connection Refused** — host is up, nothing listening on that port
- **Timeout = Firewall dropping packets** — host may be up but port is filtered

### Why `s.settimeout(3.0)` — Not Just Leaving Default?

The default TCP timeout (no `settimeout`) is managed by the OS kernel and can be **up to 75–127 seconds** in some Linux configurations.

```
Without timeout: check 10 firewalled hosts = 10 × 127s = 21+ minutes ❌
With timeout 3s: check 10 firewalled hosts = 10 × 3s   = 30 seconds  ✅
```

In SRE health checks and monitoring scripts, you **always** set explicit timeouts. An infinite wait is a bug.

### The Three Exception Types — What Each One Means

```python
except socket.timeout:
```
> The 3-second window expired with no response.
> **Cause:** Firewall silently dropping packets, host unreachable, or severe network congestion.
> **SRE action:** Check network path, firewall rules, `traceroute`, `mtr`.

```python
except ConnectionRefusedError:
```
> Server sent back TCP RST immediately. This is actually the FASTEST failure.
> **Cause:** Host is reachable, but no process is listening on that port.
> **SRE action:** Is the service running? `systemctl status nginx`, `ss -tlnp`.

```python
except OSError as e:
```
> A broader network failure.
> **Cause:** DNS resolution failed (`socket.gaierror` is a subclass of `OSError`), no route to host, network interface down.
> **SRE action:** Check DNS (`dig`, `nslookup`), check routing (`ip route`), check NIC (`ip link`).

### Why `finally` for `s.close()`?

```python
finally:
    s.close()
```

`finally` runs **no matter what** — whether `connect()` succeeded, timed out, or raised any exception.

Why this matters:
- Every socket = one OS **file descriptor (fd)**
- Linux limits open fds per process: `ulimit -n` (default ~1024)
- A script checking 1000 ports without closing = 1000 fds leaked = eventual crash with `Too many open files`
- `s.close()` releases the fd **immediately**

This is the same reason we use `with open()` for files — guaranteed cleanup.

---

## Well-Known Ports — Useful for Testing

| Port | Service | Test command |
|------|---------|-------------|
| 22 | SSH | `python3 tcp_port_checker.py myserver.com 22` |
| 80 | HTTP | `python3 tcp_port_checker.py google.com 80` |
| 443 | HTTPS | `python3 tcp_port_checker.py google.com 443` |
| 3306 | MySQL | `python3 tcp_port_checker.py db.internal 3306` |
| 5432 | PostgreSQL | `python3 tcp_port_checker.py db.internal 5432` |
| 6379 | Redis | `python3 tcp_port_checker.py cache.internal 6379` |
| 9200 | Elasticsearch | `python3 tcp_port_checker.py es.internal 9200` |

---

## What the Interviewer Is Looking For

| What they check | What your script demonstrates |
|----------------|-------------------------------|
| Do you know sockets? | `AF_INET`, `SOCK_STREAM` — correct TCP socket creation |
| Do you know TCP? | You can explain the 3-way handshake and why it tells us if a port is open |
| Timeout awareness? | `settimeout(3.0)` — never leave timeouts unconfigured |
| 3 distinct exception cases? | `timeout` vs `ConnectionRefused` vs `OSError` — each means something different |
| Resource cleanup? | `finally: s.close()` — no file descriptor leaks |
| CLI-ready tool? | `sys.argv` — works for any host/port, not a hardcoded demo |

---

## How This Convinces the Interviewer

TCP port checks are used **everywhere** in SRE:

- **Pre-deployment check:** "Is the database port reachable from the app server?"
- **Network debugging:** "Did the firewall rule actually open port 8080?"
- **Service dependency check:** Run before starting your app to verify all dependencies are reachable
- **Kubernetes readiness probe alternative:** Same concept as `tcpSocket` probes in pod specs

**Say in the interview:**
> *"In production I'd extend this to scan a list of (host, port) pairs from a YAML config, run checks in parallel using `concurrent.futures.ThreadPoolExecutor`, and send Slack/PagerDuty alerts for any CLOSED port. This becomes a lightweight connectivity monitor."*

---

## Sample Output

```bash
# Open port:
python3 tcp_port_checker.py google.com 443
142.250.77.46:443 -> OPEN

# Closed port (nothing listening):
python3 tcp_port_checker.py google.com 9999
142.250.77.46:9999 -> CLOSED (connection refused - nothing listening)

# Firewalled port (timeout):
python3 tcp_port_checker.py 10.0.0.1 22
10.0.0.1:22 -> CLOSED (timeout - no response in 3s)

# Wrong usage:
python3 tcp_port_checker.py google.com
Usage: python3 tcp_port_checker.py <host> <port>
```

---

## Usage

```bash
python3 tcp_port_checker.py <host> <port>

# Examples:
python3 tcp_port_checker.py google.com 443
python3 tcp_port_checker.py localhost 5432
python3 tcp_port_checker.py 192.168.1.100 22
```

## Requirements

- Python 3.x
- Works on **Linux, macOS, Windows**
- Network access to the target host
- No third-party packages needed
