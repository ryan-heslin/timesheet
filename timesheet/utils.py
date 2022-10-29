import datetime
import os
import re
import shelve
import sys
from os import getenv
from os.path import exists
from os.path import expanduser
from os.path import join
from os.path import split
from os.path import splitext
from typing import Any
from typing import Callable
from typing import Dict
from typing import Iterable
from typing import List
from typing import Union

import click

from timesheet import constants
from timesheet import TimeAggregate
from timesheet import Timesheet


# From https://stackoverflow.com/questions/11875770/how-to-overcome-datetime-datetime-not-json-serializable
def json_serialize(x : Union[datetime.datetime, datetime.time, "Timesheet.DayLog"]):
    """Convert datetime objects to ISO format suitable for JSON serialization
    :param x Union[datetime.datetime, datetime.time, "Timesheet.DayLog"]: an object
    of these types


    """
    if isinstance(x, (datetime.datetime, datetime.time)):
        return x.isoformat()
    elif isinstance(x, Timesheet.DayLog):
        return x.timestamps
    raise TypeError(f"Cannot serialize object of type {type(x)}")

def path_checker(permissions : int) -> Callable:
    """Create function to check whether a user has specified permissions to use a path
    permissions int: One or more :code:`os` permission codes to check for (e.g., :code:`os.W_OK | os.X_OK` )
    :rtype Callable: Function with :code:`bool` return type that checks whether
    the user has the given permissions for some path
    """
    def inner(path : str):
        return os.access(path, permissions)
    return inner

path_readable = path_checker((os.R_OK))
path_writeable = path_checker(os.W_OK | os.X_OK)

def date_parser(di : Dict[str, str]) -> Dict[str, "Timesheet.DayLog"]:
    """Parses a JSON where keys are ISO-formatted dates and values are lists of ISO-formatted times to be converted to DiffTime objects

    :param di: Dict of timestamp strings in any ISO format
    :rtype Dict[str, "Timesheet.DayLog"]: Dict of :code:`DayLog` objects constructed
    from timestamps
    """
    out = {}
    for k in di:
        date = datetime.date.fromisoformat(k)
        timestamps = [Timesheet.DiffTime.fromisoformat(ts) for ts in di[k]]
        out[k] = Timesheet.DayLog(date=date, timestamps=timestamps)
    return out


def validate_datestamps(datestamps: Iterable[str]) -> bool:
    """Confirms whether all datestamps in an iterable parse in ISO format
    :param datestamps Iterable[str]: Iterable of date strings whose formats to check
    :rtype bool: :code:`bool` indicating whether all datestamps were valid
    """
    try:
        return all(
            datetime.date.fromisoformat(timestamp) or True for timestamp in datestamps
        )
    except ValueError as e:
        raise e

def storage_path() -> str:
    """
    Returns the storage path known to :code:`timesheet` - the :code:`TIMESHEET_DIR`
    environment variable if set, otherwise the path :code:`"~/.timesheet/timesheets"`.
    :rtype str: The path found.
    """
    return getenv("TIMESHEET_DIR", expanduser("~/.timesheet/timesheets"))


def next_number(stem : str, names : List[str]) -> int:
    """
    Given a list of strings and a stem, finds all that start with the stem and
    end with digits and returns the highest such number plus one.
    :param stem: str Filename to check for
    :param names: List[str] Strings to check for any starting with the stem and ending
    with a  number
    :rtype int: The next sequential number, starting from 1.
    """
    if names == []:
        return 1
    pattern = stem + r"(\d+)\.?.*$"
    numbers = set([0])
    for name in names:
        number = re.match(pattern, name)
        if number is not None:
            # If somehow a number is negative
            numbers.add(abs(int(number.group(1))))
    return max(numbers) + 1


# storage_name ignored if None
def use_shelve_file(
        func : Callable, storage_name: Union[str, None] = None,
        path: Union[str, None] = None, confirm_prompt: Union[str, None] = None
) -> Any:
    """Apply an arbitrary function of one argument to the object bound to a name in a given shelve file
    :param func: Callable One-argument function to apply to item
    :param storage_name: str Name of :code:`shelve` file to open
    :param path: str Path to :code:`shelve` storage file
    :param confirm_prompt: str String giving prompt to show the user before invoking
    the function. If :code:`None` (default), ignored
    :rtype Any: The result of calling the function
    """
    path = f"{storage_path()}" if path is None else path
    if not exists(path):
        raise FileNotFoundError(f"{path!r} does not exist")
    with shelve.open(path) as f:
        if storage_name is not None and not f.get(storage_name):
            raise KeyError(f"{storage_name!r} is not a valid key for {path!r}")
        # Bail out if confirmation specified and no confirmation given, or not in interactive mode
        if confirm_prompt is not None:
            if not is_interactive():
                return
            elif input(confirm_prompt) != "":
                print("Aborting")
                return
        return func(f)


# https://stackoverflow.com/questions/2024566/how-to-access-outer-class-from-an-inner-class
class StandardCommandFactory:
    """Creates a Click command that inherits arguments from another command"""
    def configure(self, commands : Union[List, None] = None) -> None:
        """
        Add commands to an instance
        :param commands: List List of commands to add
        """
        commands = [] if commands is None else commands
        self.commands = commands
        __class__.StandardCommand.included_params = self.commands

    def create(self) -> "StandardCommandFactory.StandardCommand":
        return __class__.StandardCommand


    class StandardCommand(click.Command):
        included_params = []
        def __init__(self, *args, **kwargs) -> None:
            super().__init__(*args, **kwargs)
            self.params.extend(__class__.included_params)


def sum_DayLogs(
    record: dict,
    start_date: Union[datetime.date, str] = datetime.date.min,
    end_date: Union[datetime.date, str] = datetime.date.max,
    aggregate: TimeAggregate.TimeAggregate = TimeAggregate.Day,
) -> Dict[str, float]:
    """
    Given a dict of :code:`DayLog` objects, summarizes hours spent at the
    specified level of aggregation.

    :param start_date: Union[datetime.date, str] Earliest date to include (inclusive)
    :param end_date: Union[datetime.date, str] Latest date to include (inclusive)
    :param aggregate: TimeAggregate.TimeAggregate Level of aggregation to use.
    Defaults to days; weeks, months, and years are also built-in.
    :rtype Dict[str, float]: Dict pairing each datestamp within the aggregation
    period to the number of hours worked.
    """
    start_date = handle_date_arg(start_date)
    end_date = handle_date_arg(end_date)
    out = {}

    # Ensure that lowest and highest found date are ultimately recorded
    min_date = datetime.date.max
    max_date = datetime.date.min

    for datestamp, daylog in record.items():
        this_date = aggregate.floor(datetime.date.fromisoformat(datestamp))
        # Skip if date not in range
        if start_date <= this_date < end_date:
            min_date = min(this_date, min_date)
            max_date = max(this_date, max_date)
            key = datetime.date.strftime(this_date, aggregate.string_format.format)
            out[key] = out.get(key, 0) + daylog.sum_time_intervals()
    cur_date = min_date

    # Fill in omitted dates
    if len(out) > 0:
        while cur_date < max_date:
            key = datetime.date.strftime(cur_date, aggregate.string_format.format)
            out[key] = out.get(key, 0)
            cur_date = aggregate.increment(cur_date)

    # Put in sorted order
    return {datestamp : daylog for datestamp, daylog in sorted(out.items(), key = lambda kv: kv[0])}


# Credit https://stackoverflow.com/questions/2356399/tell-if-python-is-in-interactive-mode
def is_interactive() -> bool:
    """Returns whether Python is running in interactive mode"""
    return hasattr(sys, "ps1")


def handle_date_arg(
    date: Union[datetime.date, str, None], default: Any = None, allow_None=False
) -> Any:
    """
    Converts a string to :code:`datetime.date` and optionally raises an error if
    it is :code:`None`

    :param date: Union[datetime.date, str, None] Argument to process
    :param default: Any Default value to return if :code:`allow_None = True`
    and :code:`date is None`.
    :allow_None: bool Logical determining whether to substitute a default if
    :code:`date is None` instead of raising an error.
    :rtype Any: The value returned by the above logic
    """

    if isinstance(date, str):
        date = datetime.date.fromisoformat(date)
    elif date is None:
        if allow_None:
            date = default
        else:
            raise ValueError(f"{None!r} not allowed as a date value")
    return date

# Replace (or set) a path's extension
def add_extension(path : str, extension : str) -> str:
    """Replaces or sets a path's extension
    :param path: str Some file path, optionally with leading directories
    :param extension: str Extension to add

    :rtype str: The path with the extension added
    """
    stem, basename = split(path)
    return join(stem, splitext(basename)[0]) + extension
