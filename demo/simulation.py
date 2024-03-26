# -*- coding: utf-8 -*-
# Copyright 2023 Tampere University
# This software was developed as a part of the EVCommunities project
# This source code is licensed under the MIT license. See LICENSE in the repository root directory.
# Author(s): Ville Heikkilä <ville.heikkila@tuni.fi>

"""simulation"""

from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Dict, Tuple, Union
import yaml

from demo.tools import time, tools
from demo.validation import validation
from demo.validation.checkers import Attributes

LOGGER = tools.FullLogger(__name__)

SIMULATION_FILE_PREFIX = "simulation_"


@dataclass
class StationParameters:
    """StationParameters"""
    station_id: str
    max_power: float


@dataclass
class UserParameters:
    """UserParameters"""
    user_id: int
    user_name: str
    car_battery_capacity: float
    car_max_power: float
    state_of_charge: float
    target_state_of_charge: float
    station_id: str
    arrival_time: str
    target_time: str


@dataclass
class DemoParameters:
    """DemoParameters"""
    name: str
    total_max_power: float
    epoch_length: int
    users: Tuple[UserParameters]
    stations: Tuple[StationParameters]


def validate_json_input(json_object: Dict[str, Any]) -> Union[DemoParameters, str]:
    """validate_json_input"""
    validity_check = validation.Checkers.PARAMETER_CHECKER.check_for_errors(json_object)
    validation.Checkers.reset_generators()
    if validity_check is not None:
        LOGGER.warning(validity_check)
        return validity_check

    return DemoParameters(
        name=validation.Checkers.PARAMETER_CHECKER.get_value(Attributes.NAME, json_object),
        total_max_power=json_object[Attributes.TOTAL_MAX_POWER],
        epoch_length=validation.Checkers.PARAMETER_CHECKER.get_value(Attributes.EPOCH_LENGTH, json_object),
        users=tuple(
            UserParameters(
                user_id=user[Attributes.USER_ID],
                user_name=user[Attributes.USER_NAME],
                car_battery_capacity=user[Attributes.CAR_BATTERY_CAPACITY],
                car_max_power=user[Attributes.CAR_MAX_POWER],
                state_of_charge=user[Attributes.STATE_OF_CHARGE],
                target_state_of_charge=user[Attributes.TARGET_STATE_OF_CHARGE],
                station_id=user[Attributes.STATION_ID],
                arrival_time=user[Attributes.ARRIVAL_TIME],
                target_time=user[Attributes.TARGET_TIME]
            )
            for user in json_object[Attributes.USERS]
        ),  # type: ignore
        stations=tuple(
            StationParameters(
                station_id=station[Attributes.STATION_ID],
                max_power=station[Attributes.MAX_POWER]
            )
            for station in json_object[Attributes.STATIONS]
        )  # type: ignore
    )


def create_simulation_configuration(parameters: DemoParameters) -> str:
    """create_simulation_configuration"""
    epoch_duration = timedelta(seconds=parameters.epoch_length)
    earliest_arrival_time = time.to_sanitized_datetime(
        datetime_string=min(user.arrival_time for user in parameters.users),
        duration=epoch_duration
    )
    if earliest_arrival_time is None:
        LOGGER.warning("Could not determine the start time for the simulation")
        return ""
    latest_leaving_time = time.to_sanitized_datetime(
        datetime_string=max(user.target_time for user in parameters.users),
        duration=epoch_duration
    )
    if latest_leaving_time is None:
        LOGGER.warning("Could not determine the end time for the simulation")
        return ""
    simulation_start_time = time.from_datetime(earliest_arrival_time - epoch_duration)
    max_epoch_count = int((latest_leaving_time - earliest_arrival_time).total_seconds()) // parameters.epoch_length + 2

    json_configuration = {
        Attributes.SIMULATION: {
            Attributes.NAME: parameters.name,
            Attributes.DESCRIPTION: f"Simulation '{parameters.name}' started by EVCommunities demo application.",
            Attributes.INITIAL_START_TIME: simulation_start_time,
            Attributes.EPOCH_LENGTH: parameters.epoch_length,
            Attributes.MAX_EPOCH_COUNT: max_epoch_count
        },
        Attributes.COMPONENTS: {
            Attributes.IC_COMPONENT: {
                Attributes.INTELLIGENT_CONTROLLER: {
                    Attributes.TOTAL_MAX_POWER: parameters.total_max_power
                }
            },
            Attributes.USER_COMPONENT: {
                user.user_name: {
                    Attributes.USER_ID: user.user_id,
                    Attributes.USER_NAME: user.user_name,
                    Attributes.STATION_ID: user.station_id,
                    Attributes.ARRIVAL_TIME: time.to_sanitized_datetime_string(user.arrival_time, epoch_duration),
                    Attributes.STATE_OF_CHARGE: user.state_of_charge,
                    Attributes.CAR_BATTERY_CAPACITY: user.car_battery_capacity,
                    Attributes.CAR_MODEL: validation.DEFAULT_CAR_MODEL,
                    Attributes.CAR_MAX_POWER: user.car_max_power,
                    Attributes.TARGET_STATE_OF_CHARGE: user.target_state_of_charge,
                    Attributes.TARGET_TIME: time.to_sanitized_datetime_string(user.target_time, epoch_duration)
                }
                for user in parameters.users
            },
            Attributes.STATION_COMPONENT: {
                f"{Attributes.STATION}_{station.station_id}": {
                    Attributes.STATION_ID: station.station_id,
                    Attributes.MAX_POWER: station.max_power
                }
                for station in parameters.stations
            }
        }
    }
    return yaml.safe_dump_all(documents=[json_configuration], indent=4, sort_keys=False)


def get_yaml_filename() -> str:
    """get_yaml_filename"""
    return f"{SIMULATION_FILE_PREFIX}{time.get_clean_time_string()}.yaml"


def create_yaml_file(parameters: DemoParameters, filename: str) -> None:
    """create_yaml_file"""
    simulation_parameters = create_simulation_configuration(parameters)
    with open(
        file=filename,
        mode="w",
        encoding="utf-8"
    ) as yaml_file:
        yaml_file.write(simulation_parameters)
