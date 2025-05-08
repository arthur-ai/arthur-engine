from datetime import datetime, timedelta

STRFTIME_CODES_TO_TIMEDELTA = {
    "%H": timedelta(hours=1),  # Hour (24-hour clock) as zero-padded decimal number
    "%-H": timedelta(hours=1),  # Hour (24-hour clock) as decimal number
    "%I": timedelta(hours=1),  # Hour (12-hour clock)
    "%d": timedelta(days=1),  # Day of month as zero-padded decimal
    "%-d": timedelta(days=1),  # Day of month as decimal number
    "%j": timedelta(
        days=1,
    ),  # Day of year as zero-padded decimal number (001, ..., 366)
    "%-j": timedelta(days=1),  # Day of year as decimal number (1, ..., 366)
}


def find_smallest_timedelta(format_string: str) -> timedelta | None:
    """Scans a linux strftime format string to find the smallest time unit present.
    Only considers units larger than or equal to an hour or less than or equal to a day.
    Example: '%Y-%m-%d_%H' -> timedelta(hours=1), '%Y-%m-%d' -> timedelta(days=1)
    """
    smallest_delta = None
    for code, delta in STRFTIME_CODES_TO_TIMEDELTA.items():
        if code in format_string:
            if smallest_delta is None or delta < smallest_delta:
                smallest_delta = delta
    return smallest_delta


def check_datetime_tz_aware(dt: datetime) -> bool:
    """Returns true if dt is timezone-aware, false if naive."""
    return (
        True if dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None else False
    )
