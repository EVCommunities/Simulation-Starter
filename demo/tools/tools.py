# -*- coding: utf-8 -*-
# Copyright 2023 Tampere University
# This software was developed as a part of the EVCommunities project
# This source code is licensed under the MIT license. See LICENSE in the repository root directory.
# Author(s): Ville Heikkilä <ville.heikkila@tuni.fi>
#
# The code is based on https://github.com/simcesplatform/simulation-tools/blob/master/tools/tools.py
# MIT License
# Copyright 2021 Tampere University and VTT Technical Research Centre of Finland

"""Module containing common tools for the use of simulation platform components."""

import asyncio
import functools
import json
import logging
import os
import sys
from types import TracebackType
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union, cast

UTC_Z = "Z"
UTZ_VALUE = "+00:00"

SIMULATION_LOG_LEVEL = "SIMULATION_LOG_LEVEL"
SIMULATION_LOG_FILE = "SIMULATION_LOG_FILE"
SIMULATION_LOG_FORMAT = "SIMULATION_LOG_FORMAT"

EnvironmentVariableValue = Union[bool, int, float, str]
EnvironmentVariableType = Union[Type[bool], Type[int], Type[float], Type[str]]


class EnvironmentVariable:
    """Class for accessing and holding environment variable information."""

    def __init__(self, variable_name: str, variable_type: EnvironmentVariableType,
                 default_value: Optional[EnvironmentVariableValue] = None):
        """Creates a new EnvironmentVariable object that can be used to access the environment variable information."""
        self.__variable_name = variable_name
        self.__variable_type = variable_type
        if default_value is None:
            self.__default_value = default_value
        else:
            self.__default_value = variable_type(default_value)

        self.__value_fetched = False
        self.__value = self.__default_value

    @property
    def variable_name(self) -> str:
        """Return the variable name."""
        return self.__variable_name

    @property
    def variable_type(self) -> EnvironmentVariableType:
        """Returns the variable type."""
        return self.__variable_type

    @property
    def default_value(self) -> Optional[EnvironmentVariableValue]:
        """Returns the default value for the variable."""
        return self.__default_value

    @property
    def value(self) -> Optional[EnvironmentVariableValue]:
        """Returns the value of the environmental value.
           The value is only fetched from the environment at the first call."""
        if not self.__value_fetched:
            new_value = os.environ.get(self.variable_name, None)
            if new_value is None:
                self.__value = self.__default_value
            elif self.variable_type is bool:
                self.__value = new_value.lower() == "true"
            else:
                self.__value = self.variable_type(new_value)
            self.__value_fetched = True

        return self.__value

    def __str__(self) -> str:
        """Returns the string representation of the variable name and value."""
        return f"{self.variable_name}: {str(self.value)}"


EnvironmentVariableSetupType = Union[
    EnvironmentVariable,
    Tuple[str, EnvironmentVariableType],
    Tuple[str, EnvironmentVariableType, Optional[EnvironmentVariableValue]]
]


class EnvironmentVariables:
    """A class for accessing several environment variables."""

    def __init__(self, *variables: EnvironmentVariableSetupType):
        """Creates a collection of EnvironmentVariable objects. The arguments can be either
           instances of EnvironmentVariables, 2-tuples containing the variable name and type,
           or 3-tuples containing the variable name, type, and default value."""
        self.__variables: Dict[str, EnvironmentVariable] = {}
        for variable in variables:
            self.add_variable(variable)

    def add_variable(self, new_variable: EnvironmentVariableSetupType):
        """Adds new variable to the variable list.
           new_variable is either a EnvironmentVariable object or a tuple that can be used to create one."""
        if isinstance(new_variable, tuple):
            # The tuple parts handled explicitly to allow pylance linter to recognize the types.
            if len(new_variable) == 2:
                self.__variables[new_variable[0]] = EnvironmentVariable(new_variable[0], new_variable[1])
            elif len(new_variable) == 3:
                self.__variables[new_variable[0]] = EnvironmentVariable(
                    new_variable[0], new_variable[1], new_variable[2])  # type: ignore
        else:
            self.__variables[new_variable.variable_name] = new_variable

    def get_variables(self) -> List[str]:
        """Returns a list of the registered environment variable names."""
        return list(self.__variables.keys())

    def get_value(self, variable_name: str) -> Optional[EnvironmentVariableValue]:
        """Returns the value of the wanted environmental parameter.
           The value for each parameter is only fetched from the environment at the first call.
           If the given variable is not registered to the EnvironmentVariables instance, returns an empty string."""
        if variable_name in self.__variables:
            return self.__variables[variable_name].value

        LOGGER.info(f"Environment variable {variable_name} not registered.")
        return str()


def load_environmental_variables(*env_variable_specifications: EnvironmentVariableSetupType) \
        -> Dict[str, Optional[EnvironmentVariableValue]]:
    """Returns the realized environmental variable values as a dictionary."""
    env_variables = EnvironmentVariables(*env_variable_specifications)
    return {
        variable_name: env_variables.get_value(variable_name)
        for variable_name in env_variables.get_variables()
    }


DEFAULT_LOGFILE_NAME = "logfile.log"
DEFAULT_LOGFILE_FORMAT = " --- ".join([
    "%(asctime)s",
    "%(levelname)8s",
    "%(message)s"
])
LOGGING_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"
LOGGING_MSEC_FORMAT = "%s.%03d"

COMMON_ENV_VARIABLES = load_environmental_variables(
    (SIMULATION_LOG_LEVEL, int, logging.DEBUG),
    (SIMULATION_LOG_FILE, str, DEFAULT_LOGFILE_NAME),
    (SIMULATION_LOG_FORMAT, str, DEFAULT_LOGFILE_FORMAT)
)


class FullLogger:
    """Logger object that also prints all the output."""
    MESSAGE_LEVEL = {
        logging.DEBUG: "DEBUG",
        logging.INFO: "INFO",
        logging.WARNING: "WARNING",
        logging.ERROR: "ERROR",
        logging.CRITICAL: "CRITICAL"
    }

    def __init__(self, logger_name: str, logger_level: Optional[int] = None, stdout_output: bool = True):
        """Creates a logger object with the given name and log level and that writes the logs to a file.
           The log filename is determined by the environment variable SIMULATION_LOG_FILE. If argument
           logger_level is None, the logging level is determined by the environment variable SIMULATION_LOG_LEVEL.
           If stdout_output is True, then the log messages are also printed on the stdout device.
        """
        self.__logger = get_logger(logger_name, log_level=logger_level)

        if stdout_output:
            console_handler = logging.StreamHandler(sys.stdout)
            logger_formatter = self.__logger.handlers[0].formatter
            if logger_formatter is not None:
                console_handler.setFormatter(logger_formatter)
            self.__logger.addHandler(console_handler)

    def debug(self, message: str, *args: object):
        """Writes log message with DEBUG logging level."""
        self.__logger.debug(message, *args)

    def info(self, message: str, *args: object,):
        """Writes log message with INFO logging level."""
        self.__logger.info(message, *args)

    def warning(self, message: str, *args: object):
        """Writes log message with WARNING logging level."""
        self.__logger.warning(message, *args)

    def error(self, message: str, *args: object):
        """Writes log message with ERROR logging level."""
        self.__logger.error(message, *args)

    def critical(self, message: str, *args: object):
        """Writes log message with CRITICAL logging level."""
        self.__logger.critical(message, *args)

    @property
    def level(self) -> int:
        """Returns the logging level of the logger."""
        return self.__logger.level

    @level.setter
    def level(self, log_level: int):
        """Sets the logging level of the logger to log_level."""
        self.__logger.setLevel(log_level)

    @property
    def logger_name(self) -> str:
        """Returns the logger name."""
        return self.__logger.name

    @property
    def logger(self):
        """Returns the Logger object."""
        return self.__logger


def get_logger(logger_name: str, log_level: Optional[int] = None) -> logging.Logger:
    """Returns a Logger object that logs the messages to a file.
       The logging level and the log filename are determined by the environment variables
       SIMULATION_LOG_LEVEL and SIMULATION_LOG_FILE."""
    new_logger = logging.getLogger(logger_name)
    if log_level is None:
        new_logger_level = COMMON_ENV_VARIABLES[SIMULATION_LOG_LEVEL]
    else:
        new_logger_level = log_level
    if isinstance(new_logger_level, int):
        new_logger.setLevel(new_logger_level)

    log_file_name = COMMON_ENV_VARIABLES[SIMULATION_LOG_FILE]
    if isinstance(log_file_name, str):
        log_formatter = logging.Formatter(cast(str, COMMON_ENV_VARIABLES[SIMULATION_LOG_FORMAT]))
        log_formatter.default_time_format = LOGGING_DATE_FORMAT
        log_formatter.default_msec_format = LOGGING_MSEC_FORMAT

        log_file_handler = logging.FileHandler(log_file_name)
        log_file_handler.setFormatter(log_formatter)
        new_logger.addHandler(log_file_handler)

    return new_logger


LOGGER = FullLogger(__name__)


def traceback_to_str(traceback: Optional[TracebackType], indentation: str = "") -> str:
    """Return a string representation of the given traceback."""
    if isinstance(traceback, TracebackType):
        if traceback.tb_next is not None:
            traceback_next = "\n" + traceback_to_str(traceback.tb_next, indentation)
        else:
            traceback_next = ""
        filename: str = traceback.tb_frame.f_code.co_filename
        line_number: int = traceback.tb_lineno
        return f"{indentation}file: {filename}, line: {line_number}{traceback_next}"
    return ""


DEFAULT_EXCEPTION_LOG_START = "Encountered unhandled exception:"


def log_exception(
    error: BaseException,
    logger_call: Callable[[str], None] = LOGGER.error,
    log_start: str = DEFAULT_EXCEPTION_LOG_START
) -> None:
    """Logs information from the given exception."""
    traceback_text: str = "  Traceback: "
    traceback_str: str = traceback_to_str(error.__traceback__, " " * len(traceback_text))[len(traceback_text):]
    logger_call(
        f"{log_start}\n" +
        f"  Type: {type(error).__name__}\n" +
        f"  Message: {error}\n" +
        f"{traceback_text}{traceback_str}"
    )


def async_wrap(synchronous_function: Callable[..., Any]):
    """Wraps a synchronous function to an asynchronous coroutine."""
    @functools.wraps(synchronous_function)
    async def run(
            *args: ...,
            event_loop: Optional[asyncio.events.AbstractEventLoop] = None,
            executor: Any = None,
            **kwargs: ...):
        if event_loop is None:
            event_loop = asyncio.get_event_loop()
        partial_function = functools.partial(synchronous_function, *args, **kwargs)
        return await event_loop.run_in_executor(executor, partial_function)
    return run


def handle_async_exception(_: Any, context: Any):
    """Prints out any unhandled exceptions from async tasks."""
    # pylint: disable=unused-argument
    if isinstance(context, dict):
        exception = context.get("exception", None)  # type: ignore
        if isinstance(exception, SystemExit):
            LOGGER.error("SystemExit caught by async exception handler.")
        elif isinstance(exception, RuntimeError):
            LOGGER.error(f"RuntimeError caught by async exception handler: {exception}")
        elif isinstance(exception, BaseException):
            log_exception(exception, LOGGER.warning, "Async exception:")
        else:
            LOGGER.warning(f"Async exception: {str(exception)}")  # type: ignore
    else:
        LOGGER.warning(f"Exception in async task: {str(context)}")


def load_json_input(json_string: str) -> Union[Dict[str, Any], str]:
    """load_json_input"""
    try:
        json_object: Union[Any, Dict[str, Any]] = json.loads(json_string)
    except ValueError as error:
        log_exception(error)
        return str(error)

    if not isinstance(json_object, dict):
        return "Could not parse JSON object from the input"

    return json_object
