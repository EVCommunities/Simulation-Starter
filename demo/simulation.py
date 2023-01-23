# -*- coding: utf-8 -*-
# Copyright 2023 Tampere University
# This software was developed as a part of the EVCommunities project
# This source code is licensed under the MIT license. See LICENSE in the repository root directory.
# Author(s): Ville Heikkilä <ville.heikkila@tuni.fi>

"""simulation"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Dict, Tuple, Union
import yaml

from demo import time_tools
from demo import tools
from demo import validation

LOGGER = tools.FullLogger(__name__)


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
    validity_check = validation.PARAMETER_CHECKER.check_for_errors(json_object)
    if validity_check is not None:
        LOGGER.warning(validity_check)
        return validity_check

    return DemoParameters(
        name=validation.PARAMETER_CHECKER.get_value("Name", json_object),
        total_max_power=json_object["TotalMaxPower"],
        epoch_length=validation.PARAMETER_CHECKER.get_value("EpochLength", json_object),
        users=tuple(
            UserParameters(
                user_id=id_number,
                user_name=f"{validation.DEFAULT_USER_NAME_PREFIX}{id_number}",
                car_battery_capacity=user["CarBatteryCapacity"],
                car_max_power=user["CarMaxPower"],
                state_of_charge=user["StateOfCharge"],
                target_state_of_charge=user["TargetStateOfCharge"],
                arrival_time=user["ArrivalTime"],
                target_time=user["TargetTime"]
            )
            for id_number, user in enumerate(json_object["Users"], start=1)
        ),
        stations=tuple(
            StationParameters(
                station_id=f"{validation.DEFAULT_STATION_ID_PREFIX}{id_number}",
                max_power=station["MaxPower"]
            )
            for id_number, station in enumerate(json_object["Stations"], start=1)
        )
    )


def create_simulation_configuration(parameters: DemoParameters) -> str:
    """create_simulation_configuration"""
    earliest_arrival_time = time_tools.to_datetime(min(user.arrival_time for user in parameters.users))
    if earliest_arrival_time is None:
        LOGGER.warning("Could not determine the start time for the simulation")
        return ""
    latest_leaving_time = time_tools.to_datetime(max(user.target_time for user in parameters.users))
    if latest_leaving_time is None:
        LOGGER.warning("Could not determine the end time for the simulation")
        return ""
    simulation_start_time = time_tools.from_datetime(earliest_arrival_time - timedelta(seconds=parameters.epoch_length))
    max_epoch_count = (latest_leaving_time - earliest_arrival_time).seconds // parameters.epoch_length + 2

    json_configuration = {
        "Simulation": {
            "Name": parameters.name,
            "Description": f"Simulation '{parameters.name}' started by EVCommunities demo application.",
            "InitialStartTime": simulation_start_time,
            "EpochLength": parameters.epoch_length,
            "MaxEpochCount": max_epoch_count
        },
        "Components": {
            "ICComponent": {
                "IntelligentController": {
                    "TotalMaxPower": parameters.total_max_power
                }
            },
            "UserComponent": {
                f"User{user.user_id}": {
                    "UserId": user.user_id,
                    "UserName": user.user_name,
                    "StationId": parameters.stations[index].station_id,
                    "ArrivalTime": user.arrival_time,
                    "StateOfCharge": user.state_of_charge,
                    "CarBatteryCapacity": user.car_battery_capacity,
                    "CarModel": validation.DEFAULT_CAR_MODEL,
                    "CarMaxPower": user.car_max_power,
                    "TargetStateOfCharge": user.target_state_of_charge,
                    "TargetTime": user.target_time
                }
                for index, user in enumerate(parameters.users)
            },
            "StationComponent": {
                f"Station{station.station_id}": {
                    "StationId": station.station_id,
                    "MaxPower": station.max_power
                }
                for station in parameters.stations
            }
        }
    }
    return yaml.safe_dump_all(documents=[json_configuration], indent=4, sort_keys=False)


def create_yaml_file(parameters: DemoParameters) -> None:
    """create_yaml_file"""
    simulation_parameters = create_simulation_configuration(parameters)
    with open(f"simulation_{time_tools.get_clean_time_string()}.yaml", mode="w", encoding="utf-8") as yaml_file:
        yaml_file.write(simulation_parameters)
