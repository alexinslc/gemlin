"""Built-in skill: what kind of computer this is, and how long it has been on."""
import platform
import subprocess
import time
from contextlib import suppress

import psutil


def system_info() -> dict:
    """Report the operating system, processor, core count, Python version, and how long
    since the computer last restarted. Use this when the user asks about their computer,
    its specs, or when it was last restarted."""
    system = platform.system()
    if system == "Darwin":
        os_name = f"macOS {platform.mac_ver()[0]}"
    elif system == "Linux":
        try:
            os_name = platform.freedesktop_os_release().get("PRETTY_NAME", "Linux")
        except OSError:
            os_name = "Linux"
    else:
        os_name = f"{system} {platform.release()}"
    up = time.time() - psutil.boot_time()
    return {"os": os_name, "processor": processor(),
            "cores": psutil.cpu_count(logical=False), "threads": psutil.cpu_count(),
            "python": platform.python_version(),
            "on_for": f"{int(up // 86400)} days, {int(up % 86400 // 3600)} hours"}


def processor():  # a readable chip name, like "Apple M3 Max" or "Intel(R) Core(TM) i7"
    with suppress(OSError, subprocess.SubprocessError):
        if platform.system() == "Darwin":
            return subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True,
                                  text=True, timeout=3).stdout.strip() or platform.machine()
        if platform.system() == "Linux":
            with open("/proc/cpuinfo", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("model name"):
                        return line.split(":", 1)[1].strip()
    return platform.processor() or platform.machine()
