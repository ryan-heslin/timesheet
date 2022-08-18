from os.path import expanduser

STORAGE_PATH = expanduser("~/.timesheet/timesheets")

HELP_MAP = {
    "storage_path": "Path to shelve file where Timesheet instance is stored",
    "json_path": "Default path to write JSON representation of this instance",
    "storage_name": "Name identifying instance in shelve dict",
    "timestamps": "Sequence of ISO-formatted timestamps in chronological order to enter in the created object",
    "date": "Target date, as a string in ISO format (e.g., 2022-06-27)",
    "confirm": "Require user confirmation before executing the command",
    "verbose": "Print a description of command's outcome",
}

DAYS_IN_WEEK = 7
MONTHS_IN_YEAR = 12
