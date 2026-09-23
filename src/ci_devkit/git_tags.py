from __future__ import annotations

from pathlib import Path

from bashrun.bash import bash, bash_check, bash_output


def get_latest_tag_version(prefix: str) -> str | None:
    versions = list_tag_versions(prefix)
    return versions[0] if versions else None


def list_tag_versions(prefix: str) -> list[str]:
    output = bash_output(f'git tag --list "{prefix}*" --sort=-v:refname').strip()
    if not output:
        return []
    return [tag[len(prefix) :] for tag in output.splitlines()]


def has_changes_since_tag(tag: str | None, path: Path) -> bool:
    if tag is None:
        return True
    return not bash_check(f"git diff --quiet {tag} HEAD -- {path}")


def create_and_push_tag(tag: str) -> None:
    bash(f"git tag {tag}")
    bash(f"git push origin {tag}")
