from datetime import datetime
from zoneinfo import ZoneInfo

SLOTS = (
    (6, 6, "dawn"),
    (7, 8, "morning"),
    (9, 11, "forenoon"),
    (12, 12, "noon"),
    (13, 14, "afternoon_early"),
    (15, 17, "afternoon"),
    (18, 18, "dusk"),
    (19, 20, "evening"),
    (21, 22, "night"),
    (23, 23, "close"),
)
SLOT_NAMES = tuple(name for _, _, name in SLOTS)
POEM_HOURS = frozenset({6, 10, 15, 18, 21, 23})


def uses_poem(hour):
    return hour in POEM_HOURS


def now(timezone_name):
    return datetime.now(ZoneInfo(timezone_name))


def slot_for(moment, start_hour, end_hour):
    if moment.hour < start_hour or moment.hour > end_hour:
        return None
    for start, end, name in SLOTS:
        if start <= moment.hour <= end:
            return name
    return None


def in_grace(moment, grace_minutes):
    return moment.minute <= grace_minutes


def hour_key(moment):
    return f"{moment:%Y-%m-%d}-{moment.hour:02d}"
