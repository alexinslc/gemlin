"""Built-in skill: today's date and the time. A language model can't know these by itself."""
from datetime import datetime


def current_time() -> dict:
    """Report the local date, day of the week, time and time zone. Use this whenever an
    answer depends on today's date or the time: how old something is, what day it is."""
    now = datetime.now().astimezone()
    return {"date": now.strftime("%Y-%m-%d"), "weekday": now.strftime("%A"),
            "time": now.strftime("%H:%M"), "timezone": now.tzname()}
