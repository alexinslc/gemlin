"""Example skill: the apps that have been open the longest."""
import time

import psutil


def long_running_apps(top_n: int = 8) -> list:
    """List your apps that have been running the longest, with how long and how much memory
    they use (all of an app's helper processes counted together). Use this when the user asks
    what's been open forever, or what they could quit to free up memory."""
    me, apps = psutil.Process().username(), {}
    for p in psutil.process_iter(["name", "username", "create_time", "memory_percent"]):
        info = p.info
        if info["username"] != me or not info["name"] or not info["create_time"]:
            continue
        name = info["name"].split(" Helper")[0]  # "Google Chrome Helper" is still Chrome
        started, memory = apps.get(name, (info["create_time"], 0.0))
        apps[name] = (min(started, info["create_time"]), memory + (info["memory_percent"] or 0))
    oldest = sorted(apps.items(), key=lambda item: item[1][0])[:min(top_n, 20)]
    return [{"app": name, "open_for_hours": round((time.time() - started) / 3600, 1), "memory_percent": round(memory, 1)}
            for name, (started, memory) in oldest]
