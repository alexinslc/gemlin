"""Built-in skill: check the laptop battery. Skills are plain Python files; the file name
must match the function name, and the docstring tells Gemlin when to use it."""
import psutil


def battery_status() -> dict:
    """Report battery percent, whether it is plugged in, and minutes left.
    Use this when the user asks about battery, charging, or unplugging."""
    b = psutil.sensors_battery()
    if b is None:
        return {"battery": "none found (desktop, VM, or unsupported OS)"}
    unknown = (psutil.POWER_TIME_UNLIMITED, psutil.POWER_TIME_UNKNOWN)
    minutes = None if b.secsleft in unknown else b.secsleft // 60
    return {"percent": round(b.percent), "plugged_in": b.power_plugged, "minutes_left": minutes}
