# -*- coding: utf-8 -*-
# Copyright 2023 Tampere University
# This software was developed as a part of the EVCommunities project
# This source code is licensed under the MIT license. See LICENSE in the repository root directory.
# Author(s): Ville Heikkilä <ville.heikkila@tuni.fi>

"""Contains code to handle and document the REST API for the demo."""

from typing import Optional

from aiohttp_apispec import docs, request_schema, response_schema  # type: ignore
from aiohttp import web

from demo import simulation
from demo.server import responses, schemas
from demo.tools import tools
from demo.validation import checkers


@docs(
    tags=["demo"],
    summary="Start an EV charging demo simulation",
    description=(
        "Start an electric vehicle charging demo simulation using SimCES platform " +
        "by posting the simulation parameters"
    )
)
@request_schema(
    schema=schemas.DemoRequestSchema(),
    example=checkers.load_example_input(),
    add_to_refs=True
)
@response_schema(responses.OkResponse().schema, responses.OkResponse().status)
@response_schema(responses.BadRequestResponse().schema, responses.BadRequestResponse().status)
@response_schema(responses.InvalidResponse().schema, responses.InvalidResponse().status)
@response_schema(responses.ServerErrorResponse().schema, responses.ServerErrorResponse().status)
async def receive_request(request: web.Request) -> web.Response:
    """receive_request"""
    try:
        content_length: Optional[int] = request.content_length
        if content_length is None or content_length <= 2:
            return responses.BadRequestResponse("No content found in the message").get_response()

        content = await request.content.read()
        content_str = content.decode(encoding="utf-8")

        json_object = tools.load_json_input(content_str)
        if isinstance(json_object, str):
            return responses.BadRequestResponse(f"Could not parse input: {json_object}").get_response()

        parameters = simulation.validate_json_input(json_object)
        if isinstance(parameters, str):
            return responses.InvalidResponse(parameters).get_response()

        simulation.create_yaml_file(parameters)
        return responses.OkResponse().get_response()

    except Exception as error:  # pylint: disable=broad-except
        tools.log_exception(error)
        return responses.ServerErrorResponse().get_response()
