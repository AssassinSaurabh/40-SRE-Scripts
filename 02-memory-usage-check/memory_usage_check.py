def check_memory_usage():
    """
    Checks the system RAM usage by reading /proc/meminfo.
    Prints a WARNING if memory usage is above 80%, otherwise confirms memory is healthy.
    Works on Linux systems only.
    """
    try:
        with open("/proc/meminfo", "r") as f:
            lines = f.readlines()

        mem_info = {}
        for line in lines:
            parts = line.split()
            key = parts[0].rstrip(":")
            value = int(parts[1])
            mem_info[key] = value

        mem_total = mem_info.get("MemTotal", 0)
        mem_available = mem_info.get("MemAvailable", 0)

        if mem_total == 0:
            print("Error: Could not determine total memory from /proc/meminfo.")
            return

        mem_used = mem_total - mem_available
        usage_percent = (mem_used / mem_total) * 100

        if usage_percent > 80:
            print(f"WARNING: Memory usage is high at {usage_percent:.2f}%!")
        else:
            print(f"Memory is healthy. Current usage: {usage_percent:.2f}%")

    except FileNotFoundError:
        print("Error: /proc/meminfo not found. Are you on Linux?")
    except Exception as e:
        print(f"Error checking memory usage: {e}")


check_memory_usage()
