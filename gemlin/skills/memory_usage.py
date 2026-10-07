"""Built-in skill: how much memory (RAM) is in use."""
import psutil


def memory_usage() -> dict:
    """Report RAM total, used and available (GB), percent used, and swap in use.
    Use this when the user asks about memory, RAM, or why apps feel sluggish."""
    ram, swap = psutil.virtual_memory(), psutil.swap_memory()
    def gb(n):
        return round(n / 1e9, 1)
    return {"total_gb": gb(ram.total), "used_gb": gb(ram.total - ram.available), "available_gb": gb(ram.available),
            "percent_used": ram.percent, "swap_used_gb": gb(swap.used)}
