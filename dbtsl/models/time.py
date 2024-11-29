from enum import Enum


from dbtsl.models.base import deprecated


@deprecated(
    "Since the introduction of custom time granularity, the `TimeGranularity` enum is deprecated. "
    "Please just use strings to represent time grains."
)
class TimeGranularity(str, Enum):
    """A time granularity."""

    NANOSECOND = "NANOSECOND"
    MICROSECOND = "MICROSECOND"
    MILLISECOND = "MILLISECOND"
    SECOND = "SECOND"
    MINUTE = "MINUTE"
    HOUR = "HOUR"
    DAY = "DAY"
    WEEK = "WEEK"
    MONTH = "MONTH"
    QUARTER = "QUARTER"
    YEAR = "YEAR"


class DatePart(str, Enum):
    """Date part."""

    DOY = "DOY"
    DOW = "DOW"
    DAY = "DAY"
    MONTH = "MONTH"
    QUARTER = "QUARTER"
    YEAR = "YEAR"
