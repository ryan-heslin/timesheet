import json
import os
from os.path import exists
import re
import datetime

import pytest

ts = "./.venv/bin/timesheet"
date = datetime.date.today().isoformat()



def test_timesheet_installed():
    assert os.path.exists(ts)


def test_create_Timesheet(helpers, tmp_path):
    """Create empty timesheet"""
    path, __ = helpers.make_paths(tmp_path, "test", "test.json")
    os.system(f"{ts} create --storage_path {path}")
    instance = os.system(f"{ts} locate-timesheet --storage_path {path}")
    #assert len(instance) == 1 and len(instance.data.values()) == 1



def test_jsonify(helpers, tmp_path):
    path, json_path = helpers.make_paths(tmp_path, "test", "test.json")
    os.system(
        f"{ts} create --json_path {json_path} --storage_path {path} --storage_name test"
    )
    os.system(f"{ts} jsonify test --json_path {json_path} --storage_path {path}")
    os.system(
        f"{ts} create --json_source {json_path}  --storage_name test2 --storage_path {path}2"
    )
    first = helpers.Timesheet.load(storage_name="test", storage_path=path).record
    second = helpers.Timesheet.load(
        storage_name="test2", storage_path=f"{path}2"
    ).record
    assert all(first[k].timestamps == second[k].timestamps for k in first)


def test_delete(helpers, tmp_path):
    path, __ = helpers.make_paths(tmp_path, "test", "test.json")
    os.system(f"{ts} create --storage_path {path}")
    os.system(f"{ts} delete --storage_path {path} --storage_name timesheet1")
    try:
     os.system(f"{ts} locate_timesheet --storage_name timesheet1 --storage_path {path}")
    except KeyError: 
        return True 
    except Exception as e: 
        raise e

def test_list(helpers, tmp_path):
    storage_names = { f"test{i}" for i in range(1, 6) }
    path= helpers.test_path(tmp_path,"test")
    for name in storage_names:
        os.system(f"{ts} create --storage_path {path} --storage_name {name}")
    assert { x.group(0) for x in re.finditer(r"test\d",helpers.capture_stdout(f"{ts} list --storage_path {path}")) } == storage_names

def test_append_fresh_date(helpers, tmp_path):
    timestamps = helpers.timestamps
    path = helpers.test_path(tmp_path, "test")
    os.system(f"{ts} create --storage_path {path}")
    strings = " -t ".join(datetime.time.isoformat(ts) for ts in timestamps)
    os.system(f"{ts} append -t {strings} --storage_name timesheet1 --date {date} --storage_path {path}")
    instance = helpers.Timesheet.load(storage_name = "timesheet1", storage_path = path)
    assert instance[date].timestamps == timestamps
    
def test_append_old_date(helpers, tmp_path):
    """Add more timestamps to existing entry"""
    timestamps = helpers.timestamps.copy()
    path = helpers.test_path(tmp_path, "test")
    os.system(f"{ts} create --storage_path {path}")
    strings = helpers.timestamps_to_strings(timestamps)
    os.system(f"{ts} append -t {strings} --storage_name timesheet1 --date {date} --storage_path {path}")
    extra_timestamps = helpers.extra_timestamps
    extra_strings = helpers.timestamps_to_strings(extra_timestamps)
    os.system(f"{ts} append -t {extra_strings} --storage_name timesheet1 --date {date} --storage_path {path}")
    instance = helpers.Timesheet.load(storage_name = "timesheet1", storage_path = path)
    assert instance[date].timestamps == timestamps+ extra_timestamps

    # Test for all days in week

