import datetime
import json
import os
import re
import subprocess
from typing import Generator, Dict

import pytest

from timesheet import Timesheet
from timesheet import constants

class Helpers:
    """See https://stackoverflow.com/questions/33508060/crjsonify-and-import-helper-functions-in-tests-without-creating-packages-in-test-di for this hack"""

    # Classes for convenience
    ts =  "./.venv/bin/timesheet"
    TimeAggregate = Timesheet.TimeAggregate
    DiffTime = Timesheet.DiffTime
    DayLog = Timesheet.DayLog
    Timesheet = Timesheet.Timesheet

    bare_DiffTime = DiffTime(1, 2, 3, 1000)
    bare_DayLog = DayLog()
    bare_Timesheet = Timesheet(save=False)
    
    # Example timestamps
    timestamps = [
        datetime.time(0, 0, 0, 0),
        datetime.time(1, 0, 0, 0),
        datetime.time(1, 0, 1, 0),
        datetime.time(2, 1, 1, 1),
    ]
    extra_timestamps = [ 
            datetime.time(3, 0, 0 ,0), 
            datetime.time(23, 59, 59, 999)]
    # Result of summarizing week
    expected_day_times = {
            "2022-06-27": 1.5,
            "2022-06-28": 0,
            "2022-06-29": 5 / 6,
            "2022-06-30": 0,
            "2022-07-01": 0,
            "2022-07-02": 0,
            "2022-07-03": 12,
        }
    expected_start = datetime.date.fromisoformat(next(iter(expected_day_times.keys())))
    expected_end = datetime.date.fromisoformat(max(expected_day_times.keys()))
    daylog_data = {
        "2022-06-27": DayLog(
            date = "2022-06-27",
            timestamps=[
                datetime.time(hour=2),
                datetime.time(hour=3),
                datetime.time(hour=7, minute=30),
                datetime.time(hour=8),
            ]
        ),
        "2022-06-29": DayLog(
            date = "2022-06-29",
            timestamps=[datetime.time(hour=0, minute=10), datetime.time(hour=1)]
        ),
        "2022-06-30" : DayLog(date = "2022-06-30", timestamps = []), 
        "2022-07-03" : DayLog(date = "2022-07-03", timestamps = [datetime.time(hour = hour) for hour in range(1, 24, 2) ])
    }
    # Extra set of data with no common keys
    @staticmethod
    def alternate_daylog_data(month : int) -> Dict[str, "DayLog"]:
        return {
        datetime.date.isoformat(datetime.date(year = 2022, month = 1, day = i + 1)): __class__.DayLog(
            timestamps=[datetime.time(hour=3, second=20)]
        )
        for i in range(len(__class__.daylog_data))
    }

    @staticmethod
    def full_DayLog(timestamps=None):
        timestamps = __class__.timestamps if timestamps is None else timestamps
        return Timesheet.DayLog(timestamps=timestamps)

    @staticmethod
    def full_Timesheet(**kwargs):
        return Timesheet.Timesheet(
            data={"2022-06-19": __class__.full_DayLog()}, **kwargs
        )

    @staticmethod
    def capture_stdout(command):
        return subprocess.run(command.split(), stdout=subprocess.PIPE).stdout.decode(
            "utf-8"
        )

    @staticmethod
    def files_in_directory(directory, files):
        actual = os.listdir(directory)
        assert all(fi in actual for fi in files)

    @staticmethod
    def pattern_in_output(command, pattern):
        result = __class__.capture_stdout(command)
        assert bool(re.search(pattern, result))

    @staticmethod
    def pattern_in_json(path, pattern):
        with open(path) as f:
            data = json.load(f)
        __class__.recurse_dict(data, pattern)

    @staticmethod
    def recurse_dict(di, pattern):
        for v in di.values():
            if v is di:
                __class__.recurse_dict(di, pattern)
            elif v is str:
                assert re.search(pattern, v)

    @staticmethod
    def write_json(path):
        instance = __class__.full_Timesheet(save=False)
        instance.write_json(path=path)
        return instance

    @staticmethod
    def touch(path):
        """Create empty file"""
        open(path, "a").close()

    #TODO coroutine
    @staticmethod 
    def test_path(*args): 
        return "/".join(str(arg) for arg in [*args])

    @staticmethod
    def make_paths(tmp_path, *args):
        #while [*args]:
        return [__class__.test_path(tmp_path, x) for x in [ *args ]]
        #    yield from [__class__.test_path(tmp_path, x) for x in [ *args ]]
    @staticmethod 
    def timestamps_to_strings(timestamps : list ) -> str:
        """Convert list of times to string argument"""
        return " -t ".join(datetime.time.isoformat(ts) for ts in timestamps)
    
    @staticmethod
    def make_dates():
        """Generate a week of fake dates"""
        for date in list(__class__.expected_day_times.keys())[1:]:
            yield date #datetime.date(
                  #          year=2022, month=6 + (i + 27 > 30), day=(27 + i) % 31 + (i + 27 > 30)
                  #      )

    @staticmethod
    def test_summarize(aggregate, expected): 
        test = __class__.Timesheet(data=__class__.daylog_data, save = False)

        assert  all(__class__.dict_subset(test.summarize(aggregate = aggregate), expected))



    @staticmethod
    def example_summarize(timesheet, **kwargs) -> list:
        """Get a list of summaries of the same week, called with varying arguments"""
        return [timesheet.summarize(
           start_date = date,
           end_date =  __class__.expected_end
        )
        for date in __class__.make_dates()
        ]

    @staticmethod 
    def dict_subset(d1 : dict, d2 : dict) -> Generator[bool, None, None]:
        """Checks whether one dict is a subset of another"""
        return(d1[k] == d2[k] for k in d1.keys())
    @staticmethod
    def test_write_summary_command( storage_name : str, storage_path : str, directory : str) -> None:
        """Get a list of summaries of the same week, called with varying arguments"""
        test_paths = [f"{directory}/test{i}" for i in range(7)]
        instance = __class__.Timesheet(data = __class__.daylog_data, storage_path = storage_path, save = True, storage_name=storage_name)
        command_stem = f"{__class__.ts} summarize --storage_name {storage_name} --storage_path {storage_path}"
        # Save summary for each day of week
        for i, date in enumerate(__class__.make_dates()):  
            command = f"{command_stem} --date '{date}' --output_path '{test_paths[i]}'"
            os.system(command)
            with open(test_paths[i]) as f:
                assert json.load(f) == __class__.expected_day_times

@pytest.fixture
def helpers():
    return Helpers
