import csv
import datetime
import json
import shelve
from os import chdir
from os import getcwd
from os import system

import pytest

from timesheet import constants
from timesheet import TimeAggregate

test_date = "2022-06-19"
test_datestamp = datetime.date.fromisoformat(test_date)

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
    """Tests that deletion without confirmation does nothing"""
    storage_path = f"{tmp_path}/test"
    storage_name = "test"
    original = helpers.full_Timesheet(
        storage_name=storage_name, storage_path=storage_path, save=True
    )
    helpers.Timesheet.delete(storage_path=storage_path, storage_name=storage_name)
    with shelve.open(storage_path) as f:
        assert storage_name in f.keys()


def test_list(helpers, tmp_path):
    storage_path = f"{tmp_path}/test"
    test1 = helpers.full_Timesheet(storage_name="test1", storage_path=storage_path)
    test2 = helpers.full_Timesheet(storage_name="test2", storage_path=storage_path)
    assert set(helpers.Timesheet.list(path=storage_path)) == {
        "test1",
        "test2",
    }  # since dict key order is arbitrary, use unordered set for comparison


def test_summarize_day(helpers):
    """Check that `summarize` correctly reports hours worked each day"""
    helpers.test_summarize(TimeAggregate.Day, helpers.expected_day_times)


def test_summarize_week(helpers):
    helpers.test_summarize(
        TimeAggregate.Week,
        {
            datetime.date.strftime(
                datetime.date.fromisoformat(min(helpers.expected_day_times.keys())),
                TimeAggregate.Week.string_format
            ): sum(helpers.expected_day_times.values())
        }
    )


def test_summarize_month(helpers):
    helpers.test_summarize(
        TimeAggregate.Month,
        {
            datetime.date.strftime(
                datetime.date.fromisoformat(min(helpers.expected_day_times.keys())),
                TimeAggregate.Month.string_format
            ): sum(helpers.expected_day_times.values())
        },
    )


def test_summarize_year(helpers):
    helpers.test_summarize(TimeAggregate.Year, {"2022" : sum(helpers.expected_day_times.values())})


def test_write_summary(helpers, tmp_path):
    """Check that `write_json_summary` correctly  writes JSON files of the results"""
    test = helpers.Timesheet(data=helpers.daylog_data)
    json_path = f"{tmp_path}/test.json"
    # Ensure date in week
    latest_date = max(helpers.expected_day_times.keys())
    test.write_json_summary(
        start_date=min(helpers.expected_day_times.keys()),
        json_path=json_path,
        end_date=latest_date,
    )
    with open(json_path) as f:
        result = json.load(f)
        assert all(helpers.dict_subset(result, helpers.expected_day_times))


def test_write_csv(helpers, tmp_path):
    """Test that an instance with data correctly writes to csv"""
    output_path = f"{tmp_path}/test.csv"
    instance = helpers.Timesheet(
        data=helpers.daylog_data, save=True, storage_path=f"{tmp_path}/timesheet"
    )
    instance.write_csv_summary(path=output_path)
    with open(output_path) as f:
        reader = csv.reader(f)
        read_data = {date: float(hours) for date, hours in reader}
        assert all(
            read_data[date] == helpers.expected_day_times[date]
            for date in read_data.keys()
        )


def test_write_empty_csv(helpers, tmp_path):
    """Test that an instance with no recorded hours correctly writes to csv"""
    output_path = f"{tmp_path}/test.csv"
    instance = helpers.bare_Timesheet
    instance.write_csv_summary(path=output_path)
    with open(output_path) as f:
        reader = csv.reader(f)
        read_data = {date: float(hours) for date, hours in reader}
        comparison = instance.summarize(start_date=min(instance.record.keys()))
        assert all(read_data[date] == comparison[date] for date in read_data.keys())


# TODO do these with single function
def test_increment_day(helpers):
    new_datestamp = TimeAggregate.Day.increment(test_datestamp)
    assert (new_datestamp - test_datestamp).days == 1


def test_increment_week(helpers):
    # Monday
    test_datestamp = datetime.date(year=2022, month=6, day=27)
    target_datestamp = datetime.date(year=2022, month=7, day=4)
    for i in range(constants.DAYS_IN_WEEK):
        new_datestamp = TimeAggregate.Week.increment(
            test_datestamp + datetime.timedelta(days=i)
        )
        assert new_datestamp == target_datestamp


def test_increment_month(helpers):
    test_datestamp = datetime.date(year=2020, month=2, day=1)
    target_datestamp = datetime.date(year=2020, month=3, day=1)
    for i in range((target_datestamp - test_datestamp).days):
        new_datestamp = TimeAggregate.Month.increment(
            test_datestamp + datetime.timedelta(days=i)
        )
        assert new_datestamp == target_datestamp


def test_increment_year(helpers):
    test_datestamp = datetime.date(year=2020, month=1, day=1)
    target_datestamp = datetime.date(year=2021, month=1, day=1)
    for i in range((target_datestamp - test_datestamp).days):
        new_datestamp = TimeAggregate.Year.increment(
            test_datestamp + datetime.timedelta(days=i)
        )
        assert new_datestamp == target_datestamp

def test_default_name(helpers, tmp_path):
    n_tests = 5
    storage_path = f"{tmp_path}/timesheet"

    names = []
    for i in range(1, n_tests + 1): 
        helpers.Timesheet(helpers.daylog_data, storage_path  = storage_path)
        names.append(f"timesheet{i}")
    test = helpers.Timesheet(helpers.daylog_data, storage_path = storage_path )
    assert test._default_name(names) == f"timesheet{n_tests + 1}"

def test_no_storage_name(helpers, tmp_path):
    storage_path = f"{tmp_path}/timesheet"
    test = helpers.Timesheet(helpers.daylog_data, storage_name = None, storage_path = storage_path, save = True )
    test2 = helpers.Timesheet(helpers.daylog_data, storage_name = None, storage_path = storage_path, save = True )
    test3 = helpers.Timesheet(helpers.daylog_data, storage_name = None, storage_path = storage_path, save = True )

    with shelve.open(storage_path) as f: 
        assert all(k == f"timesheet{i + 1}" for i, k in enumerate(sorted(f.keys())))
