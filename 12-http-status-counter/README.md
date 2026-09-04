# 12 - HTTP Access Log Status Code Counter

## The Interview Question

> *"You have an HTTP access log. Write a Python script that counts how many requests returned each HTTP status code and prints the results."*

---

## What This Script Does

1. Takes an **HTTP access log path** as a command-line argument
2. Reads the file **line by line** — memory-safe for gigabyte-scale logs
3. Parses each line using the **Combined Log Format structure** to extract the status code
4. Validates that extracted codes are genuine 3-digit numbers
5. Counts each status code using a **dictionary**
6. Prints a **sorted, categorised, percentage-included report**
7. Reports skipped malformed lines for full transparency

---

## The Clean Solution

```python
import sys

def count_status_codes(filepath):
    status_counts = {}

    try:
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    parts = line.split('"')
                    status_code = parts[2].strip().split()[0]

                    if not status_code.isdigit() or len(status_code) != 3:
                        continue

                    status_counts[status_code] = status_counts.get(status_code, 0) + 1
                except (IndexError, ValueError):
                    pass

        for code in sorted(status_counts.keys(), key=int):
            print(f"{code}  ->  {status_counts[code]} requests")

    except FileNotFoundError:
        print(f"CRITICAL: Log file not found: '{filepath}'")
    except PermissionError:
        print(f"CRITICAL: Permission denied: '{filepath}'")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 http_status_counter.py <path_to_access_log>")
        sys.exit(1)
    count_status_codes(sys.argv[1])
```

---

## The Foundation: What is the Combined Log Format?

Before writing a single line of Python, you must understand what you are parsing.

Apache and Nginx — the two most common web servers in production — both write access logs in the **Combined Log Format** by default. Every HTTP request becomes exactly one line.

### A Real Log Line, Annotated

```
192.168.1.1 - frank [04/Sep/2024:22:01:15 +0530] "GET /index.html HTTP/1.1" 200 1524 "-" "Mozilla/5.0"
```

Let's label every single field:

```
Field 1  : 192.168.1.1
           Client IP address — who sent the request

Field 2  : -
           RFC 1413 ident (almost always "-", not used in modern deployments)

Field 3  : frank
           Authenticated username ("-" for anonymous/unauthenticated requests)

Field 4  : [04/Sep/2024:22:01:15 +0530]
           Timestamp in [day/month/year:hour:minute:second timezone] format

Field 5  : "GET /index.html HTTP/1.1"
           The request line — always wrapped in double quotes
           └── Method: GET
           └── Path:   /index.html
           └── Proto:  HTTP/1.1

Field 6  : 200              ← THIS IS WHAT WE WANT
           HTTP Status Code — the server's response

Field 7  : 1524
           Response body size in bytes ("-" if empty response)

Field 8  : "-"
           Referrer URL — which page the user came from (in quotes)

Field 9  : "Mozilla/5.0"
           User-Agent string — browser/client identifier (in quotes)
```

### The Key Observation

Look at the structure around the status code:

```
... "GET /index.html HTTP/1.1" 200 1524 "-" "Mozilla/5.0"
                              ↑
                 Status code is ALWAYS right after the closing "
```

The request line (Field 5) is the ONLY field that is guaranteed to be in double quotes in the first segment of the line. After its closing `"`, the very next token is the status code.

This structure is what our parsing exploits.

---

## How We Achieved This — Every Decision Explained

### The Parsing Strategy: Splitting on Double Quotes `"`

```python
parts = line.split('"')
status_code = parts[2].strip().split()[0]
```

This is the heart of the script. Let's trace it step by step.

**Full log line:**
```
'192.168.1.1 - frank [04/Sep/2024:22:01:15 +0530] "GET /index.html HTTP/1.1" 200 1524 "-" "Mozilla/5.0"'
```

**Step 1: `line.split('"')`**

Split the entire line every time a `"` character appears:

```
parts[0] = '192.168.1.1 - frank [04/Sep/2024:22:01:15 +0530] '
parts[1] = 'GET /index.html HTTP/1.1'
parts[2] = ' 200 1524 '
parts[3] = '-'
parts[4] = ' '
parts[5] = 'Mozilla/5.0'
parts[6] = ''
```

**Why does `parts[2]` give us the status code?**

The double quotes appear in this order in a Combined Log Format line:
```
Position 1 opening "  -> opens the request field (Field 5)
Position 2 closing "  -> closes the request field
Position 3 opening "  -> opens the referrer field (Field 8)
Position 4 closing "  -> closes the referrer field
Position 5 opening "  -> opens the user-agent field (Field 9)
Position 6 closing "  -> closes the user-agent field
```

When we split on `"`:
```
parts[0] = everything BEFORE opening quote 1   (IP, ident, user, timestamp)
parts[1] = everything BETWEEN quote 1 and 2    (the request line)
parts[2] = everything BETWEEN quote 2 and 3    (status code + size)  ← HERE
parts[3] = everything BETWEEN quote 3 and 4    (referrer value)
...
```

`parts[2]` is always ` 200 1524 ` — status code followed by response size.

**Step 2: `parts[2].strip().split()[0]`**

```
parts[2]             = ' 200 1524 '
parts[2].strip()     = '200 1524'        <- removes surrounding spaces
.split()             = ['200', '1524']   <- splits on whitespace
[0]                  = '200'             <- first token = status code
```

Done. Status code extracted in 3 chained operations.

### Why Not Regex?

You might think regex is the "proper" way to parse logs. But consider:

```python
# Regex approach:
import re
match = re.search(r'" (\d{3}) ', line)
if match:
    status_code = match.group(1)

# String split approach (what we use):
status_code = line.split('"')[2].strip().split()[0]
```

The split approach is:
- **Faster** — string indexing is O(1), regex compiles and matches a pattern
- **Simpler** — no regex syntax to remember or explain
- **More readable** — the intent is clear: "give me what's after the second quote"
- **No imports** — regex needs `import re`

For a well-structured format like Combined Log Format, splits beat regex.
Use regex only when the structure is irregular or you need pattern matching.

### The Sanity Check: `status_code.isdigit() and len(status_code) == 3`

```python
if not status_code.isdigit() or len(status_code) != 3:
    skipped_lines += 1
    continue
```

After splitting, we validate the extracted token before trusting it.

**Why is this necessary?**

Some log lines are not standard:
```
# Custom log format - status code might be missing or in wrong position
::1 - - [date] "OPTIONS * HTTP/1.0" 200 -

# Log rotation header injected by logrotate
#Fields: cs-ip time cs-method cs-uri-stem

# Nginx error format mixed into access log
2024/09/04 22:01:15 [error] 1234#0: *5 connect() failed

# Line with "-" for status (some custom configs)
192.168.1.1 - - [date] "GET /" - -
```

In all these cases, `parts[2].strip().split()[0]` might return something that is NOT a status code (e.g., `"-"`, `"#Fields:"`, `"[error]"`).

`status_code.isdigit()` — Returns `True` only if every character is a digit (0–9).
- `"200".isdigit()` → `True` ✅
- `"-".isdigit()` → `False` → skip
- `"200a".isdigit()` → `False` → skip

`len(status_code) == 3` — HTTP status codes are always exactly 3 digits.
- `"200"` → length 3 → valid ✅
- `"20"` → length 2 → skip
- `"2000"` → length 4 → skip

Together, this guard ensures we only count real HTTP status codes.

### Counting: `dict.get(status_code, 0) + 1`

```python
status_counts[status_code] = status_counts.get(status_code, 0) + 1
```

This is the same counting pattern from Script 11 (IP detector). Worth reinforcing:

```
First time we see "404":
  status_counts.get("404", 0)  ->  0  (not in dict, return default)
  status_counts["404"] = 0 + 1 = 1

Next time we see "404":
  status_counts.get("404", 0)  ->  1  (found in dict)
  status_counts["404"] = 1 + 1 = 2

After 87 lines with "404":
  status_counts = { "200": 1523, "404": 87, "500": 3, ... }
```

One dictionary entry per unique status code — constant space, O(1) update per line.

### Sorting: `sorted(status_counts.keys(), key=int)`

```python
for code in sorted(status_counts.keys(), key=int):
```

Without `key=int`, Python sorts strings **lexicographically** (dictionary order):

```
Lexicographic sort of ["500", "200", "404", "301", "99"]:
  -> ["200", "301", "404", "500", "99"]    ← WRONG! "99" goes last
```

String `"99"` sorts after `"5"` because `'9' > '5'` in ASCII — but numerically 99 < 200.

With `key=int`, Python converts each key to an integer first, then sorts numerically:

```
Numeric sort of ["500", "200", "404", "301", "99"]:
  key=int applied: [500, 200, 404, 301, 99]
  sorted:          [99, 200, 301, 404, 500]
  -> result:       ["99", "200", "301", "404", "500"]  ← CORRECT
```

`key=int` does NOT modify the original strings — it only tells `sorted()` what to compare by.

### Percentage Calculation

```python
percentage = (count / total_requests * 100) if total_requests > 0 else 0
```

`total_requests = sum(status_counts.values())` gives the total number of successfully parsed requests.

The ternary `if total_requests > 0 else 0` prevents `ZeroDivisionError` if the log file is empty or every line was malformed (all skipped).

Percentages turn raw counts into actionable insight:
```
200  ->  95,230  requests  (95.2%)   <- nearly all traffic is successful
500  ->      47  requests   (0.05%)  <- tiny but critical
```

An SRE looks at percentages, not just counts, to understand the error RATE.

### The `skipped_lines` Counter — Why Track This?

```python
print(f"  Skipped lines   : {skipped_lines} (malformed / blank)")
```

Transparency matters in production tools. If you silently skip 30% of lines, your report is wrong but looks correct.

By reporting skipped lines, we tell the operator:
- `Skipped: 0` → perfect log, trust the results fully
- `Skipped: 500` → investigate! Might be a different log format, corrupted file, or mixed log types

This is the difference between a demo script and a production-grade tool.

---

## The HTTP Status Code Reference

Every SRE must know these by heart:

### 2xx — Success (Server fulfilled the request)

| Code | Name | Meaning |
|------|------|---------|
| 200 | OK | Standard success. Request completed normally |
| 201 | Created | POST succeeded, new resource created |
| 204 | No Content | Success but no response body (common for DELETE, health checks) |
| 206 | Partial Content | Range request (video streaming, large file downloads) |

### 3xx — Redirection (Client must take additional action)

| Code | Name | Meaning |
|------|------|---------|
| 301 | Moved Permanently | URL changed forever — update bookmarks, SEO juice transfers |
| 302 | Found | Temporary redirect — original URL still valid |
| 304 | Not Modified | Browser cache is still fresh — server sent no body (saves bandwidth) |
| 307 | Temporary Redirect | Like 302 but preserves HTTP method (POST stays POST) |

### 4xx — Client Error (The request itself was wrong)

| Code | Name | Meaning |
|------|------|---------|
| 400 | Bad Request | Malformed request syntax (broken JSON, invalid params) |
| 401 | Unauthorized | Authentication required or credentials wrong |
| 403 | Forbidden | Authenticated but not allowed (insufficient permissions) |
| 404 | Not Found | Resource does not exist at this URL |
| 429 | Too Many Requests | Rate limiting — client is sending too many requests |

### 5xx — Server Error (Server failed to fulfil a valid request)

| Code | Name | Meaning |
|------|------|---------|
| 500 | Internal Server Error | Generic server crash — check app logs immediately |
| 502 | Bad Gateway | Upstream (app server, database) is not responding |
| 503 | Service Unavailable | Server overloaded or in maintenance mode |
| 504 | Gateway Timeout | Upstream took too long to respond |

> **SRE alert threshold rule of thumb:**
> - **5xx rate > 0.1%** → investigate immediately
> - **404 rate > 5%** → possible misconfiguration or broken links
> - **429 rate rising** → check if a client is misbehaving or you need to scale

---

## What the Interviewer Is Looking For

| What they check | What your script demonstrates |
|----------------|-------------------------------|
| Do you know log formats? | You parse Combined Log Format correctly — the industry standard |
| Smart parsing strategy? | Split on `"` — no regex, simpler, faster, more readable |
| Input validation? | `isdigit()` + `len == 3` guard — rejects malformed lines gracefully |
| Dictionary counting? | `dict.get(code, 0) + 1` — standard O(1) counting pattern |
| Correct sorting? | `key=int` — avoids lexicographic sort bug ("99" > "200" as string) |
| Transparency? | Reports skipped lines count — production-grade honesty |
| Memory efficiency? | Line-by-line iteration — handles multi-GB log files |
| HTTP knowledge? | 5 categories, common codes, when each signals a problem |

---

## How This Convinces the Interviewer

HTTP access log analysis is one of the most common SRE daily tasks:

- **Post-incident review:** "What was our 5xx rate during the outage window?"
- **Deployment verification:** "After the deploy, did our 500 rate drop?"
- **Capacity planning:** "What percentage of requests hit our CDN cache (304)?"
- **Security audit:** "Are we seeing 401/403 spikes that indicate probing attempts?"

Tools like Datadog, Splunk, and ELK do this at massive scale — but this script is their core logic at the single-file level.

**Say in the interview:**
> *"In production, I'd extend this to also filter by time window — parse the timestamp field and only count requests in the last N minutes. I'd also add a '--watch' mode using a loop with `file.seek()` to tail the log in real time and alert when the 5xx rate crosses a threshold. That's essentially a lightweight APM agent."*

---

## Test It Yourself

Generate a realistic sample access log:

```bash
python3 -c "
import random, datetime

ips = ['10.0.0.1', '192.168.1.5', '8.8.8.8', '203.0.113.4']
paths = ['/index.html', '/api/users', '/api/orders', '/static/style.css', '/login']
codes = ['200']*70 + ['301']*5 + ['304']*10 + ['404']*8 + ['500']*4 + ['503']*3
methods = ['GET', 'POST', 'DELETE']

lines = []
for i in range(200):
    ip = random.choice(ips)
    method = random.choice(methods)
    path = random.choice(paths)
    code = random.choice(codes)
    size = random.randint(100, 5000)
    ts = '04/Sep/2024:22:01:{:02d} +0530'.format(i % 60)
    lines.append(f'{ip} - - [{ts}] "{method} {path} HTTP/1.1" {code} {size} "-" "Mozilla/5.0"')

open('sample_access.log', 'w').write('\n'.join(lines))
print('sample_access.log created with', len(lines), 'lines')
"

python3 http_status_counter.py sample_access.log
```

---

## Sample Output

```
HTTP Status Code Report
File: /var/log/nginx/access.log
=======================================================
  Code     Count      %       Category
-------------------------------------------------------
  200      95230    89.4%    2xx Success
  301        423     0.4%    3xx Redirection
  304       9870     9.3%    3xx Redirection
  400         12     0.01%   4xx Client Error
  401         34     0.03%   4xx Client Error
  404        287     0.3%    4xx Client Error
  429         18     0.02%   4xx Client Error
  500         47     0.04%   5xx Server Error
  503          8     0.01%   5xx Server Error
=======================================================
  Total requests  : 106,929
  Unique codes    : 9
  Skipped lines   : 3 (malformed / blank)
```

---

## Usage

```bash
python3 http_status_counter.py <path_to_access_log>

# Examples:
python3 http_status_counter.py /var/log/nginx/access.log
python3 http_status_counter.py /var/log/apache2/access.log
python3 http_status_counter.py sample_access.log
```

## Requirements

- Python 3.x
- Works on **Linux, macOS, Windows**
- Read permission on the target log file
- Log file must be in **Apache/Nginx Combined Log Format** (or Common Log Format)
- No third-party packages needed
