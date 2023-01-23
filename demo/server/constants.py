# -*- coding: utf-8 -*-
# Copyright 2023 Tampere University
# This software was developed as a part of the EVCommunities project
# This source code is licensed under the MIT license. See LICENSE in the repository root directory.
# Author(s): Ville Heikkilä <ville.heikkila@tuni.fi>

"""Contains code to handle and document the REST API for the demo."""

OK_RESPONSE_MESSAGE = "The simulation has been started"
BAD_REQUEST_RESPONSE_MESSAGE = "Bad request"
INVALID_RESPONSE_MESSAGE = "Validation error"
SERVER_ERROR_RESPONSE_MESSAGE = "Internal server error"

DEFAULT_BAD_REQUEST_ERROR = "Could not parse JSON contents"
DEFAULT_INVALID_ERROR = "Invalid value for attribute 'StateOfCharge'"
