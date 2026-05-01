"""Unified time synchronization for Pocket Option API."""

import datetime
import time
from datetime import timedelta, timezone


class TimeSync:
    """Unified server timestamp tracker and drift compensator."""

    def __init__(self):
        self._server_timestamp = None
        self._local_reference = None
        self._expiration_minutes = 1
        self._timezone_offset = timedelta(seconds=self._get_local_timezone_offset())

    @staticmethod
    def _get_local_timezone_offset():
        local_time = datetime.datetime.now()
        utc_time = datetime.datetime.utcnow()
        return (local_time - utc_time).total_seconds()

    @property
    def server_timestamp(self):
        return self._server_timestamp

    @server_timestamp.setter
    def server_timestamp(self, timestamp):
        self._server_timestamp = float(timestamp) if timestamp is not None else None
        self._local_reference = time.time() if timestamp is not None else None

    @property
    def server_timestamps(self):
        return self.server_timestamp

    @server_timestamps.setter
    def server_timestamps(self, timestamp):
        self.server_timestamp = timestamp

    @property
    def server_datetime(self):
        if self.server_timestamp is None:
            return None
        return datetime.datetime.fromtimestamp(self.server_timestamp)

    @property
    def expiration_minutes(self):
        return self._expiration_minutes

    @expiration_minutes.setter
    def expiration_minutes(self, minutes):
        self._expiration_minutes = int(minutes)

    @property
    def expiration_time(self):
        return self.expiration_minutes

    @expiration_time.setter
    def expiration_time(self, minutes):
        self.expiration_minutes = minutes

    @property
    def expiration_datetime(self):
        if self.server_datetime is None:
            return None
        return self.server_datetime + timedelta(minutes=self.expiration_minutes)

    @property
    def expiration_timestamp(self):
        expiration_datetime = self.expiration_datetime
        if expiration_datetime is None:
            return None
        return time.mktime(expiration_datetime.timetuple())

    def synchronize(self, server_time):
        self.server_timestamp = server_time

    def get_synced_time(self):
        if self.server_timestamp is None or self._local_reference is None:
            raise ValueError("Time has not been synchronized yet.")
        elapsed_time = time.time() - self._local_reference
        return self.server_timestamp + elapsed_time

    def get_synced_datetime(self):
        synced_time_seconds = self.get_synced_time()
        rounded_time_seconds = round(synced_time_seconds)
        synced_datetime_utc = datetime.datetime.fromtimestamp(rounded_time_seconds, tz=timezone.utc)
        return synced_datetime_utc + self._timezone_offset

    @property
    def synced_datetime(self):
        return self.get_synced_datetime()

    def update_sync(self, new_server_time):
        self.synchronize(new_server_time)
