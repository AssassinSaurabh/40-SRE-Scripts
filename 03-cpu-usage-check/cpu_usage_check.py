import time


def get_cpu_times():
    """Reads /proc/stat and returns (total_time, idle_time)"""
    try:
        with open("/proc/stat", "r") as f:
            first_line = f.readline()

        parts = first_line.split()[1:]
        numbers = [int(p) for p in parts]

        idle_time = numbers[3] + numbers[4]
        total_time = sum(numbers)

        return total_time, idle_time

    except FileNotFoundError:
        print("Error: /proc/stat not found. Are you on Linux?")
        return None, None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None, None


def check_cpu_usage():
    """
    Checks CPU utilization of a Linux system by reading /proc/stat twice
    with a 1-second interval and computing the delta.
    Prints a WARNING if CPU usage is above 80%, otherwise confirms CPU is healthy.
    """
    print("Taking Snapshot 1...")
    total_1, idle_1 = get_cpu_times()

    if total_1 is None:
        return

    time.sleep(1)

    print("Taking Snapshot 2...")
    total_2, idle_2 = get_cpu_times()

    if total_2 is None:
        return

    total_diff = total_2 - total_1
    idle_diff = idle_2 - idle_1
    busy_diff = total_diff - idle_diff

    if total_diff > 0:
        usage_percent = (busy_diff / total_diff) * 100
    else:
        usage_percent = 0.0

    if usage_percent > 80:
        print(f"WARNING: CPU usage is high at {usage_percent:.2f}%!")
    else:
        print(f"CPU is healthy. Current usage: {usage_percent:.2f}%")


if __name__ == "__main__":
    check_cpu_usage()
