import datetime
import json
import os
import re
import subprocess
import sys
from contextlib import redirect_stdout
from io import StringIO

import pytest

from timesheet import Timesheet
from timesheet import constants

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "Timesheet"))


class Helpers:
    """See https://stackoverflow.com/questions/33508060/crjsonify-and-import-helper-functions-in-tests-without-creating-packages-in-test-di for this hack"""



    DiffTime = Timesheet.DiffTime
    DayLog = Timesheet.DayLog
    Timesheet = Timesheet.Timesheet
    bare_DiffTime = DiffTime(1, 2, 3, 1000)
    bare_DayLog = DayLog()
    bare_Timesheet = Timesheet(save=False)
    timestamps = [
        datetime.time(0, 0, 0, 0),
        datetime.time(1, 0, 0, 0),
        datetime.time(1, 0, 1, 0),
        datetime.time(2, 1, 1, 1),
    ]
    extra_timestamps = [ 
            datetime.time(3, 0, 0 ,0), 
            datetime.time(23, 59, 59, 999)]
    # Result of summarizing wee
    expected_day_times = {
            "2022-06-27": 1.5,
            "2022-06-28": 0,
            "2022-06-29": 5 / 6,
            "2022-06-30": 0,
            "2022-07-01": 0,
            "2022-07-02": 0,
            "2022-07-03": 0,
        }
    daylog_data = {
        "2022-06-27": DayLog(
            timestamps=[
                datetime.time(hour=2),
                datetime.time(hour=3),
                datetime.time(hour=7, minute=30),
                datetime.time(hour=8),
            ]
        ),
        "2022-06-29": DayLog(
            timestamps=[datetime.time(hour=0, minute=10), datetime.time(hour=1)]
        ),
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
        # for k in data.values():
        #    print(k)
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
    def example_summarize(timesheet : "Timesheet", write_json = False) -> list:
        """Get a list of summaries of the same week, called with varying arguments"""
        method = "write_json_summary" if write_json else "summarize"
        return [timesheet.summarize(
            date=datetime.date(
                year=2022, month=6 + (i + 27 > 30), day=(27 + i) % 31 + (i + 27 > 30)
            )
        )
        for i in range(constants.DAYS_IN_WEEK)
        ]
@pytest.fixture
def helpers():
    return Helpers

