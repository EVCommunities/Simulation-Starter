# -*- coding: utf-8 -*-
# Copyright 2023 Tampere University
# This software was developed as a part of the EVCommunities project
# This source code is licensed under the MIT license. See LICENSE in the repository root directory.
# Author(s): Ville Heikkilä <ville.heikkila@tuni.fi>

"""Creates a configuration for SimCES platform manager and start a container using the configuration."""

import asyncio
from typing import Optional

from aiohttp_apispec import setup_aiohttp_apispec  # type: ignore
from aiohttp import web

from demo.fetch import fetch
from demo.server import routes
from demo.tools import tools

LOGGER = tools.FullLogger(__name__)


class WebApplication:
    """Site"""
    def __init__(self) -> None:
        self.application: Optional[web.Application] = None


async def start_server(webapp: WebApplication) -> None:
    """start_server"""
    await fetch.start_fetch()

    webapp.application = web.Application()
    webapp.application.add_routes([web.post('/', routes.receive_request)])

    setup_aiohttp_apispec(
        app=webapp.application,
        title="EVCommunities demo API",
        version="v1",
        url="/docs/swagger.json",
        swagger_path="/docs"
    )

    runner = web.AppRunner(webapp.application)
    await runner.setup()
    site = web.TCPSite(runner, port=8111)
    await site.start()

    LOGGER.info("")
    LOGGER.info(f"Started a web server at {site.name}")
    LOGGER.info("Press Ctrl+C to stop:")

    # wait forever
    await asyncio.Event().wait()


async def close(webapp: WebApplication):
    """close"""
    if webapp.application is not None:
        await webapp.application.shutdown()
        await webapp.application.cleanup()


if __name__ == "__main__":
    app = WebApplication()
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(start_server(app))
    except KeyboardInterrupt:
        loop.run_until_complete(close(app))
    finally:
        LOGGER.info("")
        LOGGER.info("Web server stopped")

# TODO: add proper function descriptions
