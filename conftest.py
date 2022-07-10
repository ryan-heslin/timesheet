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


@pytest.fixture
def helpers():
    return Helpers
