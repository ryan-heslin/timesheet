import json
import os
from os.path import exists
from copy import deepcopy
import re
import datetime
import shelve

from timesheet import Timesheet

ts = "./.venv/bin/timesheet"
date = datetime.date.today().isoformat()



def test_timesheet_installed():
    """Check that binary is available"""
    assert exists(ts)


def test_create_Timesheet(helpers, tmp_path):
    """Create empty timesheet"""
    path, __ = helpers.make_paths(tmp_path, "test", "test.json")
    os.system(f"{ts} create --storage_path {path}")
    instance = os.system(f"{ts} locate-timesheet --storage_path {path}")
    #assert len(instance) == 1 and len(instance.data.values()) == 1



def test_jsonify(helpers, tmp_path):
    path, output_path = helpers.make_paths(tmp_path, "test", "test.json")
    os.system(
        f"{ts} create --output_path {output_path} --storage_path {path} --storage_name test"
    )
    os.system(f"{ts} jsonify --storage_name test --output_path {output_path} --storage_path {path}")
    os.system(
        f"{ts} create --json_source {output_path}  --storage_name test2 --storage_path {path}2"
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

def test_write_json_summary(helpers, tmp_path):
    """Use command to summarize with default args"""
    storage_path = f"{tmp_path}/timesheet"
    storage_name = "test"
    test = helpers.Timesheet(helpers.daylog_data, storage_path = storage_path, storage_name = storage_name)
    os.system(f"{ts} summarize --storage_path {storage_path} --storage_name {storage_name} --output_path {tmp_path}/test.json ")
    with open( f"{tmp_path}/test.json" ) as f: 
        result = json.load(f)

    assert all(helpers.dict_subset(result, helpers.expected_day_times))
    

def test_delete_no_confirm(helpers, tmp_path):
    """Test if deletion fails if confirmation not specified"""
    storage_name = "test"
    storage_path = f"{str(tmp_path)}/test"
    instance = Timesheet.Timesheet(data = helpers.daylog_data, save = True, storage_name = storage_name, storage_path = storage_path)
    os.system(f"{helpers.ts} delete --storage_name {storage_name} --storage_path {storage_path}")
    # Storage name should be gone if file deleted
    with shelve.open(storage_path) as f:
        assert storage_name in f.keys()

def test_delete_force(helpers, tmp_path):
    """Test that deletion works if `force` flag provided"""
    storage_name = "test"
    storage_path = f"{tmp_path}/test"
    instance = Timesheet.Timesheet(data = helpers.daylog_data, save = True, storage_name = storage_name, storage_path = storage_path)
    os.system(f"{helpers.ts} delete --storage_name {storage_name} --storage_path {storage_path} --force")
    # Storage name should be gone if file deleted
    with shelve.open(storage_path) as f:
        assert not storage_name in f.keys()


def test_single_merge(helpers, tmp_path):
    """No-op merge with just one instance"""
    storage_name = "test"
    storage_path = f"{tmp_path}/test"
    instance = Timesheet.Timesheet(data = helpers.daylog_data, save = True, storage_name = storage_name, storage_path = storage_path)
    comparison = instance.record
    os.system(f"{ts} merge f{storage_name}=f{storage_path} --storage_path = {storage_path} --storage_name {storage_name}")
    os.system(f"{ts} jsonify --storage_name {storage_name} --storage_path {storage_path} --output_path {tmp_path}/test.json")
    os.system(
            f"{ts} create --json_source {tmp_path}/test.json --storage_name test2 --storage_path {storage_path}"
        )
    result = helpers.Timesheet.load(
        storage_name="test2", storage_path=storage_path
    ).record
    assert all(result[k].timestamps == comparison[k].timestamps for k in result.keys())

def test_disjoint_merge(helpers, tmp_path): 
    storage_name1 = "test1"
    storage_path = f"{tmp_path}/test"
    storage_name2 = "test2"
    result_storage_name = "result"
    output_path = f"{tmp_path}/test.json"

    data1 = deepcopy(helpers.daylog_data)
    data2 = helpers.alternate_daylog_data(month = 1)

    instance1 = Timesheet.Timesheet(data = data1, save = True, storage_name = storage_name1, storage_path = storage_path)
    instance2 = Timesheet.Timesheet(data = data2,  save = True, storage_name = storage_name2, storage_path = storage_path)
        
    os.system(f"{ts} merge --timesheets {storage_name1}={storage_path} --timesheets '{storage_name2}={storage_path}' --storage_name {result_storage_name} --storage_path {storage_path}")
    os.system(f"{ts} jsonify --storage_name {result_storage_name} --storage_path {storage_path} --output_path {tmp_path}/test.json")
    os.system(
            f"{ts} create --json_source {output_path} --storage_name test2 --storage_path {storage_path}"
        )

    data1.update(data2)
    result = helpers.Timesheet.load(
        storage_name=result_storage_name, storage_path=storage_path
    )
    instance1.merge(instance2, save = False)
    assert result.equals(instance1)

def test_intersect_merge(helpers):
    """Merge where some keys are shared"""

    


