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


def to_datetime(datetime_string: str) -> Optional[datetime.datetime]:
    """to_datetime"""
    try:
        return datetime.datetime.fromisoformat(datetime_string.replace(UTC_Z, UTZ_VALUE))
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
