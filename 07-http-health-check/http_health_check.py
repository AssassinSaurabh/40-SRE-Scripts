#!/usr/bin/env python3
"""
Script 07 - HTTP Endpoint Health Check
Checks if an HTTP endpoint is healthy by making a real HTTP request.
No third-party libraries (no requests) - uses Python built-in urllib.
URL is passed as a command-line argument for reusability.
"""
import sys
import urllib.request
import urllib.error


def check_health(url):
    """
    Makes an HTTP GET request to the given URL.
    Prints UP if status code is 2xx or 3xx, DOWN for anything else.
    """
    try:
        # urllib.request.urlopen() sends a real HTTP GET request.
        # timeout=5 means: if the server does not respond within 5 seconds,
        # raise an exception instead of hanging forever.
        # In production, a health check that hangs is as bad as one that fails.
        response = urllib.request.urlopen(url, timeout=5)

        # response.getcode() returns the HTTP status code as an integer.
        # e.g., 200 (OK), 201 (Created), 301 (Moved), 404 (Not Found), 500 (Server Error)
        status = response.getcode()

        # HTTP status code ranges:
        # 1xx -> Informational (rarely seen in health checks)
        # 2xx -> SUCCESS  (200 OK, 201 Created, 204 No Content)
        # 3xx -> REDIRECT (301 Moved, 302 Found) - still UP, just moved
        # 4xx -> CLIENT ERROR (404 Not Found, 401 Unauthorized) - server is UP but rejecting
        # 5xx -> SERVER ERROR (500 Internal Error, 503 Unavailable) - server is DOWN
        if 200 <= status < 400:
            print(f"Status: {status}")
            print("Service: UP")
        else:
            print(f"Status: {status}")
            print("Service: DOWN")

    except urllib.error.HTTPError as e:
        # HTTPError is raised when the server RESPONDS but with a 4xx or 5xx status.
        # The server is reachable (not a network problem) but returned an error code.
        # Example: 404 Not Found, 500 Internal Server Error, 503 Service Unavailable
        # Note: urllib raises HTTPError for 4xx/5xx instead of returning the response.
        print(f"Status: {e.code}")
        print("Service: DOWN")

    except urllib.error.URLError as e:
        # URLError is raised when the request cannot be completed at the NETWORK level.
        # This covers three real production scenarios:
        # 1. Timeout    -> Server is overloaded or unreachable, took more than 5 seconds
        # 2. DNS fail   -> Hostname could not be resolved (e.g., "myapp.internal" is wrong)
        # 3. Refused    -> Server is down, nothing listening on that port
        # e.reason gives us the underlying OS-level reason string.
        print(f"Status: Unreachable ({e.reason})")
        print("Service: DOWN")


if __name__ == "__main__":
    # sys.argv is the list of command-line arguments.
    # sys.argv[0] is always the script name itself.
    # sys.argv[1] should be the URL the user passes.
    # len(sys.argv) != 2 means no URL was given (or too many were given).
    if len(sys.argv) != 2:
        print("Usage: python3 http_health_check.py <url>")
        print("Example: python3 http_health_check.py https://google.com")
        sys.exit(1)

    target_url = sys.argv[1]
    check_health(target_url)
