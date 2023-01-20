# -*- coding: utf-8 -*-
# Copyright 2023 Tampere University
# This software was developed as a part of the EVCommunities project
# This source code is licensed under the MIT license. See LICENSE in the repository root directory.
# Author(s): Ville Heikkilä <ville.heikkila@tuni.fi>
#
# The code is based on https://github.com/simcesplatform/Platform-Manager/blob/master/platform_manager/docker_runner.py
# MIT License
# Copyright 2021 Tampere University and VTT Technical Research Centre of Finland

"""This module contains the functionality for starting Docker containers."""

import asyncio
import re
from typing import Any, Dict, List, Optional, Union

from aiodocker import Docker
from aiodocker.containers import DockerContainer
from aiohttp.client_exceptions import ClientError

from demo.tools import EnvironmentVariableValue, FullLogger, log_exception

LOGGER = FullLogger(__name__)


def get_container_name(container: DockerContainer) -> str:
    """Returns the name of the given Docker container."""
    # Use a hack to get the container name because the aiodocker does not make it otherwise available.
    return container._container.get("Names", [" "])[0][1:]  # pylint: disable=protected-access  # type: ignore


class ContainerConfiguration:
    """Class for holding the parameters needed when starting a Docker container instance.
    Only parameters needed for starting containers for the simulation platform are included.
    """
    def __init__(self, container_name: str, docker_image: str, environment: Dict[str, EnvironmentVariableValue],
                 networks: Union[str, List[str]], volumes: Union[str, List[str]]):
        """
        Sets up the parameters for the Docker container configuration to the format required by aiodocker.
        - container_name:    the container name
        - docker_image:      the Docker image name including a tag
        - environment:       the environment variables and their values
        - networks:          the names of the Docker networks for the container
        - volumes:           the volume names and the target paths, format: <volume_name>:<target_path>[rw|ro]
        """
        self.__name = container_name
        self.__image = docker_image
        self.__environment = [
            "=".join([
                variable_name, str(variable_value)
            ])
            for variable_name, variable_value in environment.items()
        ]

        if isinstance(networks, str):
            self.__networks = [networks]
        else:
            self.__networks = networks

        if isinstance(volumes, str):
            self.__volumes = [volumes]
        else:
            self.__volumes = volumes

    @property
    def container_name(self) -> str:
        """The container name."""
        return self.__name

    @property
    def image(self) -> str:
        """The Docker image for the container."""
        return self.__image

    @property
    def environment(self) -> List[str]:
        """The environment variables for the Docker container."""
        return self.__environment

    @property
    def networks(self) -> List[str]:
        """The Docker networks for the Docker container."""
        return self.__networks

    @property
    def volumes(self) -> List[str]:
        """The Docker volumes for the Docker container."""
        return self.__volumes


class ContainerStarter:
    """Class for starting the Docker components for a simulation."""
    PREFIX_DIGITS = 2
    PREFIX_START = "Sim"

    def __init__(self):
        """Sets up the Docker client."""
        self.__container_prefix = \
            f"{self.__class__.PREFIX_START}{{index:0{self.__class__.PREFIX_DIGITS}d}}_"  # Sim{index:02d}_
        self.__prefix_pattern = \
            re.compile(f"{self.__class__.PREFIX_START}([0-9]{{{self.__class__.PREFIX_DIGITS}}})_")  # Sim([0-9]{2})_

        # the docker client using aiodocker library
        self.__docker_client = Docker()

        self.__lock = asyncio.Lock()

    async def close(self):
        """Closes the Docker client connection."""
        await self.__docker_client.close()

    async def get_next_simulation_index(self) -> Union[int, None]:
        """
        Returns the next available index for the container name prefix for a new simulation.
        If all possible indexes are already in use, returns None.
        """
        running_containers: List[DockerContainer] = await self.__docker_client.containers.list()  # type: ignore
        simulation_indexes = {
            int(get_container_name(container)[len(self.__class__.PREFIX_START):][:self.__class__.PREFIX_DIGITS])
            for container in running_containers
            if self.__prefix_pattern.match(get_container_name(container)) is not None
        }

        if simulation_indexes:
            index_limit = 10 ** self.__class__.PREFIX_DIGITS
            available_indexes = set(range(index_limit)) - simulation_indexes
            if available_indexes:
                return min(available_indexes)
            # no available simulation indexes available
            return None

        # no previous simulation containers found
        return 0

    async def create_container(self, container_name: str, container_configuration: ContainerConfiguration) \
            -> Optional[DockerContainer]:
        """
        Creates and returns a Docker container according to the given configuration. Uses the 'aiodocker' library.
        """
        # The API specification for Docker Engine: https://docs.docker.com/engine/api/v1.40/
        LOGGER.debug(f"Creating container: {container_name}")
        if container_configuration.networks:
            first_network_name = container_configuration.networks[0]
            first_network: Dict[str, Any] = {first_network_name: {}}
        else:
            first_network = {}

        try:
            container = await self.__docker_client.containers.create(  # type: ignore
                name=container_name,
                config={
                    "Image": container_configuration.image,
                    "Env": container_configuration.environment,
                    "HostConfig": {
                        "Binds": container_configuration.volumes,
                        "AutoRemove": True
                    },
                    "NetworkingConfig": {
                        "EndpointsConfig": first_network
                    }
                }
            )

            # When creating a container, it can only be connected to one network.
            # The other networks have to be connected separately.
            for other_network_name in container_configuration.networks[1:]:
                other_network = await self.__docker_client.networks.get(net_specs=other_network_name)
                await other_network.connect(
                    config={
                        "Container": container_name,
                        "EndpointConfig": {}
                    }
                )

            return container

        except ClientError as client_error:
            log_exception(client_error)
            return None

    async def start_container(self, configuration: ContainerConfiguration) -> Union[str, None]:
        """
        Starts a Docker container with the given configuration parameters.
        Returns the names of the container or None, if there was a problem starting the container.
        """
        async with self.__lock:
            simulation_index = await self.get_next_simulation_index()
            if simulation_index is None:
                LOGGER.warning("No free simulation indexes. Wait until a simulation run has finished.")
                return None

            full_container_name = (
                self.__container_prefix.format(index=simulation_index) +
                configuration.container_name
            )

            new_container = await self.create_container(full_container_name, configuration)
            if isinstance(new_container, DockerContainer):
                await new_container.start()  # type: ignore
                return full_container_name

            return None
