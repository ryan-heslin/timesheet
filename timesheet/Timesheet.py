import datetime
import json
import shelve
import sys
from functools import reduce
from os import access
from os import getcwd
from os import listdir
from os import makedirs
from os import W_OK
from os.path import dirname
from os.path import exists
from os.path import expanduser
from typing import Dict
from typing import List
from typing import TypeVar
from typing import Union

from timesheet import constants
from timesheet import utils

time_list = Union[List[datetime.datetime], List[datetime.time], List["DiffTime"]]


class DiffTime(datetime.time):
    """Subclass of datetime.time that supports arithmetic by adding a dummy datetime.time attribute that contains the hours, minutes, seconds, and microseconds of a datetime.time object"""

    def __init__(
        self,
        hour: int = 0,
        minute: int = 0,
        second: int = 0,
        microsecond: int = 0,
        tzinfo=None,
        *,
        fold=0,
    ):
        super().__init__()
        self._date_impl = self.dummy_date(self)

    @classmethod
    def from_time(
        cls, time: Union["DiffTime", datetime.time, datetime.datetime]
    ) -> "DiffTime":
        """Converts existing datetime.datetime or datetime.time object to DiffTime"""
        instance = cls.__new__(
            cls, time.hour, time.minute, time.second, time.microsecond
        )
        instance._date_impl = instance.dummy_date(instance)
        return instance

    @staticmethod
    def dummy_date(time: Union[datetime.datetime, "DiffTime"]) -> datetime.datetime:
        """Creates a time datetime object with given year, day, and month fields set to dummy values"""
        return datetime.datetime(
            year=1,
            day=1,
            month=1,
            hour=time.hour,
            minute=time.minute,
            second=time.second,
            microsecond=time.microsecond,
        )

    def __sub__(self, other: "DiffTime") -> datetime.timedelta:
        """Return timedelta object with difference"""
        return self._date_impl - self.dummy_date(other)


class DayLog:
    microsecond_conversions = {
        "hour": 3600000000,
        "minute": 60000000,
        "second": 1000000,
        "microsecond": 1,
    }

    def __init__(
        self,
        date: datetime.date = None,
        timestamps: time_list = [],
    ) -> None:

        # If no timestamps provided, don't automatically supply any
        self._validate_timestamp_sequence(timestamps, raise_exception=True)
        self.timestamps = self.convert_to_DiffTime(timestamps)
        self.date = date if date is not None else datetime.date.today()
        self.creation_time = datetime.datetime.today()

    def add_timestamps(self, timestamps: time_list = None) -> None:
        converted = (
            [datetime.datetime.today()]
            if timestamps is None or len(timestamps) == 0
            else timestamps
        )
        converted: List[DiffTime] = self.convert_to_DiffTime(converted)
        self._validate_timestamp_sequence(timestamps=converted, raise_exception=True)
        # New timestamp must come after all recorded ones
        if len(self) > 0 and converted[0] <= self.timestamps[-1]:
            raise ValueError(
                f"Earliest new timestamp {converted[0]} is identical to or earlier than latest recorded timestamp {self.timestamps[-1]}"
            )
        self.timestamps.extend(converted)

    def __len__(self) -> int:
        return len(self.timestamps)

    @staticmethod
    def yyyymmdd(timestamp=datetime.datetime.today()):
        return datetime.datetime.strftime(timestamp, "%Y-%m-%d")

    def __str__(self) -> str:
        return "\n".join(
            [
                f"A day log object for {self.yyyymmdd(self.date)}, created {self.creation_time}"
            ]
            + [str(x) for x in self.timestamps]
        )

    def __add__(self, other: "DayLog"):
        """Adding another DayLog object concatenates the two lists of timestamps in a new object (assuming the result is valid)"""
        if self.date != other.date:
            raise ValueError(
                f"Cannot add DiffTime objects when dates {self.date} and {other.date} disagree"
            )
        combined: time_list = self.timestamps + other.timestamps
        return self.__class__(date=self.date, timestamps=combined)

    def __repr__(self) -> str:
        return str(self)

    @staticmethod
    def convert_to_hours(delta: datetime.timedelta) -> float:
        """Converts a datetime.timedelta object to its decimal value in hours"""
        return delta.days * 24 + delta.seconds / 3600 + delta.microseconds / 3600000000

    def sum_times(self) -> float:
        n_timestamps = len(self)
        # If 0 or 1 timestamps only, no difference to account for
        if n_timestamps < 2:
            time = datetime.timedelta(0)
        else:
            time = reduce(
                lambda x, y: x + y,
                (
                    self.timestamps[i] - self.timestamps[i - 1]
                    for i in range(1, n_timestamps, 2)
                ),
            )
        if n_timestamps % 2 != 0:
            print("Odd number of timestamps; ignoring last")
        return self.convert_to_hours(time)

    @staticmethod
    def _validate_timestamp_sequence(
        timestamps: list, raise_exception: bool = True
    ) -> bool:
        """Confirm all timestamps are in increasing order"""
        out = all(timestamps[i + 1] > timestamps[i] for i in range(len(timestamps) - 1))
        if not out and raise_exception:
            raise ValueError("Timestamps not all in chronological order")
        return out

    @staticmethod
    def convert_to_DiffTime(timestamps: time_list):
        return [
            DiffTime.from_time(x) if not isinstance(x, DiffTime) else x
            for x in timestamps
        ]

    @staticmethod
    def absolute_time(time: Union[datetime.time, "DiffTime"]) -> int:
        """Converts datetime.time object to microseconds"""
        return sum(
            __class__.microsecond_conversions[unit] * getattr(time, unit)
            for unit in __class__.microsecond_conversions.keys()
        )

class Timesheet:
    def __init__(
        self,
        data: Dict[str, DayLog] = None,
        storage_path=None,
        storage_name=None,
        save=True,
        json_path=None,
    ) -> None:

        # If no initial data is supplied, default to empty DayLog dated today

        self._constructor(
            data=data,
            storage_path=storage_path,
            storage_name=storage_name,
            save=save,
            json_path=json_path,
        )

    def _constructor(self, **kwargs) -> None:
        """Common constructor, shared by __init__ and __new__"""
        kwargs = {**kwargs}
        data = (
            {DayLog.yyyymmdd(): DayLog()} if kwargs["data"] is None else kwargs["data"]
        )
        self.record = data
        self.storage_name = kwargs["storage_name"]
        self.creation_time = datetime.datetime.today()
        self.last_save = None
        self.json_path = kwargs["json_path"]
        self.storage_path = (
            kwargs["storage_path"]
            if kwargs["storage_path"] is not None
            else constants.STORAGE_PATH
        )
        # Generate default storage name if none provided
        if ( arg_name :=kwargs["storage_name"] ) is None:
            if exists(self.storage_path):
                used_names = utils.use_shelve_file(
                                storage_name=None,
                                func=lambda f: [k for k in f],
                                path=self.storage_path
                            )
            else: 
                used_names = []
            self.storage_name = self._default_name(names = used_names, extension = "")
        else: 
            self.storage_name = arg_name
            
        if kwargs.get( "save" ):
            self.save(overwrite=True)

    def __str__(self) -> str:
        return f"""A Timesheet object created {self.creation_time}
        {self.record!r}"""

    def __repr__(self) -> str:
        return self.__str__()

    def save(
        self,
        path: str = None,
        storage_name: str = None,
        overwrite: bool = False,
        create_directory: bool = False,
    ) -> None:
        storage_name = self.storage_name if storage_name is None else storage_name
        path = self.storage_path if path is None else path
        if storage_name is None:
            print("Invalid storage name")
            return
        target = dirname(path)
        if not access(target, W_OK):
            print(f"You lack write permission for directory {target}")
            return
        if not exists(target):
            if create_directory:
                makedirs(target)
            else:
                print(
                    f"Cannot save: {target} does not exist, and create_directory = False"
                )
                return

        with shelve.open(path, "c") as f:
            # Bail out on attempt to overwrite if overwrite = False
            if (
                not overwrite
                and f.get(storage_name)
                and (
                    not utils.is_interactive()
                    or input(
                        f"Saving will overwrite existing file {storage_name!r}. Press enter to continue, any other key to abort: "
                    )
                    != ""
                )
            ):
                return
            self.last_save = datetime.datetime.today()
            f[storage_name] = self

    @staticmethod
    def load(storage_name: str, storage_path: str = None) -> "Timesheet":
        return utils.use_shelve_file(
            storage_name=storage_name, func=lambda f: f[storage_name], path=storage_path
        )

    @staticmethod
    def delete(storage_name: str, path: str = None, confirm: bool = True) -> None:
        confirm_prompt = (
            "Press enter to confirm deletion, any other key to abort"
            if confirm and utils.is_interactive()
            else None
        )
        utils.use_shelve_file(
            storage_name=storage_name,
            func=lambda f: f.pop(storage_name),
            path=path,
            confirm_prompt=confirm_prompt,
        )

    @staticmethod
    def list(path: str = None) -> List[str]:
        """List names of DayLog files in shelve storage"""
        return utils.use_shelve_file(
            path=path,
            func=lambda f: [k for k, v in f.items() if isinstance(v, Timesheet)],
        )

    def add_timestamps(
        self, date: Union[datetime.date, str] = None, timestamps: List[datetime.datetime] = None
    ) -> None:
        date = datetime.datetime.today() if date is None else date
        timestamps = (
            [datetime.datetime.today()]
            if timestamps is None or timestamps == []
            else timestamps
        )
        # If passed as string, coerce first to common formate
        date = datetime.date.fromisoformat(date) if type(date) is str else date
        datestamp = DayLog.yyyymmdd(date)
        data = self.record.get(datestamp)
        # If a DayLog object exists for this day, add timestamp to it. Otherwise, create a new one, with the current time as an initial timestamp
        if data is None:
            self.record[datestamp] = DayLog(timestamps=timestamps)
        else:
            data.add_timestamps(timestamps)
        self.save(overwrite=True)

    def __getitem__(self, k: str) -> DayLog:
        return self.record[k]

    @property
    def json_path(self) -> str:
        return self._json_path

    @json_path.setter
    def json_path(self, path: str) -> None:
        self._json_path = path

    def __len__(self) -> int:
        return len(self.record)

    def _default_name(self, names: List[str] = None, extension: str = "") -> str:
        names = listdir(".") if names is None else names
        """Generate a default path for saving"""
        stem = self.__class__.__name__.lower()
        return f"{stem}{utils.next_number(stem = stem, names = names)}{extension}"

    def write_json(self, path: str = None) -> None:
        if path is None:
            path = (
                self.json_path
                if self.json_path is not None
                else self._default_name(names = listdir("."), extension=".json")
            )
        with open(path, "w") as f:
            json.dump(self.record, f, default=utils.json_serialize)

    def summarize(self, date: Union[datetime.date, str] = None ) -> Dict[str, float]:
        """Sum hours worked for a given week"""
        # Date can be any date in the target week
        parsed = date
        if isinstance(parsed , str):
            parsed : datetime.date = datetime.date.fromisoformat(parsed)
        elif parsed is None:
            parsed  : datetime.date = datetime.date.today()
        else:
            parsed  : datetime.date= date

        calendar = parsed.isocalendar()

        # Weeks start on Monday, indexed 1
        days_into_week = datetime.timedelta(days=calendar[2] - 1)
        cur_date = parsed - days_into_week
        one_day = datetime.timedelta(days=1)
        # datestamps = [None] * constants.DAYS_IN_WEEK
        out = {}
        for __ in range(constants.DAYS_IN_WEEK):
            next_date = cur_date + one_day
            cur_datestamp = DayLog.yyyymmdd(cur_date)
            # If no date exists for this day (implying no hours worked), set value to 0
            hours = self.record.get(cur_datestamp, DayLog()).sum_times()
            out[cur_datestamp] = hours
            cur_date = next_date


        return out

    def write_json_summary(self, json_path : str, date: Union[datetime.date, str] = None) -> None:
        """Compute summary and save as JSON instead of returning a dict"""
        summary = self.summarize(date = date)
        with open(json_path, "w") as f:
            json.dump(summary, f)

    def write_year_csv(self, path : str):
        # TODO: allow aggregation of all data by week, in addition to targeting 
        # just one week 
        # Maybe use a generator to yield week summaries on demand?
        #data = self.summarize(date = )
        pass

    @classmethod
    def from_json(
        cls,
        path: str,
        storage_path: str = None,
        storage_name: str = None,
        save: bool = True,
        json_path: str = None,
    ) -> "Timesheet":
        """Creates instance from path to JSON representation"""
        with open(path) as f:
            data = json.load(f, object_hook=utils.date_parser)
        instance = cls.__new__(cls)
        instance._constructor(
            data=data,
            storage_path=storage_path,
            storage_name=storage_name,
            save=save,
            json_path=json_path,
        )
        return instance
