import datetime

import pytest


def test_add_timestamp(helpers):
    instance = helpers.bare_DayLog
    orig_length = len(instance)
    instance.add_timestamps()
    assert len(instance) - orig_length == 1


def test_convert_to_hours(helpers):
    assert (
        helpers.DayLog.convert_to_hours(
            datetime.timedelta(days=0, hours=1, minutes=3, seconds=1)
        )
        == 1 * 1 + 3 / 60 + 1 / 3600
    )


def test_add(helpers):
    new_timestamps = [datetime.time(3, 1, 1, 1), datetime.time(4, 1, 1, 1)]
    assert (
        helpers.full_DayLog() + helpers.DayLog(timestamps=new_timestamps)
    ).timestamps == helpers.DayLog.convert_to_DiffTime(
        helpers.timestamps + new_timestamps
    )


def test_zero_time(helpers):
    assert helpers.bare_DayLog.sum_times() == 0


def test_DiffTime_sub1(helpers):
    assert helpers.bare_DiffTime - helpers.bare_DiffTime == datetime.timedelta(0)


def test_DiffTime_sub2(helpers):
    # timedelta stores only days, seconds, microseconds
    assert helpers.bare_DiffTime - helpers.DiffTime.from_time(
        datetime.time(1, 1, 1, 1)
    ) == datetime.timedelta(0, 62, 999)


def test_bad_timestamp(helpers):
    with pytest.raises(ValueError):
        helpers.full_DayLog().add_timestamps([datetime.time()])
