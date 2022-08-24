import datetime
import re
import shelve
import sys
from glob import glob
from os import getcwd
from os import listdir
from os.path import exists
from typing import Any
from typing import Union

import click

from timesheet import constants
from timesheet import TimeAggregate
from timesheet import Timesheet


# From https://stackoverflow.com/questions/11875770/how-to-overcome-datetime-datetime-not-json-serializable
def json_serialize(x):

    if isinstance(x, (datetime.datetime, datetime.time)):
        return x.isoformat()
    elif isinstance(x, Timesheet.DayLog):
        return x.timestamps
    raise TypeError(f"Cannot serialize object of type {type(x)}")


def date_parser(di):
    """Parses a JSON where keys are ISO-formatted dates and values are lists of ISO-formatted times to be converted to DiffTime objects"""
    out = {}
    for k in di:
        date = datetime.date.fromisoformat(k)
        timestamps = [Timesheet.DiffTime.fromisoformat(ts) for ts in di[k]]
        out[k] = Timesheet.DayLog(date=date, timestamps=timestamps)
    return out


def next_number(stem, names):
    if names == []:
        return 1
    pattern = stem + r"(\d+)\.?.*$"
    numbers = [0]
    for name in names:
        number = re.match(pattern, name)
        if number is not None:
            # If somehow a number is negative
            numbers.append(abs(int(number.group(1))))
    return max(numbers) + 1


# storage_name ignored if None
def use_shelve_file(
    func, storage_name: str = None, path: str = None, confirm_prompt: str = None
) -> Any:
    path = f"{constants.STORAGE_PATH}" if path is None else path
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
    def configure(self, commands=None) -> None:
        commands = [] if commands is None else commands
        self.commands = commands
        # self.update_commands(commands)
        __class__.StandardCommand.included_params = self.commands

    def create(self) -> "StandardCommandFactory.StandardCommand":
        return __class__.StandardCommand

    # def update_commands(self, commands):
    #    self.commands = commands

    class StandardCommand(click.Command):
        included_params = []

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.params.extend(__class__.included_params)


def sum_DayLogs(
    record: dict,
    start_date : Union[datetime.date, str] = datetime.date.min,
    end_date: Union[datetime.date, str] = datetime.date.max,
    aggregate: TimeAggregate.TimeAggregate = TimeAggregate.Day,
) -> dict:
    start_date = handle_date_arg(start_date)
    end_date = handle_date_arg(end_date)
    out = {}

    # Ensure that lowest and highest found date are ultimately recorded
    min_date = datetime.date.max
    max_date = datetime.date.min

    for datestamp, daylog in record.items():
        this_date = aggregate.floor(datetime.date.fromisoformat(datestamp))
        # Skip if date not in range
        if start_date  <= this_date < end_date:
            min_date = min(this_date, min_date)
            max_date = max(this_date, max_date)
            key = datetime.date.strftime(this_date, aggregate.string_format)
            out[key] = out.get(key, 0) + daylog.sum_time_intervals()
    cur_date = min_date

    # Fill in omitted dates
    # TODO make this optional
    if len(out) > 0:
        while cur_date < max_date: 
            key = datetime.date.strftime(cur_date, aggregate.string_format)
            out[key] = out.get(key, 0) 
            cur_date = aggregate.increment(cur_date)

    return out 
    
#dates = sorted(
        #[
            #(datetime.date.fromisoformat(datestamp), DL)
            #for datestamp, DL in record.items()
        #],
        #key=lambda x: x[0],
    #)
    #out = {}
#
    ## Default to earliest and latest recorded dates if not provided or
    ## if either beyond range
    ## Clamp dates to granularity of interval
    #start_date = (
        #dates[0][0] if start_date is None or start_date < dates[0][0] else start_date
    #)
    #end_date = (
            #dates[-1][0]
        #if end_date is None or end_date > dates[-1][0]
        #else end_date
    #)
#
    ## Illegal, since interval desired, not point
    #if start_date == end_date:
        #raise ValueError("Start and end dates must be different")
#
    ## Initialize values for loop start, truncating to aggregate granularity
    #cur_lower = aggregate.floor(start_date)
    #cur_upper = aggregate.increment(cur_lower)
    #cur_key = datetime.date.strftime(cur_lower, aggregate.string_format)
#
    #while dates and cur_lower <= dates[-1][0]:
#
        ## Explicitly indicate when zero hours recorded if no time recorded
        ## Key is always lower bound of interval
        #out[cur_key] = 0
        ## Count all dates in [cur_lower, cur_upper) 
        ## i.e., closed on left, open on right
        #while dates and cur_lower <= dates[0][0] < cur_upper <= end_date:
            #out[cur_key] += dates.pop(0)[1].sum_time_intervals()
#
        ## Advance for next iteration
        #cur_lower = cur_upper
        #cur_upper = aggregate.increment(cur_upper)
        #cur_key = datetime.date.strftime(cur_lower, aggregate.string_format)
#
    #return out


# Credit https://stackoverflow.com/questions/2356399/tell-if-python-is-in-interactive-mode
def is_interactive():
    return hasattr(sys, "ps1")


def handle_date_arg(date: Union[datetime.date, str, None], default: Any = None, allow_None = False) -> datetime.date:
    if isinstance(date, str):
        date = datetime.date.fromisoformat(date)
    elif date is None:
        if allow_None:
            date = default
        else: 
            raise ValueError(f"{None!r} not allowed as a date value")
    return date

