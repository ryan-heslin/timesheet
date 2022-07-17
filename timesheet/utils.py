import datetime
import re
import shelve
import sys
from glob import glob
from os import getcwd
from os import listdir
from os.path import exists
from typing import Any

import click

from timesheet import constants
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
    # breakpoint()
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
        if is_interactive() and confirm_prompt is not None:
            if input(confirm_prompt) != "":
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

# Credit https://stackoverflow.com/questions/2356399/tell-if-python-is-in-interactive-mode
def is_interactive(): 
    return hasattr(sys, "ps1")
