# ci-devkit

## What this is

The CI runner floor — the `-devkit` family's bottom layer: the GitHub-Actions environment helpers every domain devkit's job-step CLIs need, with no domain of its own. It absorbed `ci_step`, the runner/toolchain provisioning, the git-tag helpers, and the OCI artifact cache from unity-devkit (2026-09-21) because those had grown non-Unity consumers — the org rule being one home per first-party concern, and this concern (the runner environment) is none of python/unity/docker/registry. The dependency layering: `bashrun` → `ci-devkit` → domain devkits. Anticipated consumers include a future `node-devkit` (toolchain provisioning is ecosystem-generic by design).

The package is `ci_devkit` (src-layout under `src/ci_devkit/`); all dependencies resolve from PyPI (`bashrun`, `pydantic`, `pydantic-settings`; git-source pins only in scratch branches testing unreleased changes). Runtime dependency it must never take: any domain devkit — the floor cannot sit above what it floors.

## Release flow

Publishing rides `release.yml`, triggered by a successful CI run on a `main` push: the machinery — release-devkit's publish composite action (pinned by SHA; the uvx invocation runs inside the caller's job, keeping OIDC identity local), never a project dependency (ci-devkit sits below release-devkit; a project-level edge would be a cycle) — computes the plan from the tag ledger and path-diff, patches the version ephemerally, and publishes to PyPI under OIDC trusted publishing (publisher bound to `release.yml`, no environment). The committed `pyproject.toml` version is permanently the `0.0.0.dev0` sentinel; the `ci-devkit-v*` tags are the version ledger (first release `0.1.0`, patch-auto thereafter). API-breaking changes ship with a manually bumped version — patch-auto assumes additive changes.

## Shape

| Module | Role |
|---|---|
| `ci_step.py` | `ci_step(label)` context manager — wraps a step in `::group::`/`::endgroup::`, times it, and appends a duration row to `$GITHUB_STEP_SUMMARY` (failure-marked on exception). |
| `setup.py` | CI runner provisioning: `configure_git` (re-sets checkout's `safe.directory` in the real HOME), `free_disk_space` (strips preinstalled toolchains; container/bare-linux/Windows paths), `install_dotnet` (via the vendored `third-party/dotnet-install.sh`, PATH + `$GITHUB_PATH` wiring), `install_node` (nodejs.org tarball, npm registry override). |
| `setup_oras.py` | `install_oras` — installs the ORAS CLI (zstd dependency included) and logs into ghcr.io with the job token. |
| `git_tags.py` | Git-tag ledger primitives: `list_tag_versions(prefix)` (version-sorted, newest first), `get_latest_tag_version`, `has_changes_since_tag` (path-diff change detection), `create_and_push_tag`. Callers with filtering semantics layer on top (release-devkit's stable-version filter). |
| `cache.py` | OCI artifact cache over ORAS: `restore(registry, name, tag, target, *, required, fallback_tags)` pulls a tar+zstd artifact by tag with fallbacks; `save(registry, name, tag, source, paths)` packs glob-resolved paths and pushes. Registry names are lowercased (OCI rule vs GitHub case). |
| `third-party/` | Vendored `dotnet-install.sh` (curl-downloading it inside CI containers is unreliable — the same reason `actions/setup-dotnet` bundles it); resolved `__file__`-relative, so it works in editable installs, wheels, and git checkouts alike. |

## Constraints

- **The module surface is cross-repo Python API.** The import paths and signatures above are contract, not internals — release-devkit (ci_step, setup, git_tags), unity-devkit (ci_step, setup, setup_oras, cache, git_tags), and consumer repos' CI commands import them directly.
- **No domain code, ever.** Unity build logic → unity-devkit; compose stacks → docker-devkit; publication → release-devkit; python repo lifecycle → python-devkit. When a module grows a domain, it moves out.
- **The ORAS cache media type identifies the writer, not the consumer.** `cache.save()` pushes with `application/vnd.ci-devkit.cache.v1+zstd`. Restore doesn't filter on media type, so older `vnd.unity-devkit.*` manifests still pull — the identifier tracks the tool that wrote the cache, not the project whose bytes are inside it.
- **CI tooling prints to stdout by design** — step output is the operator interface; the `print` ignore rides the org-wide PLE-336 deferral like the sibling devkits and will never convert to structured logging here.

## See also

- `README.md` — human-facing setup and consumer install snippet.
- [`bashrun`](https://github.com/outernet-foundation/bashrun) — the shell-exec helpers everything here shells out through.
