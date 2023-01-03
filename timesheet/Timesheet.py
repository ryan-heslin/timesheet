import csv
import datetime
import json
import os.path
import shelve
from functools import lru_cache
from functools import reduce
from os import listdir
from os import makedirs
from os.path import dirname
from os.path import exists
from os.path import isdir
from os.path import split
from typing import Dict
from typing import List
from typing import Tuple
from typing import TypeVar
from typing import Union

from timesheet import constants
from timesheet import TimeAggregate
from timesheet import utils

time_list = Union[List[datetime.datetime], List[datetime.time], List["DiffTime"]]


class DiffTime(datetime.time):
    """Subclass of :code:`datetime.time` intended to represent times without reference to a particular day. It supports subtraction by creating a dummy :code:`datetime.time` attribute that contains hour, minute, second, and microsecond components"""

    def __init__(
        self,
        hour: int = 0,
        minute: int = 0,
        second: int = 0,
        microsecond: int = 0,
        tzinfo: Union[datetime.tzinfo, None] = None,
        *,
        fold: int = 0,
    ):
        """
        Initialize a DiffTime object. This subclass of :code:`datetime.datetime` creates a dummy `datetime.time` object

        :param hour int: Hour value in :code:`range(24)`
        :param minute int: Minute value in :code:`range(60)`
        :param second int: Second value in :code:`range(60)`
        :param microsecond int: Microsecond value in :code:`range(1000000)`
        :param tzinfo: :code:`tzinfo` instance, or :code:`None`
        :param fold int: 0 or 1 indicating whether to distinguish "wall times"
        """
        super().__init__()
        self._date_impl = self._dummy_date(self)

    @classmethod
    def from_time(
        cls, time: Union["DiffTime", datetime.time, datetime.datetime]
    ) -> "DiffTime":
        """
        Alternate constructor that converts an existing :code:`datetime.time` or :code:`datetime.datetime` instance to :code:`DiffTime`

        :param time Union["DiffTime", datetime.time, datetime.datetime]: :code:`datetime.time` or :code:`datetime.datetime` instance
        :rtype "DiffTime": :code:`DiffTime` instance
        """
        instance = cls.__new__(
            cls, time.hour, time.minute, time.second, time.microsecond
        )
        instance._date_impl = instance._dummy_date(instance)
        return instance

    @staticmethod
    def _dummy_date(time: Union[datetime.datetime, "DiffTime"]) -> datetime.datetime:
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
        return self._date_impl - __class__._dummy_date(other)

    @property
    @lru_cache()
    def min(self):
        """Lowest possible DiffTime object"""
        return DiffTime(hour=0, second=0, minute=0, microsecond=0)

    @property
    @lru_cache()
    def max(self):
        """Greatest possible DiffTime object"""
        return DiffTime(hour=23, minute=59, second=59, microsecond=999999)


class DayLog:

    # Used to convert time differences to hours
    hour_conversions = {"days": 24, "seconds": 1 / 3600, "microseconds": 1 / 3.6e9}

    def __init__(
        self, date: Union[datetime.date, str, None] = None, timestamps: Union[time_list, None] = None
    ) -> None:
        """
        Initialize DayLog instance. This class records a series of timestamps within the
        span of a specified date. It can form intervals from these timestamps and compute their total sum.

        :param date datetime.date: Date the instance should refer to
        :param timestamps time_list: Optional list of timestamps to record. Must be sorted in ascending order and contain no duplicates
        """

        # If, no timestamps provided, don't automatically supply any
        timestamps = [] if timestamps is None else timestamps
        self._validate_timestamp_sequence(timestamps, raise_exception=True)
        self.timestamps = self.convert_to_DiffTime(timestamps)
        self.date = utils.handle_date_arg(
            date, default=datetime.date.today(), allow_None=True
        )
        self.creation_time = datetime.datetime.today()

    def equals(self, other: "DayLog") -> bool:
        """
        Determines whether one instance and another have identical timestamp sequences.

        :param other "DayLog": A :code:`DayLog` instance
        :rtype bool: :code:`True` if the sequences are identical, :code:`False` otherwise.
        """
        return self.timestamps == other.timestamps

    def concat_timestamps(self, timestamps: Union[time_list, None] = None) -> "DayLog":
        """
        Concatenate additional timestamps to those stored in the calling instance. Added timestamps must all be later than the last timestamp stored in the
        caller and sorted in ascending order.

        :param timestamps time_list: List containing elements of class :code:`datetime.datetime`, :code:`datetime.time`, or :code:`Timesheet.DiffTime`.
        :rtype None:
        :raises ValueError: If any member of :code:`timestamps` is later than the caller's latest timestamp and/or :code:`timestamps` is not sorted in ascending order.
        """
        converted = (
            [datetime.datetime.today()]
            if timestamps is None or len(timestamps) == 0
            else timestamps
        )
        converted = self.convert_to_DiffTime(converted)
        self._validate_timestamp_sequence(timestamps=converted, raise_exception=True)

        # New timestamp must come after all recorded ones
        if len(self) > 0 and converted[0] <= self.timestamps[-1]:
            raise ValueError(
                f"Earliest new timestamp {converted[0]} is identical to or earlier than latest recorded timestamp {self.timestamps[-1]}"
            )
        self.timestamps.extend(converted)
        return self

    def __len__(self) -> int:
        return len(self.timestamps)

    @staticmethod
    def yyyymmdd(timestamp: Union[datetime.datetime, datetime.date, None] = None) -> str:
        """
        Format a date YYYY-MM-DD

        :param timestamp Union[datetime.datetime,  None]: :code:`datetime.datetime` instance
        :rtype str: The formatted date
        """
        date_value = datetime.datetime.today() if timestamp is None else timestamp
        parser = (
            datetime.datetime.strftime
            if isinstance(timestamp, datetime.datetime)
            else datetime.date.strftime
        )
        return parser(date_value, "%Y-%m-%d")

    def __str__(self) -> str:
        return "\n".join(
            [
                f"A day log object for {__class__.yyyymmdd(self.date)}, created {self.creation_time}"
            ]
            + [ "\n" ] +
            [str(x) for x in self.timestamps]
        )

    def copy(self) -> "DayLog":
        """Create a copy with identical data
        :rtype DayLog: Copy with identical data
        """
        return __class__(date = self.date, timestamps = self.timestamps.copy())

    def __add__(self, other: "DayLog") -> "DayLog":
        """
        Combine this :code:`DayLog` instance with another by creating a new
        instance with concatenated timestamps. Fails if the two instances do not describe the same date or the timstamps are incompatible.

        :param other "DayLog": Another :code:`DayLog` instance. It must refer to the same date, and its timestamps, if they exist, must meet the requirements for :code:`DayLog.concat_timestamps`
        :raises ValueError: If any of the above conditions are not met
        :rtype DayLog: A new instance with the concatenated timestamps
        """
        if self.date != other.date:
            raise ValueError(
                f"Cannot add DiffTime objects when dates {self.date} and {other.date} disagree"
            )
        # Add in sorted order (arbitrary if one or both have no timestamps)
        if (
            len(self.timestamps) == 0
            or len(other.timestamps) == 0
            or self.timestamps[0] <= self.timestamps[-1] < other.timestamps[0]
        ):
            combined: time_list = self.timestamps + other.timestamps
        elif other.timestamps[0] <= other.timestamps[-1] < self.timestamps[0]:
            combined: time_list = other.timestamps + self.timestamps
        else:
            raise ValueError(
                f"""Cannot combine DayLog instances if timestamps of one are not all either greater than or less than timestamps of the other
                Left: {self.timestamps!r}
                Right: {other.timestamps!r}
                """
            )
        return self.__class__(date=self.date, timestamps=combined)

    def __repr__(self) -> str:
        return str(self)

    @staticmethod
    def convert_to_hours(delta: datetime.timedelta) -> float:
        """
        Converts a :code:`datetime.timedelta` object to its value in hours.

        :param delta datetime.timedelta: :code:`datetime.timedelta` instance
        :rtype float: Value of the instance in hours
        """
        return sum(
            conversion * getattr(delta, unit)
            for unit, conversion in __class__.hour_conversions.items()
        )

    def sum_time_intervals(self) -> float:
        """
        Sum this instance's time intervals. Returns the total value of the time contained in the intervals in hours. If there is an odd number of timestamps, leaving an unbounded interval, the last is ignored with a warning.

        :rtype float: Total time spanned by all intervals stored in this instance, or 0 if fewer than two are recorded.
        """
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
    def convert_to_DiffTime(timestamps: time_list) -> List["DiffTime"]:
        """
        Convert a list of timestamps to :code:`DiffTime` instances

        :param timestamps time_list: List whose members are all instances of :code:`datetime.datetime`, :code:`datetime.time`, or :code:`DiffTime`
        :rtype List[DiffTime] : List of :code:`DiffTime` instances
        """
        return [
            DiffTime.from_time(x) if not isinstance(x, DiffTime) else x
            for x in timestamps
        ]


class Timesheet:
    """Contains a set of DayLog objects mapped to dates and implements methods for summarizing and aggregating hours worked across different units of time, such as days or months"""

    def __init__(
        self,
        data: Union[Dict[str, DayLog], None] = None,
        storage_path: Union[str, None] = None,
        storage_name: Union[str, None] = None,
        save: bool = True,
        data_path: Union[str, None] = None,
        output_path: Union[str, None] = None
    ) -> None:
        """
        Initialize a :code:`Timesheet` instance.

        :param data Dict[str, DayLog]: Optional dict one mapping or more :code:`DayLog`  instances to :code:`str` keys, which must be recognizable as ISO-formatted dates
        :param storage_path str: Optional path to :code:`shelve` file in which to store this instance. Defaults to :code:`$HOME/.timesheet/timesheets`
        :param storage_name : Optional name for this instance in the :code:`shelve` file in which it is stored. If already in use, an error is thrown.
        :param save bool: Optional bool determining whether to save on instance creation
        :param data_path str:
        :rtype None:
        """

        # If no initial data is supplied, default to empty DayLog dated today
        self._constructor(
            data=data,
            storage_path=storage_path,
            storage_name=storage_name,
            save=save,
            data_path=data_path,
            output_path = output_path
        )

    def _constructor(self, **kwargs) -> None:
        """Common constructor, shared by __init__ and __new__"""
        kwargs = {**kwargs}
        data = (
            {DayLog.yyyymmdd(): DayLog()} if kwargs["data"] is None else kwargs["data"]
        )
        data = {
            key: data[key].copy()
            for key in sorted(data.keys(), key=lambda k: datetime.date.fromisoformat(k))
        }
        # utils.validate_datestamps(data.keys())
        self.record = data
        self._storage_name = kwargs["storage_name"]
        self.creation_time = datetime.datetime.today()
        self.last_save = None
        self._data_path = kwargs["data_path"]
        self._output_path = kwargs["output_path"]
        self._storage_path = (
            kwargs["storage_path"]
            if kwargs["storage_path"] is not None
            else utils.storage_path()
        )
        # Create storage path if it does not exist already
        storage_dir = split(self._storage_path)[0]
        if not exists(storage_dir):
            makedirs(storage_dir)
        # Generate default storage name if none provided
        if (arg_name := kwargs["storage_name"]) is None:
            # Get storage names already in use, if any
            overwrite = True
            used_names = []
            if exists(self._storage_path):
                used_names.extend(
                    utils.use_shelve_file(
                        storage_name=None,
                        func=lambda f: [k for k in f],
                        path=self._storage_path,
                    )
                )
            self._storage_name = self._default_name(names=used_names, extension="")
        else:
            overwrite = False
            self._storage_name = arg_name

        if kwargs.get("save"):
            self.save(overwrite=overwrite)

    @property
    def storage_name(self) -> str:
        return self._storage_name

    @storage_name.setter
    def storage_name(self, storage_name: str) -> None:
        self._storage_name = storage_name

    @property
    def storage_path(self) -> str:
        return self._storage_path

    @storage_path.setter
    def storage_path(self, storage_path: str) -> None:
        if not (storage_path is None or
            (os.path.exists(storage_path) and utils.path_readable(storage_path)
        ) or utils.path_writeable(storage_path)):
            raise PermissionError(f"You lack write permission for {storage_path}")
        self._storage_path = storage_path

    @property
    def output_path(self) -> str:
        return self._output_path

    @output_path.setter
    def output_path(self, output_path: str) -> None:
        if not (output_path is None or
            (os.path.exists(output_path) and utils.path_readable(output_path)
        ) or utils.path_writeable(output_path)):
            raise PermissionError(f"You lack write permission for {output_path}")
        self._output_path = output_path

    @property
    def data_path(self) -> str:
        return self._data_path

    @data_path.setter
    def data_path(self, data_path: str) -> None:
        if not(data_path is None or utils.path_writeable(data_path)):
            raise PermissionError(f"You lack write permission for {data_path}")
        self._data_path = data_path

    def __str__(self) -> str:
        return f"""A Timesheet object created {self.creation_time}
        {self.record!r}"""

    def __repr__(self) -> str:
        return self.__str__()

    def equals(self, other: "Timesheet") -> bool:
        """
        Determine whether two instances contain the same data.

        :param other "Timesheet": Another :code:`Timesheet` instance.
        :rtype bool: :code:`True` if the data are identical, :code:`False` otherwise
        """
        # Not identical if keys not all equal
        if not (own_keys := sorted(self.record.keys())) == sorted(other.record.keys()):
            return False

        # Must use equals method instead of == because the former ignores different creation times
        return all(
            self.record[datestamp].equals(other.record[datestamp])
            for datestamp in own_keys
        )

    def save(
        self,
        path: Union[str, None] = None,
        storage_name: Union[str, None] = None,
        overwrite: bool = False,
        create_directory: bool = False,
    ) -> "Timesheet":
        """
        Save this instance to a :code:`shelve` object at a specified path, using a specified name.

        :param path str: Optional path to the :code:`shelve` file. Default to "$HOME/.timesheet/timesheets".
        :param storage_name str: Optional name for this instance in :code:`shelve` storage. Generated automatically if omitted.
        :param overwrite bool: Optional :code:`bool` indicating whether to overwrite an existing instance that shares :code:`storage_name`. Default :code:`False`
        :param create_directory bool: Optional logical indivating whether to create the directory containing :code:`storage_path` if it does not exist. Default :code:`False`.
        :rtype Timesheet: Copy of the instance
        """
        storage_name = self._storage_name if storage_name is None else storage_name
        path = self._storage_path if path is None else path
        target = dirname(path)
        if not utils.path_readable(target):
            raise PermissionError(f"You lack read permission for directory {target}")
        if not exists(target):
            if create_directory:
                makedirs(target)
            else:
                raise FileNotFoundError(
                    f"Cannot save: {target} does not exist, and create_directory = False"
                )

        with shelve.open(path, "c", writeback=True) as f:
            # Create default storage name if unspecified
            if storage_name is None:
                storage_name = self._default_name(list(f.keys()))
            # Bail out on attempt to overwrite if overwrite = False
            if (
                not overwrite
                and f.get(storage_name) is not None
                and (
                    not utils.is_interactive()
                    or input(
                        f"Saving will overwrite existing file {storage_name!r}. Press enter to continue, any other key to abort: "
                    )
                    != ""
                )
            ):
                return self
            f[storage_name] = self
            f.sync()

        return self

    def copy(self, storage_name = None) -> "Timesheet":
        """Copy a :code:`Timesheet` instance
        :param storage_name: Name to assign to copy in :code:`shelve` storage
        :rtype Timesheet: The newly created copy
        """
        return __class__(data = self.record, storage_path = self.storage_path, storage_name=storage_name, data_path=self.data_path, save = False)

    @staticmethod
    def load(storage_name: str, storage_path: Union[str, None] = None) -> "Timesheet":
        """
        Load a :code:`Timesheet` instance from storage.

        :param storage_name str: Name of the target instance in :code:`shelve` storage.
        :param storage_path str: Path to :code:`shelve` file.
        :rtype "Timesheet": Instance loaded from the target name and path.
        """
        if storage_name is None:
            raise ValueError(f"Invalid storage name {storage_name!r}")
        return utils.use_shelve_file(
            storage_name=storage_name, func=lambda f: f[storage_name], path=storage_path
        )

    @staticmethod
    def delete(storage_name: str, storage_path: str, confirm: bool = True) -> None:
        """
        Delete the :code:`Timesheet` instance identified by :code:`storage_path` and :code:`storage_name`.

        :param storage_name str: String identifying the target instance in :code:`shelve` storage.
        :param storage_path str:
        :param confirm bool: Optional :code:`bool`indicating whether to ask for confirmation before deletion (if run interactively) or abort (if not). Default :code:`True`
        :rtype None:
        """
        confirm_prompt = (
            "Press enter to confirm deletion, any other key to abort"
            if confirm
            else None
        )
        utils.use_shelve_file(
            storage_name=storage_name,
            func=lambda f: f.pop(storage_name),
            path=storage_path,
            confirm_prompt=confirm_prompt,
        )

    @staticmethod
    def list(path: Union[str, None] = None) -> List[str]:
        """
        List the names of :code:`Timesheet` instances stored at a particular path

        :param path str: Path to the :code:`shelve` file to list
        :rtype List[str]: List of keys to the :code:`shelve` file chosen.
        """
        path = utils.storage_path() if path is None else path
        if not exists(path) and isdir(path):
            out = []
        else:
            out = utils.use_shelve_file(
            path=path,
            func=lambda f: [k for k, v in f.items() if isinstance(v, Timesheet)],
        )
        return out

    def concat_timestamps(
        self,
        date: Union[datetime.date, str, None] = None,
        timestamps: Union[List[datetime.datetime], None] = None,
    ) -> "Timesheet":
        """Concatenate additional timestamps for a given date, or create a new entry if none exists
        :param date: Union[datetime.date, str] Date whose data will be combined with the new timestmaps
        :param timestamps: List[datetime.datetime] Timestamps to append
        :rtype Timesheet: Copy of the modified instance
        """
        date = datetime.datetime.today() if date is None else date
        timestamps = (
            [datetime.datetime.today()]
            if timestamps is None or timestamps == []
            else timestamps
        )

        # If passed as string, coerce first to common formate
        date = utils.handle_date_arg(date)
        datestamp = DayLog.yyyymmdd(date)
        data = self.record.get(datestamp)
        # If a DayLog object exists for this day, add timestamp to it. Otherwise, create a new one, with the current time as an initial timestamp
        if data is None:
            self.record[datestamp] = DayLog(timestamps=timestamps)
        else:
            data.concat_timestamps(timestamps)
        self.save(overwrite=True)
        return self

    def merge(
        self,
        other: "Timesheet",
        storage_path: Union[str, None] = None,
        storage_name: Union[str, None] = None,
        save: bool = True,
        data_path: Union[str, None] = None,
        output_path : Union[str, None] = None
    ) -> "Timesheet":

        """
        Initialize a :code:`Timesheet` instance.

        :param data Dict[str, DayLog]: Optional dict one mapping or more :code:`DayLog`  instances to :code:`str` keys, which must be recognizable as ISO-formatted dates
        :param storage_path str: Optional path to :code:`shelve` file in which to store this instance. Defaults to :code:`$HOME/.timesheet/timesheets`
        :param storage_name : Optional name for this instance in the :code:`shelve` file in which it is stored. If already in use, an error is thrown.
        :param save bool: Optional bool determining whether to save on instance creation
        :param data_path str:
        :rtype None:
        """
        # Find common keys
        # If none, just merge dicts
        # If common keys, for each key:
        # Try to combine
        own_keys = set(self.record.keys())
        other_keys = set(other.record.keys())
        common_keys = own_keys.intersection(other_keys)
        distinct_keys = own_keys.symmetric_difference(other_keys)

        # Get all distinct keys from appropriate dict
        new_data = {
            timestamp: self.record.get(timestamp, other.record.get(timestamp))
            for timestamp in distinct_keys
        }

        # Attempt DayLog merge for each shared key
        new_data.update(
            {
                timestamp: self.record[timestamp] + (other.record[timestamp])
                for timestamp in common_keys
            }
        )
        self._constructor(
            data=new_data,
            storage_path=storage_path,
            storage_name=storage_name,
            save=save,
            data_path=data_path,
            output_path = output_path
        )
        return self

    def __getitem__(self, k: str) -> DayLog:
        return self.record[k]

    def __len__(self) -> int:
        return len(self.record)

    def _default_name(self, names: List[str], extension: str = "") -> str:
        """Generate a default path or storage name for saving when none is provided"""
        stem = self.__class__.__name__.lower()
        return f"{stem}{utils.next_number(stem = stem, names = names)}{extension}"

    def _choose_path(self, path : Union[str, None],  default : str, extension : str )-> Tuple[str, str]:
            # If no path provided, default to {storage_name}.json, in directory of output
            # path if provided, otherwise storage path (always set)

        default_supplied = False
        if path is None:
            if default is None:
                raise ValueError("Path is None, but no default path was passed")
            default_supplied = True
            path = default
        storage_dir = path
        if not os.path.isdir(path):
            storage_dir = dirname(path)
        # If authorized, create target directory if it does not exist.
        if default_supplied:
            path = f"{storage_dir}/{self._storage_name}{utils.next_number(self._storage_name, listdir(storage_dir))}.{extension}"
        # path = (
        #    utils.add_extension(os.path.self.data_path, ".json")
        #    if self.data_path is not None
        #    else self._default_name(names=listdir("."), extension=".json")
        # )
        return storage_dir, path

    def write_json(self, path: Union[str, None] = None, make_directory=False) -> "Timesheet":
        """
        Write an instance's day data to JSON. This makes it possible to copy the instance by caling `Timesheet.from_json` on the path to the created JSON.

        :param path str: Optional path to output JSON. Defaults to the instance's :code:`data_path` attribute, or a generated unique name if it is :code:`None`.
        :make_directory: bool Whether to create directory to contain :code:`path` if it does not already exist
        :rtype Timesheet: Copy of the modified instance
        """
        storage_dir, path = self._choose_path(path = path, default = self._data_path, extension = "json")
            # If authorized, create target directory if it does not exist.
            # path = (
            #    utils.add_extension(os.path.self.data_path, ".json")
            #    if self.data_path is not None
            #    else self._default_name(names=listdir("."), extension=".json")
            # )
        if not exists(storage_dir) and make_directory:
            makedirs(storage_dir)
        with open(path, "w") as f:
            json.dump(self.record, f, default=utils.json_serialize)

        return self

    def summarize(
        self,
        start_date: Union[datetime.date, str] = datetime.date.min,
        end_date: Union[datetime.date, str] = datetime.date.max,
        aggregate: TimeAggregate.TimeAggregate = TimeAggregate.Day,
    ) -> Dict[str, float]:
        """Sum hours worked for a given week"""

        # Substitute

        # Weeks start on Monday, indexed 1
        return utils.sum_DayLogs(
            start_date=start_date,
            end_date=end_date,
            aggregate=aggregate,
            record=self.record,
        )

    def write_json_summary(
        self,
        output_path: str,
        start_date: Union[datetime.date, str] = datetime.date.min,
        end_date: Union[datetime.date, str] = datetime.date.max,
        aggregate: TimeAggregate.TimeAggregate = TimeAggregate.Day,
    ) -> None:
        """Compute summary and save as JSON instead of returning a dict"""
        summary = self.summarize(
            start_date=start_date, end_date=end_date, aggregate=aggregate
        )
        with open(output_path, "w") as f:
            json.dump(summary, f)

    def write_csv_summary(
        self,
        output_path: str,
        start_date: Union[datetime.date, str] = datetime.date.min,
        end_date: Union[datetime.date, str] = datetime.date.max,
        aggregate: TimeAggregate.TimeAggregate = TimeAggregate.Day,
    ) -> None:
        # Add explicit 0s for unrecorded dates bettwen start and end
        data = self.summarize(
            start_date=start_date, end_date=end_date, aggregate=aggregate
        )
        # Split each datestamp into components
        breakdowns = {"date" : list(data.keys()),**aggregate.string_format.decompose_dict(data.keys()), "hours" : list(data.values())}

        # Write dict to csv with columns year, month, date, hours
        with open(output_path, "w") as f:
            writer = csv.writer(f)
            writer.writerow(breakdowns.keys())
            # Transform into list of rows
            breakdowns = zip(*breakdowns.values())
            for row in breakdowns:
                writer.writerow(row)

    @classmethod
    def from_json(
        cls,
        json_path: str,
        storage_path: Union[str, None] = None,
        storage_name: Union[str, None] = None,
        save: bool = True,
        data_path: Union[str, None] = None,
        output_path : Union[str, None] = None
    ) -> "Timesheet":
        """
        Create a :code:`Timesheet` instance from a path to a JSON representation of an instance's data.

        :param data_path str: Path to a JSON file containing data for the instance, perhaps generated from another instance using :code:`write_json`.
        :param storage_path str: Optional path to :code:`shelve` file in which to store this instance. Defaults to :code:`$HOME/.timesheet/timesheets`
        :param storage_name : Optional name for this instance in the :code:`shelve` file in which it is stored. If already in use, an error is thrown.
        :param save bool: Optional bool determining whether to save on instance creation
        :rtype "Timesheet": Created :code:`Timesheet instance`
        """
        with open(json_path) as f:
            data = json.load(f, object_hook=utils.date_parser)
        instance = cls.__new__(cls)
        instance._constructor(
            data=data,
            storage_path=storage_path,
            storage_name=storage_name,
            save=save,
            data_path=data_path,
            output_path=output_path
        )
        return instance
