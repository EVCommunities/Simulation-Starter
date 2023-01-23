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

from demo.docker.configuration import ContainerConfiguration
from demo.tools.tools import FullLogger, log_exception

LOGGER = FullLogger(__name__)


async def get_container_name(container: DockerContainer) -> str:
    """Returns the name of the given Docker container."""
    # Use a hack to get the container name because the aiodocker does not make it otherwise available.
    if "Name" not in container._container:  # pylint: disable=protected-access  # type: ignore
        await container.show()  # type: ignore
    return container._container.get("Name", "")[1:]  # pylint: disable=protected-access  # type: ignore


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
        async def container_name(container: DockerContainer) -> str:
            name = await get_container_name(container)
            return name[len(self.PREFIX_START):][:self.PREFIX_DIGITS]

        running_containers: List[DockerContainer] = await self.__docker_client.containers.list(all=True)  # type: ignore
        simulation_indexes = {
            int(await container_name(container))
            for container in running_containers
            if self.__prefix_pattern.match(await get_container_name(container)) is not None
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

    async def start_container(self, configuration: ContainerConfiguration) -> Optional[DockerContainer]:
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
                return new_container

            return None
