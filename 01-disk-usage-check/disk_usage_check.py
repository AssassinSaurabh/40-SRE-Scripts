import shutil


def check_disk_usage_shutil():
    """
    Checks the disk usage of the root filesystem "/".
    Prints a WARNING if usage is above 80%, otherwise confirms disk is healthy.
    Uses Python built-in shutil module - no external dependencies needed.
    """
    try:
        disk = shutil.disk_usage("/")

        # Percentage calculate kar rahe hain: (used / total) * 100
        usage_percent = (disk.used / disk.total) * 100

        if usage_percent > 80:
            print(f"WARNING: Disk usage is high at {usage_percent:.2f}%!")
        else:
            print(f"Disk is healthy. Current usage: {usage_percent:.2f}%")

    except Exception as e:
        print(f"Error checking disk usage: {e}")


check_disk_usage_shutil()
