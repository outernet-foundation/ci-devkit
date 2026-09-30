from __future__ import annotations

import os
import platform
import shlex
import shutil
from pathlib import Path

from bashrun.bash import bash, bash_check

from .registry_auth import ensure_registry_login


def install_oras(version: str = "1.2.2") -> None:
    if not shutil.which("oras"):
        _download_oras(version)

    if not shutil.which("oras"):
        print("Error: the oras CLI is not on PATH and could not be provisioned. Install it manually:")
        print("  macOS:  brew install oras")
        print("  Linux:  https://oras.land/docs/install")
        print("  Windows: scoop install oras")
        raise SystemExit(1)

    _ensure_zstd()
    ensure_registry_login("ghcr.io")


def _download_oras(version: str) -> None:
    if not shutil.which("curl"):
        return

    system = platform.system()
    if system == "Linux":
        archive = f"oras_{version}_linux_amd64.tar.gz"
        binary_directory = Path.home() / ".local" / "bin"
    elif system == "Windows":
        archive = f"oras_{version}_windows_amd64.zip"
        binary_directory = Path.home() / ".cache" / "ci-devkit" / "oras"
    else:
        return

    binary_directory.mkdir(parents=True, exist_ok=True)
    download_url = f"https://github.com/oras-project/oras/releases/download/v{version}/{archive}"
    bash(f"curl -fsSLO {download_url}", cwd=binary_directory)

    if system == "Linux":
        bash(f"tar -xzf {shlex.quote(str(binary_directory / archive))} -C {binary_directory} oras")
    else:
        shutil.unpack_archive(str(binary_directory / archive), binary_directory)

    (binary_directory / archive).unlink()
    os.environ["PATH"] = f"{binary_directory}{os.pathsep}{os.environ['PATH']}"


def _ensure_zstd() -> None:
    if platform.system() != "Linux" or shutil.which("zstd"):
        return

    prefix = "sudo " if os.geteuid() != 0 and shutil.which("sudo") else ""
    if bash_check(f"{prefix}apt-get update -qq") and bash_check(f"{prefix}apt-get install -y -qq zstd"):
        return

    print(
        "Warning: zstd not installable; OCI cache operations that pack or unpack tar.zst artifacts require it on PATH"
    )
