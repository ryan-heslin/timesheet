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
from typing import Iterable
from typing import List
from typing import Union

import click


def path_checker(permissions : int) -> Callable:
    """Create function to check whether a user has specified permissions to use a path

    :param permissions: One or more :code:`os` permission codes to check for (e.g., :code:`os.W_OK | os.X_OK` )
    :type permissions: int

    :return: Function with :code:`bool` return type that checks whether
    the user has the given permissions for some path
    :rtype: Callable
    """
    def inner(path : str):
        return os.access(path, permissions)
    return inner

path_readable = path_checker((os.R_OK))
path_writeable = path_checker(os.W_OK | os.X_OK)



def validate_datestamps(datestamps: Iterable[str]) -> bool:
    """Confirms whether all datestamps in an iterable parse in ISO format

    :param datestamps Iterable[str]: Iterable of date strings whose formats to check
    :type datestamps: Iterable[str]
    :return: :code:`bool` indicating whether all datestamps were valid
    :rtype: bool
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

    :return: The path found.
    :rtype: str
    """
    return getenv("TIMESHEET_DIR", expanduser("~/.timesheet/timesheets"))


def next_number(stem : str, names : List[str]) -> int:
    """
    Given a list of strings and a stem, finds all that start with the stem and
    end with digits and returns the highest such number plus one.
    :param stem: Filename to check for
    :type stem: str
    :param names: Strings to check for any starting with the stem and ending
    :type names: List[str]
    with a  number
    :return: The next sequential number, starting from 1.
    :rtype int:
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
        path: Union[str, None] = None,
        confirm_prompt: Union[str, None] = None
) -> Any:
    """Apply an arbitrary function of one argument to the object bound to a name in a given shelve file
    :param func: One-argument function to apply to item
    :type func: Callable
    :param storage_name: Name of :code:`shelve` file to open
    :type storage_name: str , optional
    :param path: str Path to :code:`shelve` storage file
    :type path: str, optional
    :param confirm_prompt: String giving prompt to show the user before invoking
    :type confirm_prompt: str, optional
    the function. If :code:`None` (default), ignored
    :return: The result of calling the function
    :rtype: Any
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
        :param commands: List of commands to add
        :type commands: Union[List, None]
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





# Credit https://stackoverflow.com/questions/2356399/tell-if-python-is-in-interactive-mode
def is_interactive() -> bool:
    """
    :return: :code:`True` if Python is running in interactive mode, :code:`False` otherwise
    :rtype: bool
    """
    return hasattr(sys, "ps1")


def handle_date_arg(
    date: Union[datetime.date, str, None], default: Any = None, allow_None=False
) -> Any:
    """
    Converts a string to :code:`datetime.date` and optionally raises an error if
    it is :code:`None`

    :param date:  Argument to process
    :type  date: Union[datetime.date, str, None]
    :param default: Default value to return if :code:`allow_None = True`
    :type  default: Any, optional
    and :code:`date is None`.
    :allow_None: bool Logical determining whether to substitute a default if
    :code:`date is None` instead of raising an error.
    :type allow_None: bool, optional
    :return: The value returned by the above logic
    :rtype: Any
    """

    if isinstance(date, str):
        date = datetime.date.fromisoformat(date)
    elif date is None:
        if allow_None:
            date = default
        else:
            raise ValueError(f"{None!r} not allowed as a date value")
    return date

def add_extension(path : str, extension : str) -> str:
    """Replaces or sets a path's extension

    :param path: Some file path, optionally with leading directories
    :type path: str
    :param extension: Extension to add
    :type extension: str
    :return: The path with the extension added
    :rtype: str
    """
    stem, basename = split(path)
    return join(stem, splitext(basename)[0]) + extension
