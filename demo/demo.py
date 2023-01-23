# -*- coding: utf-8 -*-
# Copyright 2023 Tampere University
# This software was developed as a part of the EVCommunities project
# This source code is licensed under the MIT license. See LICENSE in the repository root directory.
# Author(s): Ville Heikkilä <ville.heikkila@tuni.fi>

"""Creates a configuration for SimCES platform manager and start a container using the configuration."""

from aiohttp_apispec import setup_aiohttp_apispec  # type: ignore
from aiohttp import web

from demo import server
from demo import tools

LOGGER = tools.FullLogger(__name__)


def start_server():
    """start_server"""
    app: web.Application = web.Application()
    app.add_routes([web.post('/', server.receive_request)])

    setup_aiohttp_apispec(
        app=app,
        title="EVCommunities demo API",
        version="v1",
        url="/docs/swagger.json",
        swagger_path="/docs"
    )

    web.run_app(app, port=8081)  # type: ignore


if __name__ == "__main__":
    start_server()

# TODO: add proper function descriptions
