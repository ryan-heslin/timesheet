import datetime
import enum
from os.path import exists
from os.path import splitext
from typing import List
from typing import Union

import click

from timesheet import constants
from timesheet import TimeAggregate
from timesheet import Timesheet
from timesheet import utils
# Click class for shared arguments
# https://stackoverflow.com/questions/40182157/shared-options-and-flags-between-commands

class Output(enum.Enum):
    CSV = "csv"
    JSON = "json"

@click.group()
def timesheet():
    pass


@click.option("--storage_name", help=constants.HELP_MAP["storage_name"], default=None)
@click.option(
    "--storage_path",
    help=constants.HELP_MAP["storage_path"],
    default=utils.storage_path(),
)
@timesheet.command(name="locate_timesheet")
# Actually loads given timesheet; errors are
# caught in Timesheet.load
def locate_timesheet_impl(storage_name: str, storage_path: str):
    return Timesheet.Timesheet.load(
        storage_name=storage_name, storage_path=storage_path
    )


shared = locate_timesheet_impl.params

factory = utils.StandardCommandFactory()
factory.configure(commands=shared)
locate_timesheet = factory.create()

# @click.option("--storage_name", help=constants.HELP_MAP["storage_name"], default=None)
# @click.argument(
# "--storage_path",
# help=constants.HELP_MAP["storage_path"],
# default=utils.storage_path(),
# )

# )
@click.option(
    "--data_path", help="JSON path attribute of created instance", default=None
)
@click.option("--json_source", help="Path to JSON file from which to load data")
@click.option("--verbose", default=False, is_flag = True, help=constants.HELP_MAP["verbose"])
@click.option("--overwrite", default=False, is_flag = True, help="Overwrite an existing timesheet with the same storage name?")
@timesheet.command(name="create", cls=locate_timesheet)
def create(
        json_source : Union[str, None]=None,
        data_path : Union[str, None]=None,
        storage_path : str =utils.storage_path(),
        storage_name : Union[str, None]=None,
        overwrite : bool=False,
        verbose : bool =False,
):
    # Fail if overwrite would delete data
    if not overwrite and storage_name is not None and storage_name in Timesheet.Timesheet.list(storage_path):
        click.echo(f"{storage_name} is already in use, and overwrite = False")
        return 1
    if json_source is None:
        Timesheet.Timesheet(
            storage_path=storage_path,
            storage_name=storage_name,
            data_path=data_path,
            save=True,
        )
    else:
        Timesheet.Timesheet.from_json(
            json_path=json_source,
            storage_path=storage_path,
            storage_name=storage_name,
            data_path=data_path,
            save=True,
        )
    if verbose:
        click.echo(
            f"Created Timesheet instance named {storage_name} at {storage_path} "
        )
    return 0


@click.option(
    "--timestamps",
    "-t",
    help=constants.HELP_MAP["timestamps"],
    multiple=True,
    default=[],
)
@click.option("--verbose/--silent", help=constants.HELP_MAP["verbose"], default=False)
@click.option("--date", help=constants.HELP_MAP["date"], default=None)
@timesheet.command(name="append", cls=locate_timesheet)
def append(
    storage_name: str,
    storage_path: str,
    timestamps: list = [],
    verbose: bool = False,
    date: Union[datetime.date, None] = None,
):
    date = datetime.date.today() if date is None else date
    if timestamps == []:
        parsed = []
    else:
        parsed = [datetime.time.fromisoformat(x) for x in timestamps]
    instance = Timesheet.Timesheet.load(
        storage_name=storage_name, storage_path=storage_path
    )
    instance.concat_timestamps(date=date, timestamps=parsed)
    if verbose:
        click.echo(f"Added {timestamps!r} to Timesheet {storage_name!r} ")
    return 0

@click.option("--aggregate", help=constants.HELP_MAP["aggregate"],  default="day")
@click.option("--start_date", help=constants.HELP_MAP["start_date"], default=datetime.date.min)
@click.option("--end_date", help=constants.HELP_MAP["end_date"], default=datetime.date.max)
@click.option("--output_path", help=constants.HELP_MAP["output_path"], default=None)
@click.option("--output_type", help = constants.HELP_MAP["output_type"], type = str, default = None)
@timesheet.command(name="summarize", cls=locate_timesheet)
# @click.pass_context
# TODO check if these inherit defaults
def summarize(
    storage_name: str, storage_path: str,  output_path: Union[str, None] = None,
    start_date : Union[str, datetime.date] = datetime.date.min,
    end_date : Union[str, datetime.date] = datetime.date.max,
    aggregate : str = "day",
    output_type = None
):
    # @storage_name.forward(locate_timesheet)
    instance = Timesheet.Timesheet.load(
            storage_name=storage_name, storage_path=storage_path
        )
    if output_path is None:
        if instance.output_path is None:
            raise ValueError("Must specify an output path if instance has no default")
        output_path = instance.output_path


    if output_type is None:
        output_type = splitext(output_path)[-1]
    try:
        output_type = Output[output_type.lstrip(".").upper()]
    except KeyError:
        output_type = Output.JSON

    try:
        # Get appropriate aggregate object
        aggregate_value : TimeAggregate.TimeAggregate = TimeAggregate.__dict__[aggregate.title() ]
    except KeyError as e:
        click.echo(f"Invalid aggregate {aggregate}; must choose one of 'day', 'week', 'month', or 'year'")
        raise e

    if output_type == Output.JSON:
        instance.write_json_summary(output_path=output_path, start_date = start_date, end_date=end_date, aggregate = aggregate_value)
    else:
        instance.write_csv_summary(output_path=output_path, start_date = start_date, end_date=end_date, aggregate = aggregate_value)
    return 0


#@timesheet.command()
#@click.argument("storage_name", required=1)
#@click.option(
#    "--storage_path",
#    help=constants.HELP_MAP["storage_path"],
#    default=utils.storage_path(),
#)
@click.option("--data_path", help="Path to JSON output", default=None)
@timesheet.command(name="jsonify", cls=locate_timesheet)
def jsonify(storage_name : str, storage_path : str =utils.storage_path(), data_path : Union[str, None]=None):
    instance = Timesheet.Timesheet.load(storage_name, storage_path)
    instance.write_json(path=data_path)
    return 0

@click.option("--force", help="Delete without requiring user confirmation", default=False, is_flag = True)
@timesheet.command(name="delete", cls=locate_timesheet)
def delete(storage_name : str, storage_path : str, force : bool=False):
    Timesheet.Timesheet.delete(storage_name=storage_name, storage_path = storage_path, confirm = not force)


# Show saved timesheets
@timesheet.command()
@click.option(
    "--storage_path",
    default=utils.storage_path(),
    help=constants.HELP_MAP["storage_path"],
)
def list(storage_path : str =utils.storage_path()) -> dict[str, Timesheet.Timesheet]:
    if not exists(storage_path):
        click.echo(f"{storage_path} does not exist")
        return {}
    f = utils.use_shelve_file(
        func=lambda f: {k: v for k, v in f.items() if isinstance(v, Timesheet.Timesheet)}, path=storage_path
    )
    for k, v in f.items():
        click.echo(f"{k}:")
        click.echo(v)
    return f

# https://click.palletsprojects.com/en/5.x/arguments/# Recommends "graceful no-op" if varaidic arg is empty, so `timesheets` is optional despite conceptually being mandatory
@click.option("--timesheets", multiple = True,
        help = "One or more timesheets, each preceded by this flag and in the format {storage_name}={storage_path}", default = [])
@click.option("--storage_path", help = f"{constants.HELP_MAP['storage_path']} (assigned to output object)" , default = utils.storage_path())
@click.option("--storage_name", help = f"{constants.HELP_MAP['storage_name']} (assigned to output object)", default = None)
@click.option("--data_path", help = f"{constants.HELP_MAP['data_path']} (assigned to output object)", default = None)
@timesheet.command(name = "merge")
def merge(timesheets : List[str] = [],
        data_path : Union[str, None] = None,
        storage_path : str =utils.storage_path(),
        storage_name : Union[str, None] = None,
        verbose : bool =False,
):
    loaded_timesheets = [ Timesheet.Timesheet.load(*string.split("=")) for string in timesheets]
    # Merge each timesheet in sequence with original
    # Only need to save final version, to avoid side effects
    if loaded_timesheets == []:
        return None
    n_timesheets = len(loaded_timesheets)
    while len(loaded_timesheets) > 1:
        loaded_timesheets[0].merge(loaded_timesheets.pop(1), save = False)
    combined = loaded_timesheets.pop().copy()

    # Set output names as requested
    combined.storage_name = storage_name
    combined.storage_path = storage_path
    combined.data_path = data_path

    # Save output - this does work when run interactively
    combined.save(create_directory = True, overwrite=True)
    if verbose:
        click.echo(f"Merged {n_timesheets}(s) into  {combined.storage_name} at {combined.storage_path}")

    return 0
