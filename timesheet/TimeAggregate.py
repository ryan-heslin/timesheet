import datetime
from typing import Callable

from timesheet import constants


class TimeAggregate:
    def __init__(
            self, decrement : Callable, increment: Callable,  floor: Callable, string_format: str, name: str
    ):
        self.name = name
        self.string_format = string_format
        self.decrement  = decrement
        self.increment = increment
        self.floor = floor


# Days 

def increment_day(date: datetime.date):
    return date + datetime.timedelta(days=1)

# No need to round date to nearest day!
def floor_day(date: datetime.date):
    return date

def decrement_day(date:datetime.date): 
    return date - datetime.timedelta(days=1)


# Weeks 

def increment_week(date: datetime.date):
    # Increments to Monday of next week
    return floor_week(date) + datetime.timedelta(days=constants.DAYS_IN_WEEK)

def floor_week(date: datetime.date):
    calendar = date.isocalendar()
    # Subtract -indexed value of weekday (Monday = 1, etc.)
    return date - datetime.timedelta(days=calendar[2] - 1)

# Just find Monday of week and subtract 7 days
def decrement_week(date : datetime.date):
    return floor_week(date)  - datetime.timedelta(days=constants.DAYS_IN_WEEK)

def increment_month(date: datetime.date):
    # Reworking of https://stackoverflow.com/questions/4130922/how-to-increment-datetime-by-custom-months-in-python-without-using-library
    month = date.month % constants.MONTHS_IN_YEAR + 1
    # Only increase year if last month
    year = date.year + date.month // 12
    return datetime.date(year=year, month=month, day=1)

# Months 

def floor_month(date: datetime.date):
    return datetime.date(year=date.year, month=date.month, day=1)

def decrement_month(date : datetime.date):
    month = constants.MONTHS_IN_YEAR - (date.month -1 ) % constants.MONTHS_IN_YEAR
    year = date.year - (date.month == 1)
    return datetime.date(year=year, month=month, day=1)

# Years

def increment_year(date):
    return datetime.date(year=date.year + 1, month=1, day=1)

def floor_year(date: datetime.date):
    return datetime.date(year=date.year, month=1, day=1)

def decrement_year(date : datetime.date):
    return datetime.date(year=date.year - 1, month=1, day=1)


# Representation strftime formats for aggregates

day_format = "%Y-%m-%d"
# Year-week: week 0 for days in January before first Monday
week_format = "%Y-%W"
month_format = "%Y-%-m"
year_format = "%Y"

# Built-in aggregation time spans
Day = TimeAggregate(decrement_day, increment_day , floor_day, day_format, "day")
Week = TimeAggregate(decrement_week, increment_week, floor_week, week_format, "week")
Month = TimeAggregate(decrement_month, increment_month , floor_month, month_format, "month")
Year = TimeAggregate(decrement_year, increment_year , floor_year, year_format, "year")
