# -*- coding: utf-8 -*-
# Copyright 2023 Tampere University
# This software was developed as a part of the EVCommunities project
# This source code is licensed under the MIT license. See LICENSE in the repository root directory.
# Author(s): Ville Heikkilä <ville.heikkila@tuni.fi>

"""Contains code to handle and document the REST API for the demo."""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from aiohttp import web
from marshmallow import Schema

from demo.server import constants, schemas


@dataclass
class DemoResponse:
    """DemoResponse"""
    status: int
    schema: Schema
    message: str
    information: Optional[str] = None
    error: Optional[str] = None

    @property
    def content(self) -> Dict[str, Any]:
        """get_content"""
        return (
            {"message": self.message} |
            ({} if self.information is None else {"information": self.information}) |
            ({} if self.error is None else {"error": self.error})
        )

    def get_response(self) -> web.Response:
        """get_response"""
        return web.json_response(
            data=self.content,
            status=self.status
        )


class OkResponse(DemoResponse):
    """OkResponse"""
    def __init__(self, information: Optional[str] = None):
        super().__init__(
            status=web.HTTPOk.status_code,
            schema=schemas.OkResponseSchema(),
            message=constants.OK_RESPONSE_MESSAGE,
            information=information
        )


class BadRequestResponse(DemoResponse):
    """OkResponse"""
    def __init__(self, error: Optional[str] = None):
        super().__init__(
            status=web.HTTPBadRequest.status_code,
            schema=schemas.BadRequestResponseSchema(),
            message=constants.BAD_REQUEST_RESPONSE_MESSAGE,
            error=error
        )


class InvalidResponse(DemoResponse):
    """OkResponse"""
    def __init__(self, error: Optional[str] = None):
        super().__init__(
            status=web.HTTPUnprocessableEntity.status_code,
            schema=schemas.InvalidResponseSchema(),
            message=constants.INVALID_RESPONSE_MESSAGE,
            error=error
        )


class ServerErrorResponse(DemoResponse):
    """OkResponse"""
    def __init__(self, error: Optional[str] = None):
        super().__init__(
            status=web.HTTPInternalServerError.status_code,
            schema=schemas.ServerErrorSchema(),
            message=constants.SERVER_ERROR_RESPONSE_MESSAGE,
            error=error
        )
