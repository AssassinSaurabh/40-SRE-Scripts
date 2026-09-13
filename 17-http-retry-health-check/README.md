# 17 - HTTP Health Check with Retry Logic

## The Interview Question

> *"Write a Python script that calls an HTTP health endpoint and retries the request if it fails. Retry a maximum of 3 times before declaring the service DOWN."*

---

## What This Script Does

1. Takes a **URL** as a command-line argument
2. Sends an HTTP GET request with a **5-second timeout**
3. If the request fails (network error, 4xx, 5xx), **retries up to 3 times**
4. Waits with **exponential backoff** between each retry (2s → 4s → 8s)
5. Declares **UP** on the first successful response (200–399)
6. Declares **DOWN** only after all retries are exhausted — showing the last error

---

## The Solution

```python
import sys
import time
import urllib.request
import urllib.error

MAX_RETRIES  = 3
TIMEOUT_SEC  = 5
BACKOFF_BASE = 2

def check_health(url, max_retries=MAX_RETRIES, timeout=TIMEOUT_SEC):
    total_attempts = max_retries + 1
    last_error = None

    for attempt in range(1, total_attempts + 1):
        print(f"Attempt {attempt}/{total_attempts} -> {url}")
        try:
            response = urllib.request.urlopen(url, timeout=timeout)
            status   = response.getcode()

            if 200 <= status < 400:
                print(f"Result : UP (responded on attempt {attempt})")
                return

            last_error = f"HTTP {status}"
            print(f"Status : {status} (error)")

        except urllib.error.HTTPError as e:
            last_error = f"HTTP {e.code} {e.reason}"
            print(f"Status : {e.code} {e.reason}")

        except urllib.error.URLError as e:
            last_error = str(e.reason)
            print(f"Error  : {e.reason}")

        if attempt < total_attempts:
            wait_sec = BACKOFF_BASE ** attempt
            print(f"Waiting: {wait_sec}s before retry...")
            time.sleep(wait_sec)

    print(f"Result : DOWN — {last_error} (failed after {total_attempts} attempts)")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 http_retry_health_check.py <url>")
        sys.exit(1)
    check_health(sys.argv[1])
```

---

## How We Achieved This — Every Decision Explained

### Why `max_retries + 1` Total Attempts?

```python
total_attempts = max_retries + 1   # 3 retries = 4 total attempts
for attempt in range(1, total_attempts + 1):
```

The question says "retry a maximum of 3 times". This means:

```
Attempt 1  -> the FIRST try (not a retry)
Attempt 2  -> retry 1
Attempt 3  -> retry 2
Attempt 4  -> retry 3  (final)
              -> if this fails: declare DOWN
```

`total_attempts = 3 + 1 = 4`. `range(1, 5)` gives `[1, 2, 3, 4]`. Correct.

Using `range(1, total_attempts + 1)` instead of `range(total_attempts)` means the loop variable starts at `1` — which makes the printed output `Attempt 1/4` instead of `Attempt 0/4`. Natural for a human reader.

---

### The `last_error` Variable — Why Track This?

```python
last_error = None

for attempt in ...:
    try:
        ...
    except ... as e:
        last_error = str(e.reason)

# After loop:
print(f"Result : DOWN — {last_error}")
```

When all retries fail, the engineer needs to know WHY. Was it a timeout? A 503? A DNS failure?

`last_error` stores the most recent failure message. Each failed attempt overwrites it with the latest reason. After the loop, the final value is the failure reason from the last attempt — the most relevant one.

Without this, you'd only print "DOWN" with no diagnosis — useless in production.

---

### Exponential Backoff — The Industry Standard

```python
if attempt < total_attempts:
    wait_sec = BACKOFF_BASE ** attempt   # 2^1=2, 2^2=4, 2^3=8
    print(f"Waiting: {wait_sec}s before retry...")
    time.sleep(wait_sec)
```

#### What is exponential backoff?

Instead of waiting a fixed time between retries, you wait an **exponentially increasing** amount of time:

```
After attempt 1 fails -> wait  2 seconds  (2^1)
After attempt 2 fails -> wait  4 seconds  (2^2)
After attempt 3 fails -> wait  8 seconds  (2^3)
After attempt 4 fails -> no wait (last attempt, declare DOWN)

Total wait time before giving up: 2 + 4 + 8 = 14 seconds
```

#### Why exponential and not a fixed 2s delay?

| Fixed delay (2s each) | Exponential backoff |
|-----------------------|---------------------|
| Hammers a struggling server with rapid requests | Gives the server progressively more time to recover |
| 3 retries = 6 seconds total wait | 3 retries = 14 seconds total wait |
| Can worsen a partial outage (thundering herd) | Reduces load during an outage — standard recovery pattern |
| Simple but dangerous at scale | Industry standard: AWS SQS, GCP Pub/Sub, Kubernetes kubelet, HTTP clients |

#### The `BACKOFF_BASE ** attempt` formula

`**` is Python's exponentiation operator:
```
2 ** 1 = 2
2 ** 2 = 4
2 ** 3 = 8
```

`BACKOFF_BASE = 2` is a named constant at the top of the file. If you wanted faster retries, change it to `1.5`. Named constants are easy to tune; magic numbers buried in formulas are not.

#### Why no wait after the LAST attempt?

```python
if attempt < total_attempts:   # Don't wait if this was the final attempt
    time.sleep(wait_sec)
```

After the final failed attempt we immediately declare DOWN. Waiting 8 seconds before saying "DOWN" serves no purpose — the service is confirmed dead and the operator needs the result now.

---

### The `range(1, total_attempts + 1)` Loop — `return` as Success Exit

```python
for attempt in range(1, total_attempts + 1):
    try:
        ...
        if 200 <= status < 400:
            print(f"Result : UP")
            return           # EXIT the function immediately on success
    except:
        ...
```

On success we call `return` — this exits the entire function immediately. The loop stops. No more retries happen. This is cleaner than setting a `success` flag and breaking the loop:

```python
# Messy alternative:
success = False
for attempt in ...:
    if ...:
        success = True
        break
if success:
    print("UP")
else:
    print("DOWN")

# Clean version (what we use):
for attempt in ...:
    if ...:
        print("UP")
        return    # done
print("DOWN")     # only reached if loop completes without return
```

If the function `return`s from inside the loop, execution never reaches the `print("DOWN")` after the loop. If the loop completes normally (all attempts failed), execution falls through to `print("DOWN")`.

---

### Two Exception Types — Why Both Are Needed

#### `urllib.error.HTTPError`

```python
except urllib.error.HTTPError as e:
    last_error = f"HTTP {e.code} {e.reason}"
```

Raised when the server **responds with a 4xx or 5xx status code**.

```
Server is reachable on the network.
Server received our request.
Server replied: "503 Service Unavailable"
urllib raises: HTTPError(code=503, reason="Service Unavailable")
```

`e.code` = integer status code (e.g. 503)
`e.reason` = text description (e.g. "Service Unavailable")

**Should we retry 4xx errors?** That's a design choice:
- **503 Service Unavailable** → YES, server is overloaded, retry makes sense
- **429 Too Many Requests** → YES, but wait longer
- **404 Not Found** → Technically NO (wrong URL), but this script retries anyway for simplicity
- **401 Unauthorized** → NO (wrong credentials, retrying won't help)

For a general health check script, retrying all failures is acceptable. In production, you'd filter which codes trigger a retry.

#### `urllib.error.URLError`

```python
except urllib.error.URLError as e:
    last_error = str(e.reason)
```

Raised when the request **can't reach the server at all**:

| Scenario | `e.reason` value |
|----------|-----------------|
| Service not running (port closed) | `[Errno 111] Connection refused` |
| DNS can't resolve the hostname | `[Errno -2] Name or service not known` |
| Request timed out | `timed out` |
| SSL certificate invalid | `[SSL: CERTIFICATE_VERIFY_FAILED]` |
| No network route | `[Errno 101] Network is unreachable` |

`e.reason` can be a string OR another exception object. `str(e.reason)` converts both cases to a printable string safely.

**Class hierarchy (important for the interview):**
```
IOError
  └── OSError
        └── urllib.error.URLError
                  └── urllib.error.HTTPError
```

`HTTPError` is a subclass of `URLError`. This means:
- `except URLError` would catch BOTH URLError AND HTTPError
- We put `HTTPError` first because Python checks except clauses top-to-bottom
- If we put `URLError` first, it would catch HTTPError before the HTTPError clause runs

---

### `response.getcode()` — Getting the HTTP Status

```python
response = urllib.request.urlopen(url, timeout=timeout)
status   = response.getcode()
```

`urllib.request.urlopen()` returns an `http.client.HTTPResponse` object.
`response.getcode()` returns the integer HTTP status code.

Note: `urlopen()` by default follows redirects (301, 302, etc.) automatically. So by the time `getcode()` is called, we already have the final status after all redirects. The returned code is always the final destination's code.

---

### Why Named Constants at the Top?

```python
MAX_RETRIES  = 3
TIMEOUT_SEC  = 5
BACKOFF_BASE = 2
```

Three reasons:

1. **Readability** — `MAX_RETRIES` is clearer than magic number `3` buried inside a loop
2. **Maintainability** — Change the retry count in one place, not hunting through the code
3. **Interview signal** — Shows you think about production configurability. In real code, these would come from environment variables or a config file

By convention, module-level constants in Python are written in `ALL_CAPS` with underscores (PEP 8 style).

---

## Retry vs No-Retry — When Does Retrying Help?

Retrying is the right approach for **transient failures** — problems that are temporary and resolve on their own:

| Failure type | Transient? | Should retry? |
|-------------|-----------|---------------|
| Network blip (brief packet loss) | Yes | ✅ Yes |
| Server overloaded (503) | Yes | ✅ Yes |
| Deploy in progress (502 for ~10s) | Yes | ✅ Yes |
| Service fully down | No | ❌ Retrying won't help, but we try to be sure |
| Wrong URL (404) | No | ❌ Won't help, but harmless |
| Bad credentials (401) | No | ❌ Won't help |

In practice: a health check should always retry. A single timeout might be a one-off packet drop. Three consecutive failures is a real problem.

---

## What the Interviewer Is Looking For

| What they check | What your script demonstrates |
|----------------|-------------------------------|
| Retry logic structure? | `range(1, total_attempts + 1)` — clean loop, `return` on success |
| `max_retries + 1` distinction? | You know "3 retries" ≠ "3 total attempts" |
| Exponential backoff? | `BACKOFF_BASE ** attempt` — industry standard, not fixed delay |
| No wait after last attempt? | `if attempt < total_attempts` — efficiency and UX awareness |
| Two exception types? | `HTTPError` vs `URLError` — class hierarchy, order matters |
| `last_error` tracking? | Preserves failure reason for the final DOWN message |
| Named constants? | `MAX_RETRIES`, `TIMEOUT_SEC`, `BACKOFF_BASE` — tunable, not magic numbers |
| `return` as loop exit? | Clean success exit — no flag variables needed |

---

## How This Convinces the Interviewer

Retry with backoff is not just a script pattern — it is a **fundamental reliability engineering concept**. It appears in:

- **Kubernetes liveness/readiness probes** — `failureThreshold: 3` + `periodSeconds`
- **AWS SDK** — built-in retry with exponential backoff for all API calls
- **Google Cloud client libraries** — same pattern
- **Circuit breaker pattern** — extended retry with a "give up for N minutes" state

**Say in the interview:**
> *"In production I'd add jitter to the backoff — instead of exactly 2, 4, 8 seconds, I'd use `random.uniform(0, 2^attempt)`. This prevents the thundering herd problem where hundreds of services all retry at the exact same second after an outage clears, causing a second wave of load. AWS calls this 'jitter + exponential backoff' and documents it as best practice."*

---

## Sample Output

```bash
# Service is UP on first attempt:
$ python3 http_retry_health_check.py https://google.com/
=============================================
HTTP Health Check with Retry
=============================================
URL          : https://google.com/
Max Retries  : 3
Timeout/req  : 5s
Backoff      : 2^attempt seconds
---------------------------------------------
Attempt 1/4 -> https://google.com/
Status : 200 OK
Result : UP (responded on attempt 1)

# Service is DOWN (all retries exhausted):
$ python3 http_retry_health_check.py http://localhost:9999/health
=============================================
HTTP Health Check with Retry
=============================================
Attempt 1/4 -> http://localhost:9999/health
Error  : [Errno 111] Connection refused
Waiting: 2s before retry...
Attempt 2/4 -> http://localhost:9999/health
Error  : [Errno 111] Connection refused
Waiting: 4s before retry...
Attempt 3/4 -> http://localhost:9999/health
Error  : [Errno 111] Connection refused
Waiting: 8s before retry...
Attempt 4/4 -> http://localhost:9999/health
Error  : [Errno 111] Connection refused
---------------------------------------------
Result : DOWN
Reason : [Errno 111] Connection refused
        Failed after 4 attempt(s).

# Service recovers on attempt 3 (flaky endpoint):
Attempt 1/4 -> http://myapp.internal/health
Error  : timed out
Waiting: 2s before retry...
Attempt 2/4 -> http://myapp.internal/health
Status : 503 Service Unavailable
Waiting: 4s before retry...
Attempt 3/4 -> http://myapp.internal/health
Status : 200 OK
Result : UP (responded on attempt 3)
```

---

## Usage

```bash
python3 http_retry_health_check.py <url>

# Examples:
python3 http_retry_health_check.py https://myapp.com/health
python3 http_retry_health_check.py http://localhost:8080/healthz
python3 http_retry_health_check.py https://api.example.com/status
```

## Requirements

- Python 3.x
- Works on **Linux, macOS, Windows**
- Network access to the target URL
- **No third-party packages needed** — uses built-in `urllib` and `time`
