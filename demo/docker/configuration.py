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

from pathlib import Path
from typing import cast, Dict, List, Union

from demo.tools.tools import FullLogger, EnvironmentVariable, log_exception

LOGGER = FullLogger(__name__)

CONFIGURATION_FILE_PATH: str = cast(str, EnvironmentVariable("CONFIGURATION_FILE_PATH", str, "configuration").value)
CONFIGURATION_FILES = [
    "common.env",
    "mongodb.env",
    "rabbitmq.env"
]

PLATFORM_MANAGER_NAME = "platform-manager"
PLATFORM_MANAGER_IMAGE = "ghcr.io/simcesplatform/platform-manager:latest"
PLATFORM_MANAGER_NETWORKS = [
    "simces_platform_network",
    "simces_rabbitmq_network"
]
PLATFORM_MANAGER_VOLUMES = [
    f"{Path().absolute() / 'configuration'}:/configuration",
    f"{Path().absolute() / 'manifests'}:/manifests:ro",
    f"{Path().absolute() / 'simulations'}:/simulations",
    "simces_simulation_logs:/logs",
    "simces_simulation_resources:/resources",
    "/var/run/docker.sock:/var/run/docker.sock:ro"
]


def get_environment_variables() -> Dict[str, str]:
    """get_environment_variable"""
    variables: Dict[str, str] = {}
    for configuration_file in CONFIGURATION_FILES:
        try:
            with open(Path(CONFIGURATION_FILE_PATH) / configuration_file, mode="r", encoding="utf-8") as conf_file:
                for line in conf_file:
                    stripped_line = line.strip()
                    if not stripped_line or stripped_line.strip().startswith("#"):
                        continue
                    items = stripped_line.split("=")

                    key = items[0].strip()
                    value = "=".join(items[1:]).strip()
                    variables[key] = value

        except IOError as error:
            log_exception(error)

    return variables


PLATFORM_MANAGER_ENVIRONMENT = get_environment_variables()


class ContainerConfiguration:
    """Class for holding the parameters needed when starting a Docker container instance.
    Only parameters needed for starting containers for the simulation platform are included.
    """
    def __init__(self, container_name: str, docker_image: str, environment: Dict[str, str],
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
