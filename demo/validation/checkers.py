# -*- coding: utf-8 -*-
# Copyright 2023 Tampere University
# This software was developed as a part of the EVCommunities project
# This source code is licensed under the MIT license. See LICENSE in the repository root directory.
# Author(s): Ville Heikkilä <ville.heikkila@tuni.fi>

"""Contains code to validate demo parameters."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Type, Union

from demo.tools import tools

LOGGER = tools.FullLogger(__name__)


class Attributes:
    """Attributes"""
    NAME = "Name"
    EPOCH_LENGTH = "EpochLength"
    TOTAL_MAX_POWER = "TotalMaxPower"
    USERS = "Users"
    STATIONS = "Stations"

    CAR_BATTERY_CAPACITY = "CarBatteryCapacity"
    CAR_MAX_POWER = "CarMaxPower"
    STATE_OF_CHARGE = "StateOfCharge"
    TARGET_STATE_OF_CHARGE = "TargetStateOfCharge"
    ARRIVAL_TIME = "ArrivalTime"
    TARGET_TIME = "TargetTime"

    MAX_POWER = "MaxPower"

    SIMULATION = "Simulation"
    DESCRIPTION = "Description"
    INITIAL_START_TIME = "InitialStartTime"
    MAX_EPOCH_COUNT = "MaxEpochCount"

    COMPONENT = "Component"
    COMPONENTS = "Components"
    IC = "IC"
    INTELLIGENT_CONTROLLER = "IntelligentController"
    USER = "User"
    ID = "Id"
    CAR_MODEL = "CarModel"
    STATION = "Station"

    IC_COMPONENT = f"{IC}{COMPONENT}"
    USER_COMPONENT = USER + COMPONENT
    STATION_COMPONENT = STATION + COMPONENT
    USER_ID = USER + ID
    USER_NAME = USER + NAME
    STATION_ID = STATION + ID


Value = Union[bool, int, float, str]
ValueType = Union[Type[bool], Type[int], Type[float], Type[str], Type[List[Any]], Type[Dict[str, Any]]]
ValueTypeList = List[Type[ValueType]]

EXAMPLE_INPUT_FILE = "example_parameters.json"


def load_example_input() -> Dict[str, Any]:
    """load_example_input"""
    with open(EXAMPLE_INPUT_FILE, mode="r", encoding="utf-8") as example_input:
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
                # return the error string
                return check_value

        # no errors found
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
                # return the error string
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
                # return the error string
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
