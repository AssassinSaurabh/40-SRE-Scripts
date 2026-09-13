#!/usr/bin/env python3
"""
Script 17 - HTTP Health Check with Retry Logic
Calls an HTTP health endpoint and retries on failure.
Retries up to MAX_RETRIES times with exponential backoff between attempts.
Declares the service DOWN only after all retries are exhausted.
No third-party libraries - uses built-in urllib and time modules.
"""
import sys
import time
import urllib.request
import urllib.error


# ---------------------------------------------------------------------------
# CONFIGURATION CONSTANTS
# ---------------------------------------------------------------------------
MAX_RETRIES    = 3      # Maximum number of retry attempts after the first failure
TIMEOUT_SEC    = 5      # Seconds to wait for each HTTP response before giving up
BACKOFF_BASE   = 2      # Exponential backoff base in seconds (2, 4, 8 seconds)
# ---------------------------------------------------------------------------


def check_health(url, max_retries=MAX_RETRIES, timeout=TIMEOUT_SEC):
    """
    Performs an HTTP GET request to `url` and retries up to `max_retries` times
    on any failure. Waits with exponential backoff between each retry.

    Args:
        url        (str): The HTTP health endpoint URL to check.
        max_retries (int): How many times to retry after an initial failure.
        timeout    (int): Per-request timeout in seconds.

    Returns:
        None. Prints result to stdout.
    """
    # Total attempts = 1 initial try + max_retries retries
    # Example: max_retries=3 -> attempts 1, 2, 3, 4
    total_attempts = max_retries + 1
    last_error = None   # Store the most recent failure reason for the final report

    for attempt in range(1, total_attempts + 1):

        print(f"Attempt {attempt}/{total_attempts} -> {url}")

        try:
            # -------------------------------------------------------------------
            # urllib.request.urlopen()
            # -------------------------------------------------------------------
            # Opens the URL and returns an HTTPResponse object.
            # timeout=timeout: if no response within 'timeout' seconds, raises
            # socket.timeout (which urllib wraps as urllib.error.URLError).
            #
            # This does a real HTTP GET request. It follows redirects by default
            # (up to 10 redirects before raising urllib.error.HTTPError).
            # -------------------------------------------------------------------
            response = urllib.request.urlopen(url, timeout=timeout)
            status   = response.getcode()   # HTTP status code (int): 200, 301, 404, etc.

            # -------------------------------------------------------------------
            # SUCCESS CONDITION
            # -------------------------------------------------------------------
            # HTTP 2xx codes = success family (200 OK, 201 Created, 204 No Content, etc.)
            # HTTP 3xx codes = redirect family. urlopen() follows them automatically,
            #                  so by the time we see a 3xx, we already followed it.
            # We treat 200-399 as UP. Anything >= 400 is a server/client error.
            # -------------------------------------------------------------------
            if 200 <= status < 400:
                print(f"Status : {status} OK")
                print(f"Result : UP (responded on attempt {attempt})")
                return   # Success — stop retrying

            else:
                # Server is reachable but returned an error status (4xx, 5xx)
                # This IS a failure we should retry. The server might be temporarily
                # overloaded (503) or a deploy is in progress (502).
                last_error = f"HTTP {status}"
                print(f"Status : {status} (error response)")

        except urllib.error.HTTPError as e:
            # HTTPError is raised when the server returns a 4xx or 5xx status.
            # Note: for codes > 400, urllib raises this exception rather than
            # returning the response. We still treat it as a failure to retry.
            last_error = f"HTTP {e.code} {e.reason}"
            print(f"Status : {e.code} {e.reason}")

        except urllib.error.URLError as e:
            # URLError covers network-level failures:
            #   - Connection refused (service is down)
            #   - DNS resolution failure (wrong URL)
            #   - Socket timeout (slow response, overloaded server)
            #   - SSL certificate error
            last_error = str(e.reason)
            print(f"Error  : {e.reason}")

        # -------------------------------------------------------------------
        # EXPONENTIAL BACKOFF
        # -------------------------------------------------------------------
        # After each FAILED attempt (except the last one), wait before retrying.
        # We do NOT wait after the final attempt — the service is already DOWN.
        #
        # Exponential backoff formula: wait = BACKOFF_BASE ** attempt
        #   Attempt 1 fails -> wait 2^1 = 2  seconds before attempt 2
        #   Attempt 2 fails -> wait 2^2 = 4  seconds before attempt 3
        #   Attempt 3 fails -> wait 2^3 = 8  seconds before attempt 4
        #   Attempt 4 fails -> no wait  (done, declare DOWN)
        #
        # Why exponential and not fixed?
        # A fixed 2s wait on every retry hammers a struggling server.
        # Exponential backoff gives the server progressively more time to recover,
        # reducing load during an outage. This is the industry standard.
        # (AWS SQS, Google Cloud Tasks, and most HTTP clients use it.)
        # -------------------------------------------------------------------
        if attempt < total_attempts:
            wait_sec = BACKOFF_BASE ** attempt   # 2, 4, 8 seconds
            print(f"Waiting : {wait_sec}s before retry...")
            time.sleep(wait_sec)

    # -------------------------------------------------------------------
    # ALL RETRIES EXHAUSTED
    # -------------------------------------------------------------------
    print("-" * 45)
    print(f"Result : DOWN")
    print(f"Reason : {last_error}")
    print(f"        Failed after {total_attempts} attempt(s).")


def main():
    if len(sys.argv) < 2:
        print("Usage  : python3 http_retry_health_check.py <url>")
        print("Example: python3 http_retry_health_check.py https://myapp.com/health")
        sys.exit(1)

    url = sys.argv[1]

    print("=" * 45)
    print("HTTP Health Check with Retry")
    print("=" * 45)
    print(f"URL      : {url}")
    print(f"Max Retries  : {MAX_RETRIES}")
    print(f"Timeout/req  : {TIMEOUT_SEC}s")
    print(f"Backoff      : {BACKOFF_BASE}^attempt seconds")
    print("-" * 45)

    check_health(url)


if __name__ == "__main__":
    main()
