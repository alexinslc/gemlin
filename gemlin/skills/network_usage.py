"""Built-in skill: how much data this computer has sent and received."""
import psutil


def network_usage() -> dict:
    """Report how much data has been sent and received since the computer started, and
    which connections carried it (on a Mac, en0 is usually Wi-Fi). Never looks at what was
    sent. Use this when the user asks about the internet, Wi-Fi, the network, or data usage."""
    total = psutil.net_io_counters()
    up = {name for name, stats in psutil.net_if_stats().items() if stats.isup}
    busy = sorted(((io.bytes_sent + io.bytes_recv, name) for name, io in psutil.net_io_counters(pernic=True).items()
                   if name in up and not name.lower().startswith(("lo", "loopback"))), reverse=True)
    return {"sent_mb": round(total.bytes_sent / 1e6), "received_mb": round(total.bytes_recv / 1e6),
            "busiest_connections": [{"name": name, "mb": round(size / 1e6)} for size, name in busy[:3] if size >= 1e6]}
