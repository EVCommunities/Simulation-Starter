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
    if validity_check is not None:
        LOGGER.warning(validity_check)
        return validity_check

    return DemoParameters(
        name=validation.Checkers.PARAMETER_CHECKER.get_value(Attributes.NAME, json_object),
        total_max_power=json_object[Attributes.TOTAL_MAX_POWER],
        epoch_length=validation.Checkers.PARAMETER_CHECKER.get_value(Attributes.EPOCH_LENGTH, json_object),
        users=tuple(
            UserParameters(
                user_id=id_number,
                user_name=f"{validation.DEFAULT_USER_NAME_PREFIX}{id_number}",
                car_battery_capacity=user[Attributes.CAR_BATTERY_CAPACITY],
                car_max_power=user[Attributes.CAR_MAX_POWER],
                state_of_charge=user[Attributes.STATE_OF_CHARGE],
                target_state_of_charge=user[Attributes.TARGET_STATE_OF_CHARGE],
                arrival_time=user[Attributes.ARRIVAL_TIME],
                target_time=user[Attributes.TARGET_TIME]
            )
            for id_number, user in enumerate(json_object[Attributes.USERS], start=1)
        ),
        stations=tuple(
            StationParameters(
                station_id=f"{validation.DEFAULT_STATION_ID_PREFIX}{id_number}",
                max_power=station[Attributes.MAX_POWER]
            )
            for id_number, station in enumerate(json_object[Attributes.STATIONS], start=1)
        )
    )


def create_simulation_configuration(parameters: DemoParameters) -> str:
    """create_simulation_configuration"""
    earliest_arrival_time = time.to_datetime(min(user.arrival_time for user in parameters.users))
    if earliest_arrival_time is None:
        LOGGER.warning("Could not determine the start time for the simulation")
        return ""
    latest_leaving_time = time.to_datetime(max(user.target_time for user in parameters.users))
    if latest_leaving_time is None:
        LOGGER.warning("Could not determine the end time for the simulation")
        return ""
    simulation_start_time = time.from_datetime(earliest_arrival_time - timedelta(seconds=parameters.epoch_length))
    max_epoch_count = (latest_leaving_time - earliest_arrival_time).seconds // parameters.epoch_length + 2

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
                f"{Attributes.USER}{user.user_id}": {
                    Attributes.USER_ID: user.user_id,
                    Attributes.USER_NAME: user.user_name,
                    Attributes.STATION_ID: parameters.stations[index].station_id,
                    Attributes.ARRIVAL_TIME: user.arrival_time,
                    Attributes.STATE_OF_CHARGE: user.state_of_charge,
                    Attributes.CAR_BATTERY_CAPACITY: user.car_battery_capacity,
                    Attributes.CAR_MODEL: validation.DEFAULT_CAR_MODEL,
                    Attributes.CAR_MAX_POWER: user.car_max_power,
                    Attributes.TARGET_STATE_OF_CHARGE: user.target_state_of_charge,
                    Attributes.TARGET_TIME: user.target_time
                }
                for index, user in enumerate(parameters.users)
            },
            Attributes.STATION_COMPONENT: {
                f"{Attributes.STATION}{station.station_id}": {
                    Attributes.STATION_ID: station.station_id,
                    Attributes.MAX_POWER: station.max_power
                }
                for station in parameters.stations
            }
        }
    }
    return yaml.safe_dump_all(documents=[json_configuration], indent=4, sort_keys=False)


def create_yaml_file(parameters: DemoParameters) -> None:
    """create_yaml_file"""
    simulation_parameters = create_simulation_configuration(parameters)
    with open(
        file=f"{SIMULATION_FILE_PREFIX}{time.get_clean_time_string()}.yaml",
        mode="w",
        encoding="utf-8"
    ) as yaml_file:
        yaml_file.write(simulation_parameters)
