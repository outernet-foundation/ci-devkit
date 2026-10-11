from __future__ import annotations

import json
import shlex
from pathlib import Path

from bashrun.bash import bash
from pydantic import BaseModel, Field, ValidationError
from pydantic_settings import BaseSettings


class RegistryEnvironment(BaseSettings):
    registry_username: str = ""
    registry_token: str = ""


class _DockerConfig(BaseModel):
    cred_helpers: dict[str, str] = Field(default_factory=dict, alias="credHelpers")
    creds_store: str = Field(default="", alias="credsStore")
    auths: dict[str, object] = Field(default_factory=dict)


def ensure_registry_login(registry: str, *, username: str | None = None, token: str | None = None) -> None:
    if bool(username) != bool(token):
        message = "registry login needs both a username and a token; pass both or neither"
        raise ValueError(message)

    if username and token:
        _login(registry, username, token, "explicit parameter")
        return

    environment = RegistryEnvironment.model_validate({})
    if environment.registry_username and environment.registry_token:
        _login(
            registry,
            environment.registry_username,
            environment.registry_token,
            "REGISTRY_USERNAME / REGISTRY_TOKEN environment",
        )
        return

    host = _registry_host(registry)
    if environment.registry_username or environment.registry_token:
        print("Warning: only one of REGISTRY_USERNAME / REGISTRY_TOKEN is set; skipping environment credential login")

    ambient = _ambient_credential_source(host)
    if ambient is not None:
        print(f"Registry auth for {host}: {ambient}")
        return

    print(
        f"Registry auth for {host}: no credential resolved "
        "(tried explicit parameter, REGISTRY_USERNAME / REGISTRY_TOKEN environment, docker config); "
        "continuing with ambient or anonymous access"
    )


def _login(registry: str, username: str, token: str, source: str) -> None:
    host = _registry_host(registry)
    bash(f"oras login {shlex.quote(host)} --username {shlex.quote(username)} --password-stdin", stdin_text=token)
    print(f"Registry auth for {host}: logged in via {source}")


def _registry_host(registry: str) -> str:
    scheme, separator, remainder = registry.partition("://")
    without_scheme = remainder if separator else scheme
    return without_scheme.split("/", 1)[0]


def _ambient_credential_source(host: str) -> str | None:
    config_path = Path.home() / ".docker" / "config.json"
    if not config_path.is_file():
        return None

    try:
        config = _DockerConfig.model_validate(json.loads(config_path.read_text()))
    except (ValidationError, ValueError):
        return None

    helper = config.cred_helpers.get(host)
    if helper:
        return f"docker credential helper '{helper}' for {host}"

    if config.creds_store:
        return f"docker credential store '{config.creds_store}'"

    if any(_registry_host(auth_host) == host for auth_host in config.auths):
        return f"docker config auth entry for {host}"

    return None
