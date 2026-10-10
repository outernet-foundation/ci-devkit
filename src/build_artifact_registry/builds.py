from __future__ import annotations

import shlex
from pathlib import Path
from subprocess import CalledProcessError

from bashrun.bash import bash, bash_check, bash_output

from build_artifact_registry.registry_auth import ensure_registry_login


BUILD_MEDIA_TYPE = "application/vnd.build-artifact-registry.build.v1+raw"


def build_reference(registry: str, project: str, platform: str, tag: str) -> str:
    return f"{build_repository(registry, project, platform)}:{tag}"


def build_repository(registry: str, project: str, platform: str) -> str:
    return f"{registry}/{project}-{platform}".lower()


def push_build(
    registry: str,
    project: str,
    platform: str,
    tag: str,
    source_directory: Path,
    paths: list[str],
    *,
    registry_username: str | None = None,
    registry_token: str | None = None,
) -> None:
    ensure_registry_login(registry, username=registry_username, token=registry_token)
    reference = build_reference(registry, project, platform, tag)
    layers = " ".join(f"{shlex.quote(path)}:{BUILD_MEDIA_TYPE}" for path in paths)
    bash(f"oras push {shlex.quote(reference)} {layers}", cwd=source_directory)
    print(f"Pushed build: {reference}")


def pull_artifact(
    registry: str,
    project: str,
    platform: str,
    tag: str,
    target_directory: Path,
    *,
    required: bool = True,
    registry_username: str | None = None,
    registry_token: str | None = None,
) -> bool:
    ensure_registry_login(registry, username=registry_username, token=registry_token)
    reference = build_reference(registry, project, platform, tag)
    if not required and not bash_check(f"oras manifest fetch {shlex.quote(reference)}"):
        return False
    target_directory.mkdir(parents=True, exist_ok=True)
    bash(f"oras pull {shlex.quote(reference)} -o {shlex.quote(str(target_directory))}")
    print(f"Pulled build: {reference}")
    return True


def list_build_tags(
    registry: str,
    project: str,
    platform: str,
    *,
    registry_username: str | None = None,
    registry_token: str | None = None,
) -> list[str]:
    ensure_registry_login(registry, username=registry_username, token=registry_token)
    repository = build_repository(registry, project, platform)
    try:
        output = bash_output(f"oras repo tags {shlex.quote(repository)}")
    except CalledProcessError:
        print(f"No tags found for {repository}")
        return []
    return [line.strip() for line in output.splitlines() if line.strip()]
