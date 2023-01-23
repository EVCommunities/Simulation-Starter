# -*- coding: utf-8 -*-
# Copyright 2023 Tampere University
# This software was developed as a part of the EVCommunities project
# This source code is licensed under the MIT license. See LICENSE in the repository root directory.
# Author(s): Ville Heikkilä <ville.heikkila@tuni.fi>

"""Contains code to handle and document the REST API for the demo."""

from typing import Optional

from aiohttp_apispec import docs, request_schema, response_schema  # type: ignore
from aiohttp import web
from marshmallow import Schema, fields

from demo import simulation
from demo import tools
from demo import validation


class UserSchema(Schema):
    """UserSchema"""
    CarBatteryCapacity = fields.Float(
        required=True,
        metadata={
            "description": "The maximum battery capacity for the car (kWh)",
            "example": validation.EXAMPLE_CAR_BATTERY_CAPACITY
        }
    )
    CarMaxPower = fields.Float(
        required=True,
        metadata={
            "description": "The maximum power that the car can be charged (kW)",
            "example": validation.EXAMPLE_CAR_MAX_POWER
        }
    )
    StateOfCharge = fields.Float(
        required=True,
        metadata={
            "description": "The initial state of charge of the battery at arrival time (0-100)",
            "example": validation.EXAMPLE_STATE_OF_CHARGE
        }
    )
    TargetStateOfCharge = fields.Float(
        required=True,
        metadata={
            "description": "The target state of charge of the battery at leaving time (0-100)",
            "example": validation.EXAMPLE_TARGET_STATE_OF_CHARGE
        }
    )
    ArrivalTime = fields.String(
        required=True,
        metadata={
            "description": "The arrival time in ISO 8601 format",
            "example": validation.EXAMPLE_ARRIVAL_TIME
        }
    )
    TargetTime = fields.String(
        required=True,
        metadata={
            "description": "The leaving time in ISO 8601 format",
            "example": validation.EXAMPLE_TARGET_TIME
        }
    )


class StationSchema(Schema):
    """UserSchema"""
    MaxPower = fields.Float(
        required=True,
        metadata={
            "description": "The maximum power the station can output (kW)",
            "example": validation.EXAMPLE_STATION_MAX_POWER
        }
    )


class DemoRequestSchema(Schema):
    """RequestSchema"""
    Name = fields.Str(
        required=False,
        load_default=validation.DEFAULT_SIMULATION_NAME,
        metadata={"description": "Name of the simulation"}
    )
    TotalMaxPower = fields.Float(
        required=True,
        metadata={
            "description": "The total maximum power the system can produce (kW)",
            "example": validation.EXAMPLE_TOTAL_MAX_POWER
        }
    )
    EpochLength = fields.Integer(
        required=False,
        load_default=validation.DEFAULT_EPOCH_LENGTH,
        metadata={"description": "The epoch length for the simulation (s)"}
    )
    Users = fields.Nested(
        UserSchema(many=True),
        required=True,
        metadata={"description": "The users participating in the simulation"}
    )
    Stations = fields.Nested(
        StationSchema(many=True),
        required=True,
        metadata={"description": "The stations participating in the simulation"}
    )


class OkResponseSchema(Schema):
    """OkResponseSchema"""
    message = fields.String(load_default="The simulation has been started")


class BadRequestResponseSchema(Schema):
    """BadRequestResponseSchema"""
    message = fields.String(load_default="Bad request")
    error = fields.String(load_default="Could not parse JSON contents")


class InvalidResponseSchema(Schema):
    """InvalidResponseSchema"""
    message = fields.String(load_default="Validation error")
    error = fields.String(load_default="Invalid value for attribute 'StateOfCharge'")


class ServerErrorSchema(Schema):
    """ServerErrorSchema"""
    message = fields.String(load_default="Internal server error")


@docs(
    tags=["demo"],
    summary="Start an EV charging demo simulation",
    description=(
        "Start an electric vehicle charging demo simulation using SimCES platform " +
        "by posting the simulation parameters"
    )
)
@request_schema(schema=DemoRequestSchema(), example=validation.load_example_input(), add_to_refs=True)
@response_schema(OkResponseSchema, web.HTTPOk.status_code)
@response_schema(BadRequestResponseSchema, web.HTTPBadRequest.status_code)
@response_schema(InvalidResponseSchema, web.HTTPUnprocessableEntity.status_code)
@response_schema(ServerErrorSchema, web.HTTPInternalServerError.status_code)
async def receive_request(request: web.Request) -> web.Response:
    """receive_request"""
    try:
        content_length: Optional[int] = request.content_length
        if content_length is None or content_length <= 2:
            return web.json_response(
                {
                    "message": "Bad request",
                    "error": "No content found in the message"
                },
                status=web.HTTPBadRequest.status_code
            )
        content = await request.content.read()
        content_str = content.decode(encoding="utf-8")

        json_object = tools.load_json_input(content_str)
        if isinstance(json_object, str):
            return web.json_response(
                {
                    "message": "Bad request",
                    "error": f"Could not parse input: {json_object}"
                },
                status=web.HTTPBadRequest.status_code
            )

        parameters = simulation.validate_json_input(json_object)
        if isinstance(parameters, str):
            return web.json_response(
                {
                    "message": "Validation error",
                    "error": parameters
                },
                status=web.HTTPUnprocessableEntity.status_code
            )

        simulation.create_yaml_file(parameters)
        return web.json_response(
            {
                "message": "The simulation has been started"
            },
            status=web.HTTPOk.status_code
        )

    except Exception as error:  # pylint: disable=broad-except
        tools.log_exception(error)
        return web.json_response(
            {
                "message": "Internal server error"
            },
            status=web.HTTPInternalServerError.status_code
        )
