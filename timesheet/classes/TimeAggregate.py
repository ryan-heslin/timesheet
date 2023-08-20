import datetime
from typing import Callable
from typing import Dict
from typing import Iterable
from typing import List
from typing import Tuple
from typing import Union

from ..utils import constants


class TimeAggregate:
    """
    Represents a unit of time, such as a day or month, used in computing
    aggregates

    :param decrement: Function of one argument that reduces the
    aggregate by one unit.
    :type decrement: Callable
    :param increment: Function of one argument that increases the
    :type increment: Callable
    :param floor: Function of one argument that rounds the
    aggregate to the date of the next lowest unit (e.g., converting a date
                                                   to the first day of the
                                                   month for a month aggregate).
    :type floor: Callable
    :param string_format: :code:`DateFormat` instance representing
    the fields contained in this instance
    :type string_format: DateFormat
    :param name: Name for the created instance
    :type name: str
    """
    def __init__(
            self, decrement : Callable, increment: Callable,  floor: Callable, string_format: "DateFormat", name: str
    ) -> None:
        self.name = name
        self.string_format = string_format
        self.decrement  = decrement
        self.increment = increment
        self.floor = floor

class DateFormat():
    """
    Defines a date format using ISO symbols, with support for separating into
    individual components

    :param format: String containing ISO date formatting symbols separated
    by :code:`separator`, e.g. '%Y-%m-%d'.
    :type format: str
    :param components:  Names for each date component, e.g. 'year', 'month', 'day'.
    :type components: Tuple[str, ...]
    :param separator:  String separating each date component. It must be present
    in :code:`format`. If None, no splitting is done and one component is assumed.
    Default '-'.
    :type separator: Union[str, None], optional
    """

    def __init__(self, format : str, components : Tuple[str, ...], separator : Union[str, None] = "-") ->  None:
        if not ( separator is None or separator in format):
            raise ValueError(f"Separator {separator} not used in format {format}")
        self.format = format
        self.separator = separator
        self.components = components

    def decompose(self, datestamp : str) -> List[str]:
        """Break date format string into its component pieces"""
        return  [part.lstrip("0") for part in datestamp.split(self.separator)]

    def decompose_dict(self, datestamps : Iterable[str]) -> Dict[str, Tuple[str]]:
        """Turn a list of datestamps in format into dict of component lists"""
        return dict(zip(self.components, zip(*[ self.decompose(datestamp) for datestamp in datestamps ])))

# Days
def increment_day(date: datetime.date) -> datetime.date:
    return date + datetime.timedelta(days=1)

# No need to round date to nearest day!
def floor_day(date: datetime.date) -> datetime.date:
    return date

def decrement_day(date:datetime.date) -> datetime.date:
    return date - datetime.timedelta(days=1)


# Weeks

def increment_week(date: datetime.date) -> datetime.date:
    # Increments to Monday of next week
    return floor_week(date) + datetime.timedelta(days=constants.DAYS_IN_WEEK)

def floor_week(date: datetime.date) -> datetime.date:
    calendar = date.isocalendar()
    # Subtract -indexed value of weekday (Monday = 1, etc.)
    return date - datetime.timedelta(days=calendar[2] - 1)

# Just find Monday of week and subtract 7 days
def decrement_week(date : datetime.date) -> datetime.date:
    return floor_week(date)  - datetime.timedelta(days=constants.DAYS_IN_WEEK)

def increment_month(date: datetime.date) -> datetime.date:
    # Reworking of https://stackoverflow.com/questions/4130922/how-to-increment-datetime-by-custom-months-in-python-without-using-library
    month = date.month % constants.MONTHS_IN_YEAR + 1
    # Only increase year if last month
    year = date.year + date.month // 12
    return datetime.date(year=year, month=month, day=1)

# Months

def floor_month(date: datetime.date) -> datetime.date:
    return datetime.date(year=date.year, month=date.month, day=1)

def decrement_month(date : datetime.date) -> datetime.date:
    month = constants.MONTHS_IN_YEAR - (date.month -1 ) % constants.MONTHS_IN_YEAR
    year = date.year - (date.month == 1)
    return datetime.date(year=year, month=month, day=1)

# Years

def increment_year(date) -> datetime.date:
    return datetime.date(year=date.year + 1, month=1, day=1)

def floor_year(date: datetime.date) -> datetime.date:
    return datetime.date(year=date.year, month=1, day=1)

def decrement_year(date : datetime.date) -> datetime.date:
    return datetime.date(year=date.year - 1, month=1, day=1)


# Representation of strftime formats for aggregates

day_format = DateFormat(format = "%Y-%m-%d", components = ( "year", "month", "day" ))
# Year-week: week 0 for days in January before first Monday
week_format = DateFormat(format = "%Y-%W", components = ( "year", "week" ))
month_format = DateFormat(format = "%Y-%-m", components = ( "year", "month" ))
year_format = DateFormat(format = "%Y", components=( "year", ), separator = None)

# Built-in aggregation time spans
Day = TimeAggregate(decrement_day, increment_day , floor_day, day_format, "day")
Week = TimeAggregate(decrement_week, increment_week, floor_week, week_format, "week")
Month = TimeAggregate(decrement_month, increment_month , floor_month, month_format, "month")
Year = TimeAggregate(decrement_year, increment_year , floor_year, year_format, "year")
