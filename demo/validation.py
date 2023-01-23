# -*- coding: utf-8 -*-
# Copyright 2023 Tampere University
# This software was developed as a part of the EVCommunities project
# This source code is licensed under the MIT license. See LICENSE in the repository root directory.
# Author(s): Ville Heikkilä <ville.heikkila@tuni.fi>

"""Contains code to validate demo parameters."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Type, Union

from demo import time_tools
from demo import tools

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

EXAMPLE_TOTAL_MAX_POWER = 23.5
EXAMPLE_CAR_BATTERY_CAPACITY = 140.0
EXAMPLE_CAR_MAX_POWER = 12.5
EXAMPLE_STATE_OF_CHARGE = 17.5
EXAMPLE_TARGET_STATE_OF_CHARGE = 85.0
EXAMPLE_ARRIVAL_TIME = "2023-01-23T18:00:00Z"
EXAMPLE_TARGET_TIME = "2020-01-24T07:00:00Z"
EXAMPLE_STATION_MAX_POWER = 15.0

REQUIRED_DEMO_PARAMETERS = (
    "TotalMaxPower",
    "Users",
    "Stations"
)
REQUIRED_USER_PARAMETERS = (
    "CarBatteryCapacity",
    "CarMaxPower",
    "StateOfCharge",
    "TargetStateOfCharge",
    "ArrivalTime",
    "TargetTime"
)
REQUIRED_STATION_PARAMETERS = (
    "MaxPower"
)

Value = Union[bool, int, float, str]
ValueType = Union[Type[bool], Type[int], Type[float], Type[str], Type[List[Any]], Type[Dict[str, Any]]]
ValueTypeList = List[Type[ValueType]]


def load_example_input() -> Dict[str, Any]:
    """load_example_input"""
    with open("example_parameters.json", mode="r", encoding="utf-8") as example_input:
        example_input_string = example_input.read()
    example_input = tools.load_json_input(example_input_string)
    return (
        {} if isinstance(example_input, str)
        else example_input
    )


class BaseCollectionChecker:
    """BaseCollectionChecker"""
    def _check_for_valid_value(self, value: Any, checker: CheckerType, key: Optional[str] = None) -> Optional[str]:
        info_text = "value" if key is None else f"attribute {key}"

        if isinstance(checker, AttributeChecker):
            if not isinstance(value, tuple(checker.allowed_types)):
                return f"Invalid type for {info_text}"
            if not checker.check_function(value):
                LOGGER.info(value)
                return checker.error_description

        elif isinstance(checker, ListChecker) and not isinstance(value, list):
            return f"{info_text} was not a list"
        elif isinstance(checker, DictionaryChecker) and not isinstance(value, dict):
            return f"{info_text} was not a dictionary"

        else:
            check_value = checker.check_for_errors(value)  # type: ignore
            if check_value is not None:
                return check_value

        return None


@dataclass
class AttributeChecker:
    """AttributeChecker"""
    allowed_types: ValueTypeList
    check_function: Callable[[Any], bool]
    error_description: str


@dataclass
class MultiAttributeChecker:
    """MultiAttributeChecker"""
    attribute_names: List[str]
    check_function: Callable[..., bool]
    error_description: str


@dataclass
class ListChecker(BaseCollectionChecker):
    """ListChecker"""
    min_list_length: int
    max_list_length: int
    length_error: str
    item_checker: CheckerType

    def check_for_errors(self, values: List[Any]) -> Optional[str]:
        """check_for_errors"""
        list_length = len(values)
        if list_length < self.min_list_length or list_length > self.max_list_length:
            return self.length_error

        for value in values:
            check_value = self._check_for_valid_value(value, self.item_checker)
            if check_value is not None:
                return check_value

        # no errors found
        return None


@dataclass
class DictionaryChecker(BaseCollectionChecker):
    """DictionaryChecker"""
    required_attributes: List[str]
    default_values: Dict[str, Value]
    attribute_checkers: Dict[str, CheckerType]
    additional_checkers: List[MultiAttributeChecker]

    def get_value(self, key: str, values: Dict[str, Any]) -> Any:
        """get_value"""
        return values.get(key, self.default_values.get(key, None))

    def check_for_errors(self, values: Dict[str, Any]) -> Optional[str]:
        """check_for_errors"""
        for check_type in (
            self._check_for_required_keys,
            self._check_for_valid_attributes,
            self._check_for_additional_conditions
        ):
            check_value = check_type(values)
            if check_value is not None:
                return check_value

        # no errors found
        return None

    def _check_for_required_keys(self, values: Dict[str, Any]) -> Optional[str]:
        for required_key in self.required_attributes:
            if required_key not in values:
                return f"Missing required attribute: '{required_key}'"
        return None

    def _check_for_valid_attributes(self, values: Dict[str, Any]) -> Optional[str]:
        for key, checker in self.attribute_checkers.items():
            value = self.get_value(key, values)
            value_check = self._check_for_valid_value(value, checker, key)
            if value_check is not None:
                return value_check
        return None

    def _check_for_additional_conditions(self, values: Dict[str, Any]) -> Optional[str]:
        for additional_checker in self.additional_checkers:
            target_values = [
                self.get_value(key, values)
                for key in additional_checker.attribute_names
            ]
            if not additional_checker.check_function(*target_values):
                return additional_checker.error_description
        return None


CheckerType = Union[AttributeChecker, ListChecker, DictionaryChecker]


USER_CHECKER = DictionaryChecker(
    required_attributes=[
        "CarBatteryCapacity",
        "CarMaxPower",
        "StateOfCharge",
        "TargetStateOfCharge",
        "ArrivalTime",
        "TargetTime"
    ],
    default_values={},
    attribute_checkers={
        "CarBatteryCapacity": AttributeChecker(
            allowed_types=[int, float],
            check_function=lambda x: 0 < x <= MAXIMUM_ALLOWED_VALUE,
            error_description=f"The max battery capacity must be positive and at most {MAXIMUM_ALLOWED_VALUE}"
        ),
        "CarMaxPower": AttributeChecker(
            allowed_types=[int, float],
            check_function=lambda x: 0 < x <= MAXIMUM_ALLOWED_VALUE,
            error_description=f"The max car charging power must be positive and at most {MAXIMUM_ALLOWED_VALUE}"
        ),
        "StateOfCharge": AttributeChecker(
            allowed_types=[int, float],
            check_function=lambda x: 0 <= x <= 100,
            error_description="The initial state of charge must be between 0 and 100"
        ),
        "TargetStateOfCharge": AttributeChecker(
            allowed_types=[int, float],
            check_function=lambda x: 0 <= x <= 100,
            error_description="The target state of charge must be between 0 and 100"
        ),
        "ArrivalTime": AttributeChecker(
            allowed_types=[str],
            check_function=lambda x: time_tools.to_datetime(x) is not None,
            error_description="The arrival time must be valid ISO 8601 format datetime string"
        ),
        "TargetTime": AttributeChecker(
            allowed_types=[str],
            check_function=lambda x: time_tools.to_datetime(x) is not None,
            error_description="The leaving time must be valid ISO 8601 format datetime string"
        )
    },
    additional_checkers=[
        MultiAttributeChecker(
            attribute_names=[
                "ArrivalTime",
                "TargetTime"
            ],
            check_function=lambda x, y: 0 < time_tools.get_time_difference(x, y) <= MAX_SIMULATION_LENGTH,
            error_description=(
                f"The leaving time must be between 0 and {MAX_SIMULATION_LENGTH // 3600} " +
                "hours later than the arrival time"
            )
        ),
        MultiAttributeChecker(
            attribute_names=[
                "TargetStateOfCharge",
                "StateOfCharge"
            ],
            check_function=lambda x, y: 0 <= x - y <= 100,
            error_description="The target state of charge cannot be smaller the initial state of charge"
        )
    ]
)

STATION_CHECKER = DictionaryChecker(
    required_attributes=[
        "MaxPower"
    ],
    default_values={},
    attribute_checkers={
        "MaxPower": AttributeChecker(
            allowed_types=[int, float],
            check_function=lambda x: 0 < x <= MAXIMUM_ALLOWED_VALUE,
            error_description=f"The max station charging power must be positive and at most {MAXIMUM_ALLOWED_VALUE}"
        )
    },
    additional_checkers=[]
)

PARAMETER_CHECKER = DictionaryChecker(
    required_attributes=[
        "TotalMaxPower",
        "Users",
        "Stations"
    ],
    default_values={
        "Name": DEFAULT_SIMULATION_NAME,
        "EpochLength": DEFAULT_EPOCH_LENGTH
    },
    attribute_checkers={
        "Name": AttributeChecker(
            allowed_types=[str],
            check_function=lambda x: len(x) > 0,
            error_description="The simulation name must contain at least one character"
        ),
        "EpochLength": AttributeChecker(
            allowed_types=[int],
            check_function=lambda x: MIN_EPOCH_LENGTH <= x <= MAX_EPOCH_LENGTH,
            error_description=f"Epoch length must be between {MIN_EPOCH_LENGTH} and {MAX_EPOCH_LENGTH} seconds"
        ),
        "TotalMaxPower": AttributeChecker(
            allowed_types=[int, float],
            check_function=lambda x: 0 <= x <= MAXIMUM_ALLOWED_VALUE,
            error_description=(
                f"The total maximum power charging power must be positive and at most {MAXIMUM_ALLOWED_VALUE}"
            )
        ),
        "Users": ListChecker(
            min_list_length=1,
            max_list_length=MAX_USERS,
            length_error=f"There must be at least one user and no more than {MAX_USERS} users",
            item_checker=USER_CHECKER
        ),
        "Stations": ListChecker(
            min_list_length=1,
            max_list_length=MAX_USERS,
            length_error=f"There must be at least one station and no more than {MAX_USERS} stations",
            item_checker=STATION_CHECKER
        ),
    },
    additional_checkers=[
        MultiAttributeChecker(
            attribute_names=[
                "Users",
                "Stations"
            ],
            check_function=lambda x, y: len(x) == len(y),
            error_description="The number of users and stations must match"
        ),
        MultiAttributeChecker(
            attribute_names=["Users"],
            check_function=(
                lambda x: time_tools.get_time_difference(
                    min(user["ArrivalTime"] for user in x),
                    max(user["TargetTime"] for user in x),
                ) <= MAX_SIMULATION_LENGTH
            ),
            error_description=f"The maximum length for a simulation is {MAX_SIMULATION_LENGTH // 3600} hours"
        )
    ]
)
