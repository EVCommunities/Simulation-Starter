# -*- coding: utf-8 -*-
# Copyright 2023 Tampere University
# This software was developed as a part of the EVCommunities project
# This source code is licensed under the MIT license. See LICENSE in the repository root directory.
# Author(s): Ville Heikkilä <ville.heikkila@tuni.fi>

"""Module containing datetime tools for the use of simulation platform components."""

import datetime
from typing import Optional

UTC_Z = "Z"
UTZ_VALUE = "+00:00"

DAY_TO_SECONDS = 86400
SECOND_TO_MICROSECONDS = 1000000


def to_datetime(datetime_string: str) -> Optional[datetime.datetime]:
    """to_datetime"""
    try:
        return datetime.datetime.fromisoformat(datetime_string.replace(UTC_Z, UTZ_VALUE)) \
                                .astimezone(datetime.timezone.utc)
    except ValueError:
        return None


def get_time_difference(datetime_string_begin: str, datetime_string_end: str) -> int:
    """get_time_difference"""
    datetime_begin = to_datetime(datetime_string_begin)
    datetime_end = to_datetime(datetime_string_end)
    return (
        -1 if datetime_begin is None or datetime_end is None
        else int((datetime_end - datetime_begin).total_seconds())
    )


def from_datetime(datetime_object: datetime.datetime) -> str:
    """from_datetime"""
    return datetime_object.isoformat().replace(UTZ_VALUE, UTC_Z)


def get_clean_time_string() -> str:
    """get_clean_time_string"""
    now = datetime.datetime.utcnow()
    return now.isoformat().replace("-", "").replace(":", "").replace("T", "-").replace(".", "-")


def to_microseconds(duration: datetime.timedelta) -> int:
    """to_microseconds"""
    return (duration.days * DAY_TO_SECONDS + duration.seconds) * SECOND_TO_MICROSECONDS + duration.microseconds


def to_sanitized_datetime(datetime_string: str, duration: datetime.timedelta) -> Optional[datetime.datetime]:
    """to_sanitized_datetime"""
    if duration.total_seconds() == 0:
        return None

    original_datetime = to_datetime(datetime_string)
    if original_datetime is None:
        return None

    day_start = original_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
    duration_microseconds = to_microseconds(duration)
    microseconds_in_original = to_microseconds(original_datetime - day_start)
    skew_microseconds = microseconds_in_original % duration_microseconds

    if skew_microseconds == 0:
        return original_datetime
    if skew_microseconds < duration_microseconds // 2:
        return original_datetime - datetime.timedelta(microseconds=skew_microseconds)
    return original_datetime + datetime.timedelta(microseconds=duration_microseconds - skew_microseconds)


def to_sanitized_datetime_string(datetime_string: str, duration: datetime.timedelta) -> str:
    """to_sanitized_datetime"""
    sanitized_datetime = to_sanitized_datetime(datetime_string, duration)
    if sanitized_datetime is None:
        return ""

    return from_datetime(sanitized_datetime)
