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
from demo.docker.runner import ContainerConfiguration, ContainerStarter, get_container_name
from demo.docker import configuration
from demo.server import responses, schemas
from demo.tools import tools
from demo.validation import checkers
from demo.tools.tools import FullLogger

LOGGER = FullLogger(__name__)


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

        yaml_filename = simulation.get_yaml_filename()
        LOGGER.info(yaml_filename)
        simulation.create_yaml_file(parameters, f"simulations/{yaml_filename}")

        container_starter = ContainerStarter()
        container_configuration = await create_container_configuration(yaml_filename)
        if container_configuration is None:
            error_text = "Could not create a configuration for a new Platform Manager container"
            LOGGER.error(error_text)
            return responses.ServerErrorResponse(error_text).get_response()

        container = await container_starter.start_container(container_configuration)
        if container is None:
            error_text = "Could not start a new Platform Manager container"
            LOGGER.error(error_text)
            return responses.ServerErrorResponse(error_text).get_response()

        LOGGER.info(await get_container_name(container))
        return responses.OkResponse(await get_container_name(container)).get_response()

    except Exception as error:  # pylint: disable=broad-except
        tools.log_exception(error)
        return responses.ServerErrorResponse().get_response()


async def create_container_configuration(configuration_filename: str) -> Optional[ContainerConfiguration]:
    """create_container_configuration"""
    manager_environment = {
            **configuration.PLATFORM_MANAGER_ENVIRONMENT,
            **{"SIMULATION_CONFIGURATION_FILE": f"/simulations/{configuration_filename}"}
        }
    LOGGER.info(str(manager_environment))
    LOGGER.info(str(configuration.PLATFORM_MANAGER_NETWORKS))
    LOGGER.info(str(configuration.PLATFORM_MANAGER_VOLUMES))

    return ContainerConfiguration(
        container_name=configuration.PLATFORM_MANAGER_NAME,
        docker_image=configuration.PLATFORM_MANAGER_IMAGE,
        environment=manager_environment,
        networks=configuration.PLATFORM_MANAGER_NETWORKS,
        volumes=configuration.PLATFORM_MANAGER_VOLUMES
    )
