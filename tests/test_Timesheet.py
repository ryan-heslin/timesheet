import csv
import datetime
import json
import shelve
from copy import deepcopy
from itertools import groupby
from os import chdir
from os import getcwd
from os import system
from os.path import join
from os.path import split

import pytest

from timesheet import constants
from timesheet import TimeAggregate
from timesheet import utils

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
    new = helpers.Timesheet.from_json(json_path=f"{tmp_path}/{path}", save = False)
    assert original[test_date].timestamps == new[test_date].timestamps


def test_auto_data_path(helpers, tmp_path):
         
    """Default output path is correctly formed if `data_path` is not specified"""
    system(f"touch {tmp_path}/timesheet1.json {tmp_path}/timesheet2.json")
    original = helpers.full_Timesheet(save=False)
    original.write_json(path=None)
    new = helpers.Timesheet.from_json(
        json_path=f"{split(utils.storage_path())[0]}/{original.storage_name}1.json", save=False
    )
    assert original.equals(new)


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
                TimeAggregate.Week.string_format.format,
            ): sum(helpers.expected_day_times.values())
        },
    )


def test_summarize_month(helpers):
    expected = {}
    # Manually aggregate hours by month
    for datestamp in helpers.expected_day_times.keys():
        month = datetime.date.strftime(
            datetime.date.fromisoformat(datestamp),
            TimeAggregate.Month.string_format.format,
        )
        expected[month] = expected.get(month, 0) + helpers.expected_day_times[datestamp]
    helpers.test_summarize(
        TimeAggregate.Month,
        expected,
    )


def test_summarize_year(helpers):
    helpers.test_summarize(
        TimeAggregate.Year, {"2022": sum(helpers.expected_day_times.values())}
    )


def test_write_summary(helpers, tmp_path):
    """Check that `write_json_summary` correctly  writes JSON files of the results"""
    test = helpers.Timesheet(data=helpers.daylog_data, save = False)
    data_path = f"{tmp_path}/test.json"
    # Ensure date in week
    latest_date = max(helpers.expected_day_times.keys())
    test.write_json_summary(
        start_date=min(helpers.expected_day_times.keys()),
        data_path=data_path,
        end_date=latest_date,
    )
    with open(data_path) as f:
        result = json.load(f)
        assert all(helpers.dict_subset(result, helpers.expected_day_times))


def test_write_csv(helpers, tmp_path):
    """Test that an instance with data correctly writes to csv"""
    data_path = f"{tmp_path}/test.csv"
    instance = helpers.Timesheet(
        data=helpers.daylog_data, save=True, storage_path=f"{tmp_path}/timesheet"
    )
    instance.write_csv_summary(path=data_path)
    with open(data_path) as f:
        reader = csv.reader(f)
        read_data = dict(zip(next(iter(reader)), zip(*reader)) )
        assert all(
            float(read_data["hours"][i]) == helpers.expected_day_times[read_data["date"][i]]
            for i in range(len(read_data["date"]))
        )


def test_write_empty_csv(helpers, tmp_path):
    """Test that an instance with no recorded hours correctly writes to csv"""
    data_path = f"{tmp_path}/test.csv"
    instance = helpers.bare_Timesheet
    instance.write_csv_summary(path=data_path)
    with open(data_path) as f:
        reader = csv.reader(f)
        read_data = dict(zip(next(iter(reader)), zip(*reader)) )
        comparison = instance.summarize(start_date=min(instance.record.keys()))
        assert all(
                    float(read_data["hours"][i]) == comparison[read_data["date"][i]]
                    for i in range(len(read_data["date"]))
                )


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
        helpers.Timesheet(helpers.daylog_data, storage_path=storage_path)
        names.append(f"timesheet{i}")
    test = helpers.Timesheet(helpers.daylog_data, storage_path=storage_path)
    assert test._default_name(names) == f"timesheet{n_tests + 1}"


def test_no_storage_name(helpers, tmp_path):
    storage_path = f"{tmp_path}/timesheet"
    test = helpers.Timesheet(
        helpers.daylog_data, storage_name=None, storage_path=storage_path, save=True
    )
    test2 = helpers.Timesheet(
        helpers.daylog_data, storage_name=None, storage_path=storage_path, save=True
    )
    test3 = helpers.Timesheet(
        helpers.daylog_data, storage_name=None, storage_path=storage_path, save=True
    )

    with shelve.open(storage_path) as f:
        assert all(k == f"timesheet{i + 1}" for i, k in enumerate(sorted(f.keys())))


def test_bad_datestamp(helpers, tmp_path):
    """Timesheet given non-ISO formatted datestamp raises error"""
    with pytest.raises(ValueError):
        helpers.Timesheet(
            data={"bad_date": helpers.DayLog()}, storage_path=f"{tmp_path}/timesheet"
        )


def test_self_merge(helpers):
    """Merging Timesheet with itself fails"""
    start = helpers.full_Timesheet(save = False)
    with pytest.raises(ValueError):
        start.merge(start)


def test_simple_merge(helpers):
    """Merging with empty Timesheet has no effect"""
    test = helpers.full_Timesheet(save=False)
    old = test.record
    new = helpers.bare_Timesheet.record
    test.merge(helpers.bare_Timesheet, save = False)
    old.update(new)
    assert all({v.equals(old[k]) for k, v in test.record.items()})


def test_intersect_merge(helpers):
    """Merge where some keys are shared"""
    target_date = "2022-06-27"
    reference = deepcopy(helpers.daylog_data)
    left = helpers.Timesheet(data=reference, save = False)
    right = helpers.Timesheet(
        data={
            target_date: helpers.DayLog(
                date=target_date, timestamps=[datetime.time(hour=1)]
            )
        }, 
        save = False
    )
    left.merge(right, save = False)
    reference[target_date] = helpers.DayLog(
        timestamps=[datetime.time(hour=1)] + reference[target_date].timestamps
    )
    assert all(
        left.record[key].timestamps == reference[key].timestamps
        for key in left.record.keys()
    )


def test_all_intersect_merge(helpers):
    """Timesheets with entirely shared keys are added correctly"""
    reference = deepcopy(helpers.daylog_data)
    left = helpers.Timesheet(data=reference, save = False)
    new_timestamp = datetime.time(hour=23, minute=3)
    # Create new data with a later timestamp for each key
    new_data = {
        key: helpers.DayLog(date=key, timestamps=[new_timestamp])
        for key in reference.keys()
    }
    right = helpers.Timesheet(data=new_data, save = False)
    reference = {
        key: helpers.DayLog(
            date=key, timestamps=reference[key].timestamps + [new_timestamp]
        )
        for key in reference.keys()
    }
    left.merge(right, save = False)
    assert all(
        left.record[key].timestamps == reference[key].timestamps
        for key in left.record.keys()
    )


def test_disjoint_merge(helpers):
    """Merge of DayLogs with no common keys"""
    reference = deepcopy(helpers.daylog_data)
    # No common keys - dates in January
    new = {
        datetime.date.isoformat(datetime.date(year = 2022, month = 1, day = i + 1)): helpers.DayLog(
            timestamps=[datetime.time(hour=3, second=20)]
        )
        for i in range(len(reference))
    }
    left = helpers.Timesheet(data=reference, save = False)
    right = helpers.Timesheet(data=new, save = False)
    reference.update(new)
    left.merge(right, save = True)
    assert all(left.record[key].equals(reference[key]) for key in left.record.keys())


def test_sequential_merge(helpers):
    reference = deepcopy(helpers.daylog_data)
    reference_timesheet = helpers.Timesheet(reference, save = False)
    timesheets = [
        helpers.Timesheet({timestamp: daylog}, save=False)
        for timestamp, daylog in reference.items()
    ]

    # Merge one by one
    while len(timesheets) > 1:
        timesheets[0] = timesheets[0].merge(timesheets.pop(1), save = False)
    combined = timesheets.pop()

    assert all(
        reference_timesheet.record[key].timestamps == combined[key].timestamps
        for key in combined.record.keys()
    )


def test_reference_semantics(helpers):
    """Timesheet unaffacted by deletion of data used to create it"""
    reference = deepcopy(helpers.daylog_data)
    reference_timesheet = helpers.Timesheet(reference, save = False)
    del reference
    assert all(
        reference_timesheet.record[key].timestamps
        == helpers.daylog_data[key].timestamps
        for key in reference_timesheet.record.keys()
    )

def test_equals_equal(helpers):
    assert helpers.full_Timesheet(save = False).equals(helpers.full_Timesheet(save = False))

def test_equals_different(helpers):
    assert not helpers.full_Timesheet(save = False).equals(helpers.bare_Timesheet)

def test_default_json_path(helpers, tmp_path): 
    """Default path is correctly formed it `data_path` is specified"""
    data_path = f"{tmp_path}/test"
    test = helpers.full_Timesheet(data_path = data_path, save = False)
    test.write_json()
    result = helpers.Timesheet.from_json(f"{split(data_path)[0]}/{test.storage_name}1.json", save = False)
    assert test.equals(result)

def test_concat_timestamps(helpers):
    instance = helpers.Timesheet(data = helpers.daylog_data)
    new = [datetime.time(10, 1, 1), datetime.time(12, 2, 2)]
    target_datestamp = "2022-06-27"
    expected = instance.record[target_datestamp].copy().concat_timestamps(new)
    instance.concat_timestamps(date = target_datestamp, timestamps = new)
    assert instance.record[target_datestamp].equals(expected)
