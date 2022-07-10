import click

from timesheet import constants
from timesheet import Timesheet
from timesheet import utils

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
def locate_timesheet_impl(storage_name, storage_path):
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
# @click.argument("--storage_name", help="Name to use for object in shelve storage")
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

@click.option("--verbose/--silent", help=constants.HELP_MAP["verbose"], default=False)
@click.option("--timestamps", help=constants.HELP_MAP["timestamps"], default=[])
@timesheet.command(name="append", cls=locate_timesheet)
def append(storage_name, storage_path, timestamps, verbose=False):
    instance = Timesheet.Timesheet.load(storage_name=storage_name, storage_path=storage_path)
    instance.add_timestamps(timestamps)
    if verbose:
        click.echo(f"Added {timestamps!r} to Timesheet {storage_name} ")
    return 0


@click.option(("--date"), help=constants.HELP_MAP["date"], default=None)
@timesheet.command(name="summarize", cls=locate_timesheet)
# TODO check if these inherit defaults
def summarize(storage_name, storage_path, date=None):
    instance = locate_timesheet_impl(
        storage_name=storage_name, storage_path=storage_path
    )
    instance.summarize_week(date=date)


@timesheet.command()
@click.argument("storage_name", required = 1)
@click.option(
    "--storage_path",
    help=constants.HELP_MAP["storage_path"],
    default=constants.STORAGE_PATH,
    )
@click.option("--json_path", help="Path to JSON output", default = None)
#@timesheet.command(name="jsonify", cls=locate_timesheet)
def jsonify(storage_name, storage_path = constants.STORAGE_PATH, json_path = None):
    instance = Timesheet.Timesheet.load(
        storage_name, storage_path
    )
    instance.write_json(path=json_path)
    return 0


@click.option("--confirm", help=constants.HELP_MAP["confirm"], default=True)
@timesheet.command(name="delete", cls=locate_timesheet)
def delete(storage_name, storage_path):
    instance = Timesheet.Timesheet.load(storage_name=storage_name, storage_path=storage_path)
    Timesheet.Timesheet.delete(storage_name=storage_name, path=storage_path)


# Show saved timesheets
@timesheet.command()
@click.option("--storage_path", default =  constants.STORAGE_PATH, help = constants.HELP_MAP["storage_path"])
def list(storage_path = constants.STORAGE_PATH): 
    f = utils.use_shelve_file(func = lambda f: f, path = storage_path)
    for k, v in f.items(): 
        print(f"{k}:")
        print(v)
# Delete selected timesheet
# Storage name
# Storage path

# timesheet.add_command(create)
# timesheet.add_command(summarize)
# timesheet.add_command(append)
# timesheet.add_command(delete)
# timesheet()
