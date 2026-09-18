#!/usr/bin/env python3
"""
Script 20 - Memory Leak Detector
Reads a file containing timestamped memory usage measurements.
Checks if the last 3 readings show a continuous increase.
If yes: warns of a possible memory leak.
No third-party libraries needed.
"""
import sys


def check_memory_trend(filepath):
    """
    Reads memory values from a log file and checks whether the last
    3 measurements are strictly increasing (possible memory leak).

    Expected log file format — one entry per line:
        <timestamp>  <memory_value_in_MB>
    Example:
        2024-01-15 10:00:00 512
        2024-01-15 10:05:00 520
        2024-01-15 10:10:00 535
        2024-01-15 10:15:00 548

    We only care about the LAST field on each line (the memory value).
    The timestamp format does not matter — we ignore it.
    """
    values = []

    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()   # Remove leading/trailing whitespace and \n

                # Skip blank lines (empty lines between entries)
                if not line:
                    continue

                # split() breaks the line on any whitespace.
                # [-1] gets the LAST token — the memory value.
                # This works regardless of whether the timestamp is
                # "10:00:00" (1 word) or "2024-01-15 10:00:00" (2 words).
                #
                # Example:
                #   "2024-01-15 10:00:00 512".split() -> ["2024-01-15", "10:00:00", "512"]
                #   [-1] -> "512"
                #
                # float() handles both integers ("512") and decimals ("512.4")
                values.append(float(line.split()[-1]))

    except FileNotFoundError:
        print(f"Error: File not found: '{filepath}'")
        sys.exit(1)

    # -------------------------------------------------------------------
    # GUARD: Need at least 3 measurements to check a trend
    # -------------------------------------------------------------------
    if len(values) < 3:
        print(f"Not enough data: found {len(values)} reading(s), need at least 3.")
        return

    # -------------------------------------------------------------------
    # THE TREND CHECK: look at only the LAST 3 values
    # -------------------------------------------------------------------
    # values[-3:] is a slice that gives us the last 3 elements.
    # Example: values = [512, 495, 520, 535, 548]
    #          values[-3:] = [520, 535, 548]
    #
    # We use the most recent 3 readings because:
    # - Old data may be from a different time period or after a restart
    # - A continuous rise in the last 3 points is a strong short-term signal
    last3 = values[-3:]

    print(f"Total readings : {len(values)}")
    print(f"Last 3 values  : {last3[0]} MB -> {last3[1]} MB -> {last3[2]} MB")
    print("-" * 45)

    # -------------------------------------------------------------------
    # CHAINED COMPARISON: last3[0] < last3[1] < last3[2]
    # -------------------------------------------------------------------
    # Python's chained comparison checks:
    #   last3[0] < last3[1]  AND  last3[1] < last3[2]
    # Both must be True for the overall expression to be True.
    #
    # This means ALL THREE values must be STRICTLY increasing:
    #   512 < 520 < 535  -> True  (continuously rising)   -> WARNING
    #   512 < 520 > 515  -> False (not monotonic)         -> OK
    #   512 = 512 < 515  -> False (not STRICTLY greater)  -> OK
    # -------------------------------------------------------------------
    if last3[0] < last3[1] < last3[2]:
        print("Status : WARNING — Memory is continuously increasing!")
        print("         Possible memory leak. Investigate the application.")
    else:
        print("Status : OK — Memory is not continuously increasing.")


def main():
    if len(sys.argv) != 2:
        print("Usage  : python3 memory_leak_detector.py <log_file>")
        print("Example: python3 memory_leak_detector.py memory_usage.log")
        sys.exit(1)

    check_memory_trend(sys.argv[1])


if __name__ == "__main__":
    main()
