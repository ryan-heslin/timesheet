import datetime
import click
from typing import Union

from timesheet import constants
from timesheet import Timesheet
from timesheet import utils
from timesheet import TimeAggregate

# Click class for shared arguments
# https://stackoverflow.com/questions/40182157/shared-options-and-flags-between-commands


@click.group()
def timesheet():
    pass


@click.option("--storage_name", help=constants.HELP_MAP["storage_name"], default=None)
@click.option(
    "--storage_path",
    help=constants.HELP_MAP["storage_path"],
    default=constants.STORAGE_PATH,
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
# default=constants.STORAGE_PATH,
# )

# )
@click.option(
    "--json_path", help="JSON path attribute of created instance", default=None
)
@click.option("--json_source", help="Path to JSON file from which to load data")
@click.option("--verbose", default=False, help=constants.HELP_MAP["verbose"])
@timesheet.command(name="create", cls=locate_timesheet)
def create(
    json_source=None,
    json_path=None,
    storage_path=constants.STORAGE_PATH,
    storage_name=None,
    verbose=False,
):
    if json_source is None:
        Timesheet.Timesheet(
            storage_path=storage_path,
            storage_name=storage_name,
            json_path=json_path,
            save=True,
        )
    else:
        Timesheet.Timesheet.from_json(
            path=json_source,
            storage_path=storage_path,
            storage_name=storage_name,
            json_path=json_path,
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
    timestamps: list = [str],
    verbose: bool = False,
    date: datetime.date = None,
):
    date = datetime.date.today() if date is None else date
    if timestamps == []:
        parsed = None
    else:
        parsed = [datetime.time.fromisoformat(x) for x in timestamps]
    instance = Timesheet.Timesheet.load(
        storage_name=storage_name, storage_path=storage_path
    )
    instance.concat_timestamps(date=date, timestamps=parsed)
    if verbose:
        click.echo(f"Added {timestamps!r} to Timesheet {storage_name!r} ")
    return 0



@click.option("--aggregate", help="Level of aggregation to choose (day, week, month, or year)", default="day")
@click.option("--start_date", help="Date on which to start aggregation (inclusive)", default=datetime.date.min)
@click.option("--end_date", help="Date on which to end aggregation (exclusive)", default=datetime.date.max)
@click.option("--output_path", help="Path to output JSON", default=None)
@timesheet.command(name="summarize", cls=locate_timesheet)
# @click.pass_context
# TODO check if these inherit defaults
def summarize(
    storage_name: str, storage_path: str,  output_path: str = None, 
    start_date : Union[str, datetime.date] = datetime.date.min, 
    end_date : Union[str, datetime.date] = datetime.date.max, 
    aggregate : str = "day"
):
    # @storage_name.forward(locate_timesheet)
    instance = Timesheet.Timesheet.load(
            storage_name=storage_name, storage_path=storage_path
        )
   
    try:
        # Get appropriate aggregate object
        aggregate = TimeAggregate.__dict__[aggregate.title() ]
    except KeyError as e: 
        print(f"Invalid aggregate {aggregate}; must choose one of 'day', 'week', 'month', or 'year'")
        raise e


    if output_path is None:
        instance.summarize(start_date = start_date, end_date=end_date, aggregate = aggregate)
    else:
        instance.write_json_summary(json_path=output_path, start_date = start_date, end_date=end_date, aggregate = aggregate)


@timesheet.command()
@click.argument("storage_name", required=1)
@click.option(
    "--storage_path",
    help=constants.HELP_MAP["storage_path"],
    default=constants.STORAGE_PATH,
)
@click.option("--json_path", help="Path to JSON output", default=None)
# @timesheet.command(name="jsonify", cls=locate_timesheet)
def jsonify(storage_name, storage_path=constants.STORAGE_PATH, json_path=None):
    instance = Timesheet.Timesheet.load(storage_name, storage_path)
    instance.write_json(path=json_path)
    return 0


@click.option("--force", help="Delete without requiring user confirmation", default=False, is_flag = True)
@timesheet.command(name="delete", cls=locate_timesheet)
def delete(storage_name, storage_path, force=False):
    Timesheet.Timesheet.delete(storage_name=storage_name, storage_path = storage_path, confirm = not force)


# Show saved timesheets
@timesheet.command()
@click.option(
    "--storage_path",
    default=constants.STORAGE_PATH,
    help=constants.HELP_MAP["storage_path"],
)
def list(storage_path : str =constants.STORAGE_PATH) -> dict:
    f = utils.use_shelve_file(
        func=lambda f: {k: v for k, v in f.items()}, path=storage_path
    )
    for k, v in f.items():
        print(f"{k}:")
        print(v)
    return f
