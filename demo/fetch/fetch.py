# -*- coding: utf-8 -*-
# Copyright 2023 Tampere University
# This software was developed as a part of the EVCommunities project
# This source code is licensed under the MIT license. See LICENSE in the repository root directory.
# Author(s): Ville Heikkilä <ville.heikkila@tuni.fi>
#
# The code is based on https://github.com/simcesplatform/Platform-Manager/blob/master/fetch/fetch.py
# MIT License
# Copyright 2021 Tampere University and VTT Technical Research Centre of Finland

"""
This module fetches files from GitLab or GitHub repositories.
"""

from asyncio import run as asyncio_run, TimeoutError as AsyncioTimeoutError
from dataclasses import dataclass, field
from pathlib import Path
from re import compile as re_compile
from urllib.parse import quote
from typing import Any, cast, Dict, List, Optional, Tuple, Union
from yaml import safe_load, YAMLError

from aiohttp import ClientSession, ClientTimeout
from aiohttp.client_exceptions import ClientError

from demo.tools.tools import EnvironmentVariable, FullLogger, async_wrap, log_exception

LOGGER = FullLogger(__name__)

HTTP_TIMEOUT = 10.0

GITHUB = "GitHub"
GITLAB = "GitLab"

DEFAULT_FILENAME = "component_manifest.yml"
DEFAULT_BRANCH = "master"

GITHUB_HOST_FOR_RAW = "https://{access_token:}raw.githubusercontent.com"
DEFAULT_GITLAB_HOST = "https://gitlab.com"

SERVER_CONFIG_TYPE = "Type"
SERVER_CONFIG_HOST = "Host"
SERVER_CONFIG_CERTIFICATE = "Certificate"
SERVER_CONFIG_ACCESS_TOKEN = "AccessToken"
SERVER_CONFIG_REPOSITORIES = "Repositories"
REPOSITORY_CONFIG_FILE = "File"
REPOSITORY_CONFIG_BRANCH = "Branch"

ENV_VARIABLE_PATTERN = re_compile(r"\${.*}")

MANIFEST_FOLDER = "MANIFEST_FOLDER"
SERVER_CONFIG_FOLDER = "SERVER_CONFIG_FOLDER"


@dataclass
class RepositoryFileConfiguration:
    """
    Data class for holding the parameters regarding the repository name and
    the name and branch of the file that is to fetched.
    - repository_name: the full name of the repository, i.e. including also the user/organization name
    - filename: the name of the file to be fetched, defaults to "component_manifest.yml"
    - branch: the name of the branch or tag where the file can be found, default to "master"
    """
    repository_name: str
    filename: Optional[str] = None
    branch: Optional[str] = None


@dataclass
class RepositoryServerConfiguration:
    """
    Data class for holding the parameters for server containing simulation component repositories
    - repository_type: the server type, either GitHub or GitLab
    - repositories: the list of the considered repositories
    - host: the host address for the server
    - certificate: whether to check the SSL certificate when making requests to the server
    - access_token: access token to be used when making requests to the server
    """
    repository_type: str
    repositories: List[RepositoryFileConfiguration] = field(default_factory=list)
    host: Optional[str] = None
    certificate: Optional[bool] = None
    access_token: Optional[str] = None


def evaluate_environment_variable(string_value: str) -> str:
    """
    If the given string is in format "${ENV_VARIABLE_NAME}", evaluates and returns
    the corresponding environmental variable value if it is set.
    Otherwise, returns the given string without changes.
    """
    if ENV_VARIABLE_PATTERN.match(string_value) is None:
        return string_value

    env_variable_name = string_value[2:-1]
    env_variable_value = EnvironmentVariable(env_variable_name, str, None).value
    if env_variable_value is None:
        return string_value
    return env_variable_value  # type: ignore


def create_repository_configurations_from_dict(configuration: Dict[str, Any]) -> List[RepositoryFileConfiguration]:
    """Creates a list of repository configurations from the given dictionary."""
    repository_list: List[RepositoryFileConfiguration] = []
    for repository_name, repository_configuration in configuration.items():

        # The default filename and branch for the repository.
        if repository_configuration is None:
            repository_list.append(RepositoryFileConfiguration(repository_name))

        elif isinstance(repository_configuration, dict):
            filename = repository_configuration.get(REPOSITORY_CONFIG_FILE, None)  # type: ignore
            if not isinstance(filename, str):
                if filename is not None:
                    LOGGER.warning(f"Ignoring non-string value for filename for repository: {repository_name}")
                filename = None

            branch = repository_configuration.get(REPOSITORY_CONFIG_BRANCH, None)  # type: ignore
            if not isinstance(branch, str):
                if branch is not None:
                    LOGGER.warning(f"Ignoring non-string value for branch for repository: {repository_name}")
                branch = None

            repository_list.append(
                RepositoryFileConfiguration(
                    repository_name=repository_name,
                    filename=filename,
                    branch=branch
                )
            )

        else:
            LOGGER.warning(f"Ignoring repository: {repository_name}")

    return repository_list


def create_repository_configurations_from_list(configuration: List[Any]) -> List[RepositoryFileConfiguration]:
    """Creates a list of repository configurations from the given list."""
    repository_list: List[RepositoryFileConfiguration] = []
    for repository in configuration:

        # The default filename and branch for the repository.
        if isinstance(repository, str):
            repository_list.append(RepositoryFileConfiguration(repository))

        elif isinstance(repository, dict):
            repository_list += create_repository_configurations_from_dict(repository)  # type: ignore

        else:
            LOGGER.warning(f"Ignoring non supported value '{repository}' for a repository")

    return repository_list


def create_repository_configurations(configuration: Any) -> List[RepositoryFileConfiguration]:
    """Creates a list of repository configurations from the given configuration."""
    if isinstance(configuration, list):
        return create_repository_configurations_from_list(configuration)  # type: ignore
    if isinstance(configuration, dict):
        return create_repository_configurations_from_dict(configuration)  # type: ignore
    return []


def load_repository_parameters_from_yaml(yaml_filename: Union[str, Path]) \
        -> Optional[RepositoryServerConfiguration]:
    """
    Loads and returns the repositories and their parameters that are used to fetch component type manifests.
    """
    try:
        with open(yaml_filename, mode="r", encoding="UTF-8") as yaml_file:
            yaml_content: Dict[str, Any] = safe_load(yaml_file)

        if not isinstance(yaml_content, dict):  # type: ignore
            LOGGER.warning(f"The server configuration in '{yaml_filename}' for repositories is not a dictionary")
            return None

        repository_type: str = str(yaml_content.get(SERVER_CONFIG_TYPE, ""))
        if repository_type not in (GITHUB, GITLAB):
            LOGGER.warning(f"Unknown repository type '{repository_type}' found in '{yaml_filename}'")
            return None

        repositories: Any = yaml_content.get(SERVER_CONFIG_REPOSITORIES, None)
        considered_repositories = create_repository_configurations(repositories)

        host = yaml_content.get(SERVER_CONFIG_HOST, None)
        if repository_type == GITHUB and host is not None:
            LOGGER.info(f"Host name for GitHub repositories will be ignored in '{yaml_filename}'")
            host = None
        elif host is not None and not isinstance(host, str):
            LOGGER.warning(f"Ignoring a non-string host name in '{yaml_filename}'")
            host = None

        certificate = yaml_content.get(SERVER_CONFIG_CERTIFICATE, None)
        if certificate is not None and not isinstance(certificate, bool):
            LOGGER.warning(f"Ignoring non-boolean value for certificate in '{yaml_filename}'")
            certificate = None

        access_token = yaml_content.get(SERVER_CONFIG_ACCESS_TOKEN, None)
        if access_token is not None and not isinstance(access_token, str):
            LOGGER.warning(f"Ignoring non-string value for access token in '{yaml_filename}'")
            access_token = None
        elif isinstance(access_token, str):
            access_token = evaluate_environment_variable(access_token)
            # empty access token is considered to be the same as no access token given at all
            if access_token == "":
                access_token = None

        return RepositoryServerConfiguration(
            repository_type=cast(str, repository_type),
            repositories=considered_repositories,
            host=host,
            certificate=certificate,
            access_token=access_token
        )

    except (OSError, TypeError, YAMLError) as yaml_error:
        LOGGER.error(
            f"Encountered '{type(yaml_error).__name__}' exception when loading server parameters from file " +
            f"'{yaml_filename}': {yaml_error}"
        )
        return None


def create_folder(target_folder: Path):
    """Creates the target folder if it does not exist yet."""
    try:
        if target_folder.exists():
            if not target_folder.is_dir():
                LOGGER.warning(f"'{target_folder}' is not a directory")
            return

        resolved_target = target_folder.resolve()
        if resolved_target.parent != resolved_target and not resolved_target.parent.is_dir():
            create_folder(resolved_target.parent)
        resolved_target.mkdir()
        # change the permission to allow read-write access to the folder for all users
        resolved_target.chmod(0o777)

    except OSError as os_error:
        LOGGER.error(f"Received '{type(os_error).__name__}' while creating folder '{target_folder}': {os_error}")


def write_file(contents: str, filename: Path):
    """Writes the given text to a file with the given filename. Overwrites any previous file."""
    try:
        create_folder(filename.parent)
        with open(filename, mode="w", encoding="UTF-8") as target_file:
            target_file.write(contents)
        # change the permission to allow read-write access to the file for all users
        filename.chmod(0o666)

    except OSError as file_error:
        LOGGER.error(f"Received '{type(file_error).__name__}' when writing file '{filename}: {file_error}")


def get_github_request_params(
        repository_name: str, filename: str = DEFAULT_FILENAME,
        branch: str = DEFAULT_BRANCH, access_token: Optional[str] = None) -> Dict[str, Any]:
    """
    Returns a dictionary containing the required parameters for a aiohttp request
    to fetch the given file from the given GitHub repository.
    """
    if access_token is None:
        host = GITHUB_HOST_FOR_RAW.format(access_token="")
    else:
        host = GITHUB_HOST_FOR_RAW.format(access_token="".join([access_token, "@"]))

    return {
        "url": "/".join([
            host,
            repository_name,
            branch,
            filename
        ])
    }


def get_gitlab_request_params(
        repository_name: str, host_name: str, filename: str = DEFAULT_FILENAME,
        branch: str = DEFAULT_BRANCH, check_certificate: bool = True,
        access_token: Optional[str] = None) -> Dict[str, Any]:
    """
    Returns a dictionary containing the required parameters for a aiohttp request
    to fetch the given file from the given GitLab repository.
    """
    request_params = {
        "url": "/".join([
            host_name,
            "api",
            "v4",
            "projects",
            quote(repository_name, safe=""),
            "repository",
            "files",
            quote(filename, safe=""),
            "raw"
        ]),
        "params": {
            "ref": branch
        },
        "ssl": check_certificate
    }
    if access_token is not None:
        request_params["headers"] = {
            "Private-Token": access_token
        }

    return request_params


def get_repository_request_params(
        repository_name: str, repository_type: str, filename: Optional[str] = None,
        branch: Optional[str] = None, check_certificate: Optional[bool] = None,
        host_name: Optional[str] = None, access_token: Optional[str] = None) \
        -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Returns a 2-tuple in which the first element is a dictionary containing the required parameters
    for a aiohttp request to fetch the given file from the given repository. The second element in the
    returned tuple is the filename for the file to be fetched.
    Supported repository types are GitHub and GitLab.
    """
    if filename is None:
        filename = DEFAULT_FILENAME
    if branch is None:
        branch = DEFAULT_BRANCH
    if check_certificate is None:
        check_certificate = True

    if repository_type == GITHUB:
        return (
            get_github_request_params(
                repository_name=repository_name,
                filename=filename,
                branch=branch,
                access_token=access_token),
            filename
        )

    if repository_type == GITLAB:
        if host_name is None:
            host_name = DEFAULT_GITLAB_HOST
        return (
            get_gitlab_request_params(
                repository_name=repository_name,
                host_name=host_name,
                filename=filename,
                branch=branch,
                check_certificate=check_certificate,
                access_token=access_token),
            filename
        )

    LOGGER.error(f"Repository type '{repository_type}' is not supported")
    return None, None


def get_output_filename(output_folder: str, repository_type: str,
                        repository_name: str, filename: str) -> Path:
    """Returns the output filename for the file fetched from a repository."""
    return (
        Path(output_folder) / Path(repository_type.lower())
        / Path(Path(repository_name).name) / Path(Path(filename).name)
    )


async def start_fetch():
    """Fetches files from remote repositories."""
    component_file = "configuration/components.yml"
    output_folder = "manifests"

    server_configuration = load_repository_parameters_from_yaml(component_file)
    if server_configuration is None:
        LOGGER.warning("No repository configurations found in the configuration file")
        return

    async with ClientSession(timeout=ClientTimeout(total=HTTP_TIMEOUT)) as session:  # type: ignore
        for repository in server_configuration.repositories:
            request_params, filename = get_repository_request_params(
                repository_name=repository.repository_name,
                repository_type=server_configuration.repository_type,
                filename=repository.filename,
                branch=repository.branch,
                check_certificate=server_configuration.certificate,
                host_name=server_configuration.host,
                access_token=server_configuration.access_token
            )
            if request_params is None or filename is None:
                continue

            LOGGER.info(
                f"Fetching file '{filename}' from {server_configuration.repository_type} " +
                f"repository {repository.repository_name}"
            )
            try:
                async with session.get(**request_params) as response:
                    html_contents = await response.text()

                    if response.status == 200:
                        target_filename = get_output_filename(
                            output_folder=output_folder,
                            repository_type=server_configuration.repository_type,
                            repository_name=repository.repository_name,
                            filename=filename
                        )
                        await async_wrap(write_file)(html_contents, target_filename)

                    else:
                        LOGGER.warning(
                            f"Repository: {repository}: received status '{response.status}' " +
                            f"when fetching file '{filename}': {html_contents}"
                        )

            except (ClientError, AsyncioTimeoutError) as client_error:
                log_exception(client_error)


if __name__ == "__main__":
    asyncio_run(start_fetch())
