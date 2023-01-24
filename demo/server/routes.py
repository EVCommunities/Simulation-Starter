# -*- coding: utf-8 -*-
# Copyright 2023 Tampere University
# This software was developed as a part of the EVCommunities project
# This source code is licensed under the MIT license. See LICENSE in the repository root directory.
# Author(s): Ville Heikkilä <ville.heikkila@tuni.fi>

"""Contains code to handle and document the REST API for the demo."""

from typing import AsyncGenerator, List, Optional

from aiohttp_apispec import docs, request_schema, response_schema  # type: ignore
from aiohttp import web

from demo import simulation
from demo.docker.runner import ContainerConfiguration, ContainerStarter, get_container_name
from demo.docker import configuration
from demo.server import constants, responses, schemas
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
    ),
    parameters=schemas.get_request_header_parameters()
)
@request_schema(
    schema=schemas.DemoRequestSchema(),
    example=checkers.load_example_input(),
    add_to_refs=True
)
@response_schema(**responses.OkResponse().get_details())
@response_schema(**responses.BadRequestResponse().get_details())
@response_schema(**responses.UnauthorizedResponse().get_details())
@response_schema(**responses.InvalidResponse().get_details())
@response_schema(**responses.ServerErrorResponse().get_details())
async def receive_request(request: web.Request) -> web.Response:
    """receive_request"""
    try:
        private_key = request.headers.get(constants.HEADER_PRIVATE_KEY, None)
        if private_key is None or private_key != constants.PRIVATE_KEY_VALUE:
            LOGGER.warning(f"Invalid token used: {private_key}")
            return responses.UnauthorizedResponse().get_response()

        content_length: Optional[int] = request.content_length
        if content_length is None or content_length <= 2:
            LOGGER.info("No content found in the request")
            return responses.BadRequestResponse("No content found in the request").get_response()

        content = await request.content.read()
        content_str = content.decode(encoding="utf-8")

        json_object = tools.load_json_input(content_str)
        if isinstance(json_object, str):
            return responses.BadRequestResponse(f"Could not parse input: {json_object}").get_response()

        parameters = simulation.validate_json_input(json_object)
        if isinstance(parameters, str):
            return responses.InvalidResponse(parameters).get_response()

        yaml_filename = simulation.get_yaml_filename()
        simulation.create_yaml_file(parameters, f"simulations/{yaml_filename}")
        LOGGER.debug(f"Created new simulation configuration to file 'simulations/{yaml_filename}'")

        container_starter = ContainerStarter()
        container_configuration = await create_container_configuration(yaml_filename)
        if container_configuration is None:
            error_text = "Could not create a configuration for a new Platform Manager container"
            LOGGER.error(error_text)
            await container_starter.close()
            return responses.ServerErrorResponse(error_text).get_response()

        container = await container_starter.start_container(container_configuration)
        if container is None:
            error_text = "Could not start a new Platform Manager container"
            LOGGER.error(error_text)
            await container_starter.close()
            return responses.ServerErrorResponse(error_text).get_response()

        LOGGER.debug(f"Started container {await get_container_name(container)}")
        container_logs = container.log(stdout=True, follow=True)  # type: ignore
        stored_logs: List[str] = []
        if isinstance(container_logs, AsyncGenerator):
            async for item in container_logs:
                if "started successfully" in item:
                    simulation_id = item.split(": ")[-1].strip()
                    LOGGER.info(f"Simulation started with id: {simulation_id}")
                    await container_starter.close()
                    return responses.OkResponse(simulation_id).get_response()
                stored_logs.append(item)

        stored_logs_str = "\n".join(["---".join(log.split("---")[1:]).strip() for log in stored_logs])
        LOGGER.warning(f"Platform manager could not start the simulation:\n{stored_logs_str}")
        await container_starter.close()
        return responses.ServerErrorResponse(constants.SIMULATION_CONTAINER_ERROR).get_response()

    except Exception as error:  # pylint: disable=broad-except
        tools.log_exception(error)
        if "container_starter" in locals():
            await container_starter.close()  # type: ignore
        return responses.ServerErrorResponse(str(error)).get_response()


async def create_container_configuration(configuration_filename: str) -> Optional[ContainerConfiguration]:
    """create_container_configuration"""
    manager_environment = {
        **configuration.PLATFORM_MANAGER_ENVIRONMENT,
        **{"SIMULATION_CONFIGURATION_FILE": f"/simulations/{configuration_filename}"}
    }

    return ContainerConfiguration(
        container_name=configuration.PLATFORM_MANAGER_NAME,
        docker_image=configuration.PLATFORM_MANAGER_IMAGE,
        environment=manager_environment,
        networks=configuration.PLATFORM_MANAGER_NETWORKS,
        volumes=configuration.PLATFORM_MANAGER_VOLUMES
    )
