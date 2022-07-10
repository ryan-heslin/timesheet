import datetime
from os import chdir
from os import getcwd
from os import system

import pytest

import timesheet.constants

test_date = "2022-06-19"

# @pytest.fixture
# def bare_Timesheet():
## test_date = DayLog.yyyymmdd(datetime.date.today())
# return Timesheet(save=False)
#
#
# @pytest.fixture
# def full_Timesheet(full_DayLog):
# return Timesheet(data={"2022-06-19": full_DayLog}, save=False)
#


def test_bare_Timesheet(helpers):
    instance = helpers.bare_Timesheet
    assert len(instance) == 1 and len(instance.record.values()) == 1


def test_full_Timesheet(helpers):
    instance = helpers.full_Timesheet(save=False)
    assert instance.record[test_date].timestamps == helpers.full_DayLog().timestamps


def test_write_json(helpers, tmp_path):
    # helpers.full_Timesheet(save=False).write_json(path=f"{tmp_path}/test.json")
    helpers.write_json(path=f"{tmp_path}/test.json")
    helpers.files_in_directory(tmp_path, ["test.json"])


def test_from_json(helpers, tmp_path):
    path = "test.json"
    original = helpers.write_json(path=f"{tmp_path}/{path}")
    new = helpers.Timesheet.from_json(path=f"{tmp_path}/{path}")
    assert original[test_date].timestamps == new[test_date].timestamps


def test_auto_json_path(helpers, tmp_path):
    # helpers.touch(f"{tmp_path}/timesheet1.json")
    # helpers.touch(f"{tmp_path}/timesheet2.json")

    wd = getcwd()
    chdir(tmp_path)
    system(f"touch {tmp_path}/timesheet1.json {tmp_path}/timesheet2.json")
    original = helpers.full_Timesheet(save=False)
    original.write_json(path=None)
    chdir(wd)
    new = helpers.Timesheet.from_json(f"{tmp_path}/timesheet3.json", save=False)
    # breakpoint()
    assert original.record[test_date].timestamps == new.record[test_date].timestamps


def test_save(helpers, tmp_path):
    storage_path = f"{tmp_path}/test"
    original = helpers.full_Timesheet(storage_name="test", storage_path=storage_path)
    original.save()
    copy = helpers.Timesheet.load(storage_name="test", storage_path=storage_path)
    assert original.record[test_date].timestamps == copy.record[test_date].timestamps


def test_delete(helpers, tmp_path):
    storage_path = f"{tmp_path}/test"
    original = helpers.full_Timesheet(storage_name="test", storage_path=storage_path)
    helpers.Timesheet.delete(path=storage_path, storage_name="test")
    with pytest.raises(KeyError):
        helpers.Timesheet.load(storage_name="test", storage_path=storage_path)


def test_list(helpers, tmp_path):
    storage_path = f"{tmp_path}/test"
    test1 = helpers.full_Timesheet(storage_name="test1", storage_path=storage_path)
    test2 = helpers.full_Timesheet(storage_name="test2", storage_path=storage_path)
    assert set(helpers.Timesheet.list(path=storage_path)) == {
        "test1",
        "test2",
    }  # since key order is arbitrary


def test_summarize(helpers):
    test = helpers.Timesheet(data=helpers.daylog_data)

    # Test for all days in week
    assert all(
        test.summarize(
            date=datetime.date(
                year=2022, month=6 + (i + 27 > 30), day=(27 + i) % 31 + (i + 27 > 30)
            )
        )
        == {
            "2022-06-27": 1.5,
            "2022-06-28": 0,
            "2022-06-29": 5 / 6,
            "2022-06-30": 0,
            "2022-07-01": 0,
            "2022-07-02": 0,
            "2022-07-03": 0,
        }
        for i in range(timesheet.constants.DAYS_IN_WEEK)
    )
