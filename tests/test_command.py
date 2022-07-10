import os 
from os.path import exists
import json

ts = "./.venv/bin/timesheet"

def test_timesheet_installed():
    assert os.path.exists(ts)
    
def test_create_Timesheet(helpers, tmp_path):
    path =f"{tmp_path}/test" 
    os.system(f"{ts} create --storage_path {path}")
    instance = os.system(f"{ts} locate-timesheet --storage_path {path}")
    #assert len(instance) == 1 and len(instance.record.values()) == 1

def test_jsonify(helpers, tmp_path):
    path =f"{tmp_path}/test" 
    json_path =f"{tmp_path}/test.json" 
    os.system(f"{ts} create --json_path {json_path} --storage_path {path} --storage_name test")
    os.system(f"{ts} jsonify test --json_path {json_path} --storage_path {path}")
    os.system(f"{ts} create --json_source {json_path}  --storage_name test2 --storage_path {path}2")
    #breakpoint()
    first = helpers.Timesheet.load(storage_name = "test", storage_path = path ).record
    second = helpers.Timesheet.load(storage_name = "test2", storage_path = f"{path}2").record
    assert all(first[k].timestamps == second[k].timestamps for k in first)

