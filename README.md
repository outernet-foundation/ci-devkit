# ci-devkit

The CI runner floor for outernet-foundation repos: the GitHub Actions step wrapper, runner and toolchain provisioning (git config, disk space, .NET, Node, ORAS), and the OCI artifact cache. Every domain devkit (`python-devkit`, `unity-devkit`, `docker-devkit`, `release-devkit`, and future arrivals like `node-devkit`) builds on this package; it owns nothing domain-specific.

## Setup

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

## Consuming from another repo

```toml
[project]
dependencies = ["ci-devkit>=0.1.0"]
```

```python
from ci_devkit.cache import restore, save
from ci_devkit.ci_step import ci_step
from ci_devkit.setup import configure_git, free_disk_space, install_dotnet, install_node
from ci_devkit.setup_oras import install_oras
```

To test an unreleased change, pin the repo at a git ref in a scratch branch instead (`ci-devkit = { git = "…", rev = "<sha>" }` under `[tool.uv.sources]`) and drop the pin when the release lands.

## Development

```bash
uv run ruff check .
uv run ruff format --check .
uv run basedpyright
```
