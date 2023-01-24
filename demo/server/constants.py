# -*- coding: utf-8 -*-
# Copyright 2023 Tampere University
# This software was developed as a part of the EVCommunities project
# This source code is licensed under the MIT license. See LICENSE in the repository root directory.
# Author(s): Ville Heikkilä <ville.heikkila@tuni.fi>

"""Contains code to handle and document the REST API for the demo."""

from typing import cast

from demo.tools.tools import EnvironmentVariable


HEADER_PRIVATE_KEY = "private-key"
PRIVATE_KEY_VALUE = cast(str, EnvironmentVariable("SERVER_PRIVATE_KEY", str, "missing").value)

OK_RESPONSE_MESSAGE = "The simulation has been started"
BAD_REQUEST_RESPONSE_MESSAGE = "Bad request"
UNAUTHORIZED_RESPONSE_MESSAGE = "Unauthorized"
INVALID_RESPONSE_MESSAGE = "Validation error"
SERVER_ERROR_RESPONSE_MESSAGE = "Internal server error"

OK_RESPONSE_DESCRIPTION = "Successful simulation start"
BAD_REQUEST_RESPONSE_DESCRIPTION = "Input contained errors"
UNAUTHORIZED_RESPONSE_DESCRIPTION = "Request with incorrect authorization"
INVALID_RESPONSE_DESCRIPTION = "Input could not be validated"
SERVER_ERROR_RESPONSE_DESCRIPTION = "Error while trying to start the simulation"

DEFAULT_BAD_REQUEST_ERROR = "Could not parse JSON contents"
DEFAULT_UNAUTHORIZED_ERROR = "Invalid or missing token"
DEFAULT_INVALID_ERROR = "Invalid value for attribute 'StateOfCharge'"
DEFAULT_SIMULATION_ID = "2023-01-24T12:00:00.000Z"
SIMULATION_CONTAINER_ERROR = "Problem when trying to start simulation containers"
