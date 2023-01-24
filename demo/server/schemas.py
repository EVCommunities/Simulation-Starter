# -*- coding: utf-8 -*-
# Copyright 2023 Tampere University
# This software was developed as a part of the EVCommunities project
# This source code is licensed under the MIT license. See LICENSE in the repository root directory.
# Author(s): Ville Heikkilä <ville.heikkila@tuni.fi>

"""Contains code to handle and document the REST API for the demo."""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from marshmallow import Schema, fields

from demo.server import constants
from demo.validation import validation
from demo.validation.checkers import Value


@dataclass
class SchemaMetadata:
    """SchemaMetadata"""
    description: str
    example: Optional[Value] = None

    @property
    def metadata(self) -> Dict[str, Any]:
        """metadata"""
        return (
            {"description": self.description} |
            {} if self.example is None else {"example": self.example}
        )


class UserSchema(Schema):
    """UserSchema"""
    CarBatteryCapacity = fields.Float(
        required=True,
        metadata=SchemaMetadata(
            "The maximum battery capacity for the car (kWh)",
            validation.EXAMPLE_CAR_BATTERY_CAPACITY
        ).metadata
    )
    CarMaxPower = fields.Float(
        required=True,
        metadata=SchemaMetadata(
            "The maximum power that the car can be charged (kW)",
            validation.EXAMPLE_CAR_MAX_POWER
        ).metadata
    )
    StateOfCharge = fields.Float(
        required=True,
        metadata=SchemaMetadata(
            "The initial state of charge of the battery at arrival time (0-100)",
            validation.EXAMPLE_STATE_OF_CHARGE
        ).metadata
    )
    TargetStateOfCharge = fields.Float(
        required=True,
        metadata=SchemaMetadata(
            "The target state of charge of the battery at leaving time (0-100)",
            validation.EXAMPLE_TARGET_STATE_OF_CHARGE
        ).metadata
    )
    ArrivalTime = fields.String(
        required=True,
        metadata=SchemaMetadata(
            "The arrival time in ISO 8601 format",
            validation.EXAMPLE_ARRIVAL_TIME
        ).metadata
    )
    TargetTime = fields.String(
        required=True,
        metadata=SchemaMetadata(
            "The leaving time in ISO 8601 format",
            validation.EXAMPLE_TARGET_TIME
        ).metadata
    )


class StationSchema(Schema):
    """UserSchema"""
    MaxPower = fields.Float(
        required=True,
        metadata=SchemaMetadata(
            "The maximum power the station can output (kW)",
            validation.EXAMPLE_STATION_MAX_POWER
        ).metadata
    )


class DemoRequestSchema(Schema):
    """RequestSchema"""
    Name = fields.Str(
        required=False,
        load_default=validation.DEFAULT_SIMULATION_NAME,
        metadata=SchemaMetadata("Name of the simulation").metadata
    )
    TotalMaxPower = fields.Float(
        required=True,
        metadata=SchemaMetadata(
            "The total maximum power the system can produce (kW)",
            validation.EXAMPLE_TOTAL_MAX_POWER
        ).metadata
    )
    EpochLength = fields.Integer(
        required=False,
        load_default=validation.DEFAULT_EPOCH_LENGTH,
        metadata=SchemaMetadata("The epoch length for the simulation (s)").metadata
    )
    Users = fields.Nested(
        UserSchema(many=True),
        required=True,
        metadata=SchemaMetadata("The users participating in the simulation").metadata
    )
    Stations = fields.Nested(
        StationSchema(many=True),
        required=True,
        metadata=SchemaMetadata("The stations participating in the simulation").metadata
    )


class OkResponseSchema(Schema):
    """OkResponseSchema"""
    message = fields.String(load_default=constants.OK_RESPONSE_MESSAGE)
    simulation_id = fields.String(load_default=constants.DEFAULT_SIMULATION_ID)


class BadRequestResponseSchema(Schema):
    """BadRequestResponseSchema"""
    message = fields.String(load_default=constants.BAD_REQUEST_RESPONSE_MESSAGE)
    error = fields.String(load_default=constants.DEFAULT_BAD_REQUEST_ERROR)


class InvalidResponseSchema(Schema):
    """InvalidResponseSchema"""
    message = fields.String(load_default=constants.INVALID_RESPONSE_MESSAGE)
    error = fields.String(load_default=constants.DEFAULT_INVALID_ERROR)


class ServerErrorSchema(Schema):
    """ServerErrorSchema"""
    message = fields.String(load_default=constants.SERVER_ERROR_RESPONSE_MESSAGE)
    error = fields.String(load_default=constants.SIMULATION_CONTAINER_ERROR)
