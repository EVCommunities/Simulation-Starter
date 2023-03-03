# -*- coding: utf-8 -*-
# Copyright 2023 Tampere University
# This software was developed as a part of the EVCommunities project
# This source code is licensed under the MIT license. See LICENSE in the repository root directory.
# Author(s): Ville Heikkilä <ville.heikkila@tuni.fi>

"""Contains code to validate demo parameters."""

from typing import Generator

from demo.tools import time
from demo.tools import tools
from demo.validation.checkers import Attributes, AttributeChecker, DictionaryChecker, ListChecker, MultiAttributeChecker

LOGGER = tools.FullLogger(__name__)

MAXIMUM_ALLOWED_VALUE = 10000
MAX_USERS = 20
MIN_EPOCH_LENGTH = 60
MAX_EPOCH_LENGTH = 7200
MAX_SIMULATION_LENGTH = 7 * 24 * 3600

DEFAULT_SIMULATION_NAME = "EVCommunities demo"
DEFAULT_CAR_MODEL = "default"
DEFAULT_EPOCH_LENGTH = 3600
DEFAULT_USER_NAME_PREFIX = "User_"
DEFAULT_STATION_ID_PREFIX = "Station_"
DEFAULT_USER_ID = 1
DEFAULT_USER_NAME = f"{DEFAULT_USER_NAME_PREFIX}{DEFAULT_USER_ID}"

EXAMPLE_TOTAL_MAX_POWER = 23.5
EXAMPLE_CAR_BATTERY_CAPACITY = 140.0
EXAMPLE_CAR_MAX_POWER = 12.5
EXAMPLE_STATE_OF_CHARGE = 17.5
EXAMPLE_TARGET_STATE_OF_CHARGE = 85.0
EXAMPLE_ARRIVAL_TIME = "2023-01-23T18:00:00Z"
EXAMPLE_TARGET_TIME = "2020-01-24T07:00:00Z"
EXAMPLE_STATION_MAX_POWER = 15.0
EXAMPLE_STATION_ID = "1"


def user_id_generator(start: int = 1) -> Generator[int, None, None]:
    """user_id_generator"""
    id_number: int = start
    while True:
        yield id_number
        id_number += 1


def user_name_generator(start: int = 1) -> Generator[str, None, None]:
    """user_name_generator"""
    id_number: int = start
    while True:
        yield f"{DEFAULT_USER_NAME_PREFIX}{id_number}"
        id_number += 1


class Checkers:
    """ParameterCheckers"""
    USER_CHECKER = DictionaryChecker(
        required_attributes=[
            Attributes.CAR_BATTERY_CAPACITY,
            Attributes.CAR_MAX_POWER,
            Attributes.STATE_OF_CHARGE,
            Attributes.TARGET_STATE_OF_CHARGE,
            Attributes.ARRIVAL_TIME,
            Attributes.TARGET_TIME,
            Attributes.STATION_ID
        ],
        default_values={
            Attributes.USER_ID: user_id_generator(),
            Attributes.USER_NAME: user_name_generator()
        },
        attribute_checkers={
            Attributes.CAR_BATTERY_CAPACITY: AttributeChecker(
                allowed_types=[int, float],
                check_function=lambda x: 0 < x <= MAXIMUM_ALLOWED_VALUE,
                error_description=f"The max battery capacity must be positive and at most {MAXIMUM_ALLOWED_VALUE}"
            ),
            Attributes.CAR_MAX_POWER: AttributeChecker(
                allowed_types=[int, float],
                check_function=lambda x: 0 < x <= MAXIMUM_ALLOWED_VALUE,
                error_description=f"The max car charging power must be positive and at most {MAXIMUM_ALLOWED_VALUE}"
            ),
            Attributes.STATE_OF_CHARGE: AttributeChecker(
                allowed_types=[int, float],
                check_function=lambda x: 0 <= x <= 100,
                error_description="The initial state of charge must be between 0 and 100"
            ),
            Attributes.TARGET_STATE_OF_CHARGE: AttributeChecker(
                allowed_types=[int, float],
                check_function=lambda x: 0 <= x <= 100,
                error_description="The target state of charge must be between 0 and 100"
            ),
            Attributes.ARRIVAL_TIME: AttributeChecker(
                allowed_types=[str],
                check_function=lambda x: time.to_datetime(x) is not None,
                error_description="The arrival time must be valid ISO 8601 format datetime string"
            ),
            Attributes.TARGET_TIME: AttributeChecker(
                allowed_types=[str],
                check_function=lambda x: time.to_datetime(x) is not None,
                error_description="The leaving time must be valid ISO 8601 format datetime string"
            ),
            Attributes.STATION_ID: AttributeChecker(
                allowed_types=[str],
                check_function=lambda x: len(x) > 0,
                error_description="The station id for a user must not be empty"
            ),
            Attributes.USER_ID: AttributeChecker(
                allowed_types=[int],
                check_function=lambda x: x > 0,
                error_description="The user id must be a positive integer"
            ),
            Attributes.USER_NAME: AttributeChecker(
                allowed_types=[str],
                check_function=lambda x: len(x) > 0,
                error_description="The user name must not be empty"
            )
        },
        additional_checkers=[
            MultiAttributeChecker(
                attribute_names=[Attributes.ARRIVAL_TIME, Attributes.TARGET_TIME],
                check_function=lambda x, y: 0 < time.get_time_difference(x, y) <= MAX_SIMULATION_LENGTH,
                error_description=(
                    f"The leaving time must be between 0 and {MAX_SIMULATION_LENGTH // 3600} " +
                    "hours later than the arrival time"
                )
            ),
            MultiAttributeChecker(
                attribute_names=[Attributes.TARGET_STATE_OF_CHARGE, Attributes.STATE_OF_CHARGE],
                check_function=lambda x, y: 0 <= x - y <= 100,
                error_description="The target state of charge cannot be smaller the initial state of charge"
            )
        ]
    )

    STATION_CHECKER = DictionaryChecker(
        required_attributes=[
            Attributes.MAX_POWER,
            Attributes.STATION_ID
        ],
        default_values={},
        attribute_checkers={
            Attributes.MAX_POWER: AttributeChecker(
                allowed_types=[int, float],
                check_function=lambda x: 0 < x <= MAXIMUM_ALLOWED_VALUE,
                error_description=f"The max station charging power must be positive and at most {MAXIMUM_ALLOWED_VALUE}"
            ),
            Attributes.STATION_ID: AttributeChecker(
                allowed_types=[str],
                check_function=lambda x: len(x) > 0,
                error_description="The station id must not be empty"
            )
        },
        additional_checkers=[]
    )

    PARAMETER_CHECKER = DictionaryChecker(
        required_attributes=[
            Attributes.TOTAL_MAX_POWER,
            Attributes.USERS,
            Attributes.STATIONS
        ],
        default_values={
            Attributes.NAME: DEFAULT_SIMULATION_NAME,
            Attributes.EPOCH_LENGTH: DEFAULT_EPOCH_LENGTH
        },
        attribute_checkers={
            Attributes.NAME: AttributeChecker(
                allowed_types=[str],
                check_function=lambda x: len(x) > 0,
                error_description="The simulation name must contain at least one character"
            ),
            Attributes.EPOCH_LENGTH: AttributeChecker(
                allowed_types=[int],
                check_function=lambda x: MIN_EPOCH_LENGTH <= x <= MAX_EPOCH_LENGTH,
                error_description=f"Epoch length must be between {MIN_EPOCH_LENGTH} and {MAX_EPOCH_LENGTH} seconds"
            ),
            Attributes.TOTAL_MAX_POWER: AttributeChecker(
                allowed_types=[int, float],
                check_function=lambda x: 0 <= x <= MAXIMUM_ALLOWED_VALUE,
                error_description=(
                    f"The total maximum power charging power must be positive and at most {MAXIMUM_ALLOWED_VALUE}"
                )
            ),
            Attributes.USERS: ListChecker(
                min_list_length=1,
                max_list_length=MAX_USERS,
                length_error=f"There must be at least one user and no more than {MAX_USERS} users",
                item_checker=USER_CHECKER
            ),
            Attributes.STATIONS: ListChecker(
                min_list_length=1,
                max_list_length=MAX_USERS,
                length_error=f"There must be at least one station and no more than {MAX_USERS} stations",
                item_checker=STATION_CHECKER
            ),
        },
        additional_checkers=[
            MultiAttributeChecker(
                attribute_names=[Attributes.USERS],
                check_function=lambda users: (
                    len([user[Attributes.USER_ID] for user in users]) ==
                    len(set(user[Attributes.USER_ID] for user in users))
                ),
                error_description="All users must have an unique user id"
            ),
            MultiAttributeChecker(
                attribute_names=[Attributes.USERS],
                check_function=lambda users: (
                    len([user[Attributes.USER_NAME] for user in users]) ==
                    len(set(user[Attributes.USER_NAME] for user in users))
                ),
                error_description="All users must have an unique user name"
            ),
            MultiAttributeChecker(
                attribute_names=[Attributes.USERS, Attributes.STATIONS],
                check_function=lambda users, stations: all(
                    user[Attributes.STATION_ID] in [station[Attributes.STATION_ID] for station in stations]
                    for user in users
                ),
                error_description="All stations that users are connected to must be part of the simulation"
            ),
            MultiAttributeChecker(
                attribute_names=[Attributes.USERS],
                check_function=(
                    lambda users: time.get_time_difference(
                        min(user[Attributes.ARRIVAL_TIME] for user in users),
                        max(user[Attributes.TARGET_TIME] for user in users)
                    ) <= MAX_SIMULATION_LENGTH
                ),
                error_description=f"The maximum length for a simulation is {MAX_SIMULATION_LENGTH // 3600} hours"
            ),
            MultiAttributeChecker(
                attribute_names=[Attributes.USERS],
                check_function=lambda users: all(
                    all(
                        (
                            same_station_user[Attributes.ARRIVAL_TIME] >= user[Attributes.TARGET_TIME] or
                            same_station_user[Attributes.TARGET_TIME] <= user[Attributes.ARRIVAL_TIME]
                        )
                        for same_station_index, same_station_user in enumerate(users)
                        if (
                            same_station_index != index and
                            same_station_user[Attributes.STATION_ID] == user[Attributes.STATION_ID]
                        )
                    )
                    for index, user in enumerate(users)
                ),
                error_description="Multiple users cannot be connected to the same station at the same time"
            )
        ]
    )

    @classmethod
    def reset_generators(cls) -> None:
        """reset_generators"""
        cls.USER_CHECKER.default_values = {
            Attributes.USER_ID: user_id_generator(),
            Attributes.USER_NAME: user_name_generator()
        }
