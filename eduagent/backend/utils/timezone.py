import os
from datetime import date, datetime, timedelta, timezone


def _tz() -> timezone:
    minutes = int(os.getenv("APP_TIMEZONE_OFFSET_MINUTES", "330"))
    return timezone(timedelta(minutes=minutes), name=os.getenv("APP_TIMEZONE", "Asia/Kolkata"))


def local_today() -> date:
    return datetime.now(_tz()).date()


def local_date(value: datetime) -> date:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(_tz()).date()
