import datetime

# Commands help
HELP_MAP = {
    "storage_path": "Path to shelve file where Timesheet instance is stored",
    "data_path" : "Directory to which to write JSON or CSV summaries of this instance",
    "json_path": "Default path to write JSON representation of this instance",
    "storage_name": "Name identifying instance in shelve dict",
    "timestamps": "Sequence of ISO-formatted timestamps in chronological order to enter in the created object",
    "date": "Target date, as a string in ISO format (e.g., 2022-06-27)",
    "confirm": "Require user confirmation before executing the command",
    "verbose": "Print a description of command's outcome",
"aggregate" : "Level of aggregation to choose (day, week, month, or year)",
"start_date" : "Date on which to start aggregation (inclusive)",
"end_date" : "Date on which to end aggregation (exclusive)",
"output_path" : "Path to output JSON",
"output_type" :  "Type of summary to create, 'csv' or 'json'. If omitted, inferred from the file extension of `output_path`, defaulting to 'json' if the extension is missing or nonstandard"
}

DAYS_IN_WEEK = 7
MONTHS_IN_YEAR = 12
EARLIEST_DATE= datetime.date(1, 1, 1)
