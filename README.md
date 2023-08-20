`timesheet` is a command-line application that tracks and records time spent on tasks.
It is intended to track time spent working, a useful capability for anyone paid
by the hour. Times are recorded as intervals of start and stop times.

You can install `timesheet` with:

```sh
python3 -m pip install --index-url https://test.pypi.org/simple/ timesheet
```

`timesheet` is used by invoking `timesheet` on the command
line with the appropriate subcommand. Subcommands implement
the application's functions and are individually documented.

Enter `timesheet --help` for a list of all subcommands, or `timesheet {{subcommand}} --help` to view the help for a specific subcommand.

`Timesheet` objects are used to record time intervals. The class
stores a record of time intervals mapped to dates, and can produce
JSON or `.csv` summaries of time worked across different intervals (day, week, month, etc.)

A timesheet can be created with:

```sh
timesheet create --storage_name my_timesheet
```

By default, it is stored in a `shelve` file in `~/.timesheet/`.

You can add one or more timestamps to a given day using the `append` subcommand.
By default, it adds the current system time to the record for the current system day:

```sh
timesheet append --storage_name my_timesheet
```

`timesheet list` can be used to print information about each Timesheet object
stored in a particular location:

```sh
timesheet list
```


You can create a JSON or `.csv` record of a Timesheet object using
`timesheet summarize`:

```sh
timesheet summarize --storage_name my_timesheet --output_path ./summary.csv


The Timesheet itself can be converted to a `JSON` representation using `timesheet jsonify`:

```sh
timesheet jsonify --storage_name my_timesheet --data_path ./timesheet.json
```
By default, it sums recorded time intervals for each day between the object's
earliest and latest recorded dates, inclusive. You can also aggregate by
week, month, or year:


```sh
timesheet summarize --storage_name my_timesheet --output_path ./summary.csv --aggregate week
```


You can use the `merge` subcommand to combine two Timesheet objects.

```sh
timesheet create --storage_name my_timesheet
timesheet create --storage_name another_timesheet
timesheet append --storage_name my_timesheet
timesheet append --storage_name my_timesheet
timesheet append --storage_name another_timesheet --date 2023-01-01 --timestamps 10:00:00 11:00:00
timesheet merge --timesheets my_timesheet --timesheets another_timesheet --storage_name combined_timesheet
```

Finally, you can delete timesheets like so:

```sh
timesheet delete --storage_name my_timesheet
```

# Acknowledgements

Docs built with [Sphinx](https://www.sphinx-doc.org/). Project built with [Poetry](https://python-poetry.org/).
Deployment action taken from [https://tomasfarias.dev/posts/sphinx-docs-with-poetry-and-github-pages/#specifying-the-dependencies-in-poetry](https://tomasfarias.dev/posts/sphinx-docs-with-poetry-and-github-pages/#specifying-the-dependencies-in-poetry).
