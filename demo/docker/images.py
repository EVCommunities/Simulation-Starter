# -*- coding: utf-8 -*-
# Copyright 2023 Tampere University
# This software was developed as a part of the EVCommunities project
# This source code is licensed under the MIT license. See LICENSE in the repository root directory.
# Author(s): Ville Heikkilä <ville.heikkila@tuni.fi>

"""This module contains the functionality for pulling Docker images."""

from pathlib import Path

from aiodocker import Docker, DockerError

from demo.tools.tools import FullLogger, log_exception
from demo.docker.configuration import CONFIGURATION_FILE_PATH

LOGGER = FullLogger(__name__)

IMAGE_FILE = "docker_images.txt"


async def pull_images() -> None:
    """get_environment_variable"""
    docker_client = Docker()
    try:
        with open(Path(CONFIGURATION_FILE_PATH) / IMAGE_FILE, mode="r", encoding="utf-8") as image_file:
            for line in image_file:
                stripped_line = line.strip()
                if not stripped_line or stripped_line.strip().startswith("#"):
                    continue

                pull_output = docker_client.pull(from_image=stripped_line, stream=True)  # type: ignore
                async for log in pull_output:
                    status = log.get("status", None)
                    if status is not None and (":" in status or "from" in status):
                        LOGGER.info(status)

    except (IOError, DockerError) as error:
        log_exception(error)
    finally:
        await docker_client.close()
