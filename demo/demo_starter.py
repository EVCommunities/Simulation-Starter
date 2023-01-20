# -*- coding: utf-8 -*-
# Copyright 2023 Tampere University
# This software was developed as a part of the EVCommunities project
# This source code is licensed under the MIT license. See LICENSE in the repository root directory.
# Author(s): Ville Heikkilä <ville.heikkila@tuni.fi>

"""Creates a configuration for SimCES platform manager and start a container using the configuration."""

from dataclasses import dataclass
from datetime import datetime, timedelta
import json
from typing import List, Optional
import yaml

from demo.tools import FullLogger

LOGGER = FullLogger(__name__)

UTC_Z = "Z"
UTZ_VALUE = "+00:00"

DEFAULT_SIMULATION_NAME = "EVCommunities demo"
DEFAULT_CAR_MODEL = "default"
DEFAULT_EPOCH_LENGTH = 3600
DEFAULT_USER_NAME_PREFIX = "User_"
DEFAULT_STATION_ID_PREFIX = "Station_"

REQUIRED_DEMO_PARAMETERS = [
    "TotalMaxPower",
    "Users",
    "Stations"
]
REQUIRED_USER_PARAMETERS = [
    "CarBatteryCapacity",
    "CarMaxPower",
    "StateOfCharge",
    "TargetStateOfCharge",
    "ArrivalTime",
    "TargetTime"
]
REQUIRED_STATION_PARAMETERS = [
    "MaxPower"
]


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
    users: List[UserParameters]
    stations: List[StationParameters]


def to_datetime(datetime_string: str) -> datetime:
    """to_datetime"""
    return datetime.fromisoformat(datetime_string.replace(UTC_Z, UTZ_VALUE))


def from_datetime(datetime_object: datetime) -> str:
    """from_datetime"""
    return datetime_object.isoformat().replace(UTZ_VALUE, UTC_Z)


def create_simulation_configuration(parameters: DemoParameters) -> str:
    """create_simulation_configuration"""
    earliest_arrival_time = to_datetime(min(user.arrival_time for user in parameters.users))
    latest_leaving_time = to_datetime(max(user.target_time for user in parameters.users))
    simulation_start_time = from_datetime(earliest_arrival_time - timedelta(seconds=parameters.epoch_length))
    max_epoch_count = (latest_leaving_time - earliest_arrival_time).seconds // parameters.epoch_length + 2

    json_configuration = {
        "Simulation": {
            "Name": parameters.name,
            "Description": f"Simulation '{parameters.name}' started by EVCommunities demo.",
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
                    "CarModel": DEFAULT_CAR_MODEL,
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


def load_json_input(json_string: str) -> Optional[DemoParameters]:
    """load_json_input"""
    json_object = json.loads(json_string)
    for required_attribute in REQUIRED_DEMO_PARAMETERS:
        if required_attribute not in json_object:
            LOGGER.warning(f"Missing required attribute: '{required_attribute}'")
            return None

    user_list = json_object["Users"]
    if not user_list:
        LOGGER.warning("There must be at least one user")
        return None
    for user in user_list:
        for required_attribute in REQUIRED_USER_PARAMETERS:
            if required_attribute not in user:
                LOGGER.warning(f"Missing required attribute for a user: '{required_attribute}'")
                return None

    station_list = json_object["Stations"]
    if len(user_list) != len(station_list):
        LOGGER.warning(f"The user and station lists must be of equal length: {len(user_list)} != {len(station_list)}")
        return None
    for station in station_list:
        for required_attribute in REQUIRED_STATION_PARAMETERS:
            if required_attribute not in station:
                LOGGER.warning(f"Missing required attribute for a station: '{required_attribute}'")
                return None

    # TODO: add proper sanity checks for all the input values
    return DemoParameters(
        name=json_object.get("Name", DEFAULT_SIMULATION_NAME),
        total_max_power=json_object["TotalMaxPower"],
        epoch_length=int(json_object.get("EpochLength", DEFAULT_EPOCH_LENGTH)),
        users=[
            UserParameters(
                user_id=id_number,
                user_name=f"{DEFAULT_USER_NAME_PREFIX}{id_number}",
                car_battery_capacity=user["CarBatteryCapacity"],
                car_max_power=user["CarMaxPower"],
                state_of_charge=user["StateOfCharge"],
                target_state_of_charge=user["TargetStateOfCharge"],
                arrival_time=user["ArrivalTime"],
                target_time=user["TargetTime"]
            )
            for id_number, user in enumerate(user_list, start=1)
        ],
        stations=[
            StationParameters(
                station_id=f"{DEFAULT_STATION_ID_PREFIX}{id_number}",
                max_power=station["MaxPower"]
            )
            for id_number, station in enumerate(station_list, start=1)]
    )


def main() -> None:
    """main"""
    with open("test_parameters.json", mode="r", encoding="utf-8") as test_input:
        test_string = test_input.read()

    test_parameters = load_json_input(test_string)
    if test_parameters is None:
        LOGGER.warning("Could not load the parameters for the demo")
        return

    simulation_parameters = create_simulation_configuration(test_parameters)
    with open("test_simulation.yaml", mode="w", encoding="utf-8") as yaml_file:
        yaml_file.write(simulation_parameters)


if __name__ == "__main__":
    main()
