# 07 - HTTP Endpoint Health Check

## The Interview Question

> *"Write a Python script that checks whether an HTTP endpoint is healthy. If it returns a successful response, print UP; otherwise print DOWN."*

---

## What This Script Does

1. Takes a URL as a **command-line argument** (reusable for any endpoint)
2. Sends a real HTTP GET request with a **5-second timeout**
3. Checks the HTTP status code
4. Prints `UP` for 2xx/3xx responses, `DOWN` for everything else
5. Handles all three failure modes: bad status codes, HTTP errors, and network failures

---

## The Clean Solution

```python
import sys
import urllib.request
import urllib.error

def check_health(url):
    try:
        response = urllib.request.urlopen(url, timeout=5)
        status = response.getcode()

        if 200 <= status < 400:
            print(f"Status: {status}")
            print("Service: UP")
        else:
            print(f"Status: {status}")
            print("Service: DOWN")

    except urllib.error.HTTPError as e:
        print(f"Status: {e.code}")
        print("Service: DOWN")

    except urllib.error.URLError as e:
        print(f"Status: Unreachable ({e.reason})")
        print("Service: DOWN")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 http_health_check.py <url>")
        sys.exit(1)
    check_health(sys.argv[1])
```

---

## How We Achieved This — Every Decision Explained

### Why `urllib` and not `requests`?

The interviewer said no psutil, implying no third-party libraries. `urllib` is Python's built-in HTTP client — zero installation, always available, even on a bare server.

```
urllib.request  -> Makes the actual HTTP request (GET, POST, etc.)
urllib.error    -> Contains exception classes for HTTP and URL-level failures
```

### How `urllib.request.urlopen()` works

```
urllib.request.urlopen(url, timeout=5)
                       |    |
                       |    +-- If no response in 5 seconds, raise URLError
                       +------- Send HTTP GET to this URL
```

It returns a **response object** (like a file) if the request succeeds.
You call `.getcode()` on it to get the HTTP status code as an integer.

**Why `timeout=5`?**
Without a timeout, if the server is unreachable or extremely slow, `urlopen()` will hang **forever**. A health check that hangs is as bad as one that fails — it blocks your monitoring pipeline. In production, SREs set short timeouts (2–10 seconds) on health checks.

### HTTP Status Code Logic

```
200–399 = Service is UP
  200 OK             -> Normal success
  201 Created        -> POST succeeded
  204 No Content     -> Success, no body (common for health endpoints)
  301 Moved          -> Redirect - server is UP, just at a new URL
  302 Found          -> Temporary redirect - server is UP

400+ = Service is DOWN
  404 Not Found      -> Wrong URL (but server is UP - debatable in interviews!)
  500 Internal Error -> Server crashed
  502 Bad Gateway    -> Upstream service failed
  503 Unavailable    -> Service temporarily down (deployments, overload)
```

> **Interview talking point:** Whether 404 counts as UP or DOWN depends on context. For a generic health check endpoint (like `/health` or `/ping`), 404 means the endpoint doesn't exist — so DOWN. This script conservatively marks anything ≥400 as DOWN.

### The Two Exception Classes — Why Both Matter

```python
except urllib.error.HTTPError as e:
```
**When:** Server responded, but with 4xx or 5xx.
The server IS reachable (network is fine), it just returned an error code.
`e.code` gives you the exact status (e.g., 503).

```python
except urllib.error.URLError as e:
```
**When:** Request failed at the network level — server never sent a response.
Three real production causes:
```
1. Timeout      -> Server alive but overloaded/slow (took > 5 seconds)
2. DNS failure  -> "myapp.prod.internal" doesn't resolve -> wrong hostname
3. Connection refused -> Nothing listening on that port -> server is truly DOWN
```
`e.reason` gives the OS-level reason string (e.g., `timed out`, `[Errno -2] Name or service not known`).

**Why not catch them with one `except Exception`?**
Because the fix for each is different:
- HTTPError 503 -> check your app logs
- DNS failure -> check your DNS config or VPN
- Timeout -> check network latency or server load

Separate exceptions let you (or future monitoring code) take different actions.

### Why `sys.argv` instead of hardcoding the URL?

```python
target_url = sys.argv[1]
```

Hardcoding the URL inside the script means you need a different script for every service.
`sys.argv` lets you pass the URL at runtime:

```bash
python3 http_health_check.py https://api.myapp.com/health
python3 http_health_check.py https://payment-service/ping
python3 http_health_check.py http://localhost:8080
```

One script, any endpoint. This is how real monitoring tools work.

---

## What the Interviewer Is Looking For

| What they check | What your script demonstrates |
|----------------|-------------------------------|
| Do you know HTTP basics? | You understand status code ranges (2xx/3xx = UP, 4xx/5xx = DOWN) |
| Timeout awareness? | `timeout=5` shows you know hanging is a real failure mode |
| Exception handling depth? | Two separate except blocks for two different failure types |
| No hardcoded values? | `sys.argv` makes it a real tool, not a demo |
| No external deps? | `urllib` shows Python standard library competence |

---

## How This Convinces the Interviewer

This script is the building block of every SRE health check pipeline:

- **Kubernetes liveness/readiness probes** — same concept, different syntax
- **Cron-based uptime monitoring** — run this every minute, alert on DOWN
- **Deployment verification** — run after deploy to confirm the new version started
- **Synthetic monitoring** — simulate real user traffic to check endpoints

**Say in the interview:**
> *"In production I'd extend this to record response time, send alerts to PagerDuty or Slack if DOWN, and run it in a loop with exponential backoff before alerting to avoid false positives from transient errors."*

---

## Sample Output

```bash
# Healthy endpoint:
python3 http_health_check.py https://google.com
Status: 200
Service: UP

# Server error:
python3 http_health_check.py https://httpstat.us/503
Status: 503
Service: DOWN

# Unreachable / timeout:
python3 http_health_check.py https://doesnotexist.invalid
Status: Unreachable ([Errno -2] Name or service not known)
Service: DOWN

# No URL given:
python3 http_health_check.py
Usage: python3 http_health_check.py <url>
```

---

## Usage

```bash
python3 http_health_check.py <url>

# Examples:
python3 http_health_check.py https://google.com
python3 http_health_check.py http://localhost:8080/health
python3 http_health_check.py https://api.github.com
```

## Requirements

- Python 3.x
- Works on **Linux, macOS, Windows**
- Network access to the target URL
- No third-party packages needed
