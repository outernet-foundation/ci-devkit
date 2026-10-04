# ci-devkit

## What this is

The CI runner floor — the `-devkit` family's bottom layer: the GitHub Actions runner environment helpers every domain devkit's job-step CLIs need, with no domain of its own. Its charter is the runner environment itself: step presentation (`ci_step`), runner/toolchain provisioning (`setup`), and OCI artifact I/O (`setup_oras`, `registry_auth`, `cache`, `builds`). The runner-environment and ORAS modules were absorbed from unity-devkit once they grew non-Unity consumers (org rule: one home per first-party concern); the version-tag primitives live in release-devkit's `tags.py` (version-tags semantics belong to the publisher — release-domain logic importing its own primitives from a floor package was an inverted seam). The dependency layering: `bashrun` → `ci-devkit` → domain devkits.

The package is `ci_devkit` (src-layout under `src/ci_devkit/`); all dependencies resolve from PyPI (`bashrun`, `pydantic`, `pydantic-settings`; git-source pins only in scratch branches testing unreleased changes). Runtime dependency it must never take: any domain devkit — the floor cannot sit above what it floors.

## Release flow

release-devkit's `AGENTS.md` owns the three-workflow contract; this repo follows it unchanged. Repo-specific facts: release-devkit is never a project dependency (ci-devkit sits below release-devkit; a project-level edge would be a cycle), and while pre-1.0, breaking changes ride the current `0.1` patch line (a `major_minor` bump is reserved for the eventual 1.0.0 stabilization).

This repo cannot take python-devkit as a dependency (python-devkit runtime-depends on ci-devkit; uv's resolver rejects the name-shadowing as a self-dependency), so its own preflight consumes python-devkit through the `tools/devkit/` sidecar: a `package = false` project named `ci-devkit-devkit` that exact-pins `python-devkit` — the different root name lets the dependency resolve to PyPI inside the sidecar's isolated env with no shadowing. `--project` uses the sidecar env but leaves cwd at the repo root, so preflight's child `uv run` calls (sync, ruff, basedpyright, …) re-discover ci-devkit's real project and run in ci-devkit's `.venv`. The committed `tools/devkit/uv.lock` is the single version surface, checked with `uv lock --check --project tools/devkit`.

## Shape

| Module | Role |
|---|---|
| `ci_step.py` | `ci_step(label)` context manager — wraps a step in `::group::`/`::endgroup::`, times it, and appends a duration row to `$GITHUB_STEP_SUMMARY` (failure-marked on exception). |
| `setup.py` | CI runner provisioning: `configure_git` (re-sets checkout's `safe.directory` in the real HOME), `free_disk_space` (strips preinstalled toolchains; container/bare-linux/Windows paths), `install_dotnet` (via the vendored `third-party/dotnet-install.sh`, PATH + `$GITHUB_PATH` wiring), `install_node` (nodejs.org tarball, npm registry override). |
| `setup_oras.py` | `install_oras` — best-effort ORAS CLI provisioning (downloads to `~/.local/bin` / `~/.cache/ci-devkit/oras` when absent; clear failure when un-installable), then logs into ghcr.io through the neutral credential chain. |
| `builds.py` | OCI build artifacts over ORAS, separate from the cache: `build_reference(registry, project, platform, tag)` composes the shared shelf address `{registry}/{project}-{platform}:{tag}` (lowercased end-to-end); `push_build` pushes files as layers stamped `application/vnd.ci-devkit.build.v1+raw`; `pull_build` is immutable/must-exist (no fallback tags); `list_build_tags` / `build_exists` query. |
| `registry_auth.py` | `ensure_registry_login(registry, *, username, token)` — the credential chain: explicit parameter → `CI_REGISTRY_USERNAME`/`CI_REGISTRY_TOKEN` environment → ambient docker config (credential helper / store / auth entry). Prints which source resolved; no `GITHUB_`-shaped input anywhere. |
| `cache.py` | OCI artifact cache over ORAS: `restore(registry, name, tag, target, *, required, fallback_tags)` pulls a tar+zstd artifact by tag with fallbacks; `save(registry, name, tag, source, paths)` packs glob-resolved paths and pushes. Registry names are lowercased (OCI rule vs GitHub case). Best-effort semantics — the deliberate contrast with `builds`. |
| `third-party/` | Vendored `dotnet-install.sh` (curl-downloading it inside CI containers is unreliable — the same reason `actions/setup-dotnet` bundles it); resolved `__file__`-relative, so it works in editable installs, wheels, and git checkouts alike. |

## Constraints

- **The module surface is cross-repo Python API.** The import paths and signatures above are contract, not internals — release-devkit (ci_step, setup), unity-devkit (ci_step, setup, setup_oras, cache, builds), and consumer repos' CI commands import them directly.
- **No domain code, ever.** Unity build logic → unity-devkit; compose stacks → docker-devkit; publication → release-devkit; python repo lifecycle → python-devkit. When a module grows a domain, it moves out.
- **ORAS lives only here.** Domain devkits contain no `oras` CLI knowledge; the builds module is the single door for build-artifact I/O, and the reference convention (`build_reference`) lives here so upload and consumption sides cannot drift apart.
- **No runner knowledge.** Nothing in this package names a `GITHUB_*` variable or assumes per-run-ephemeral credentials; registries, references, and credentials are the floor's vocabulary, and workflow YAML maps runner secrets onto the neutral `CI_REGISTRY_*` environment. If a second CI platform ever arrives, the auth seam upgrades to a per-platform CredentialProvider — one implementor today is ceremony, not architecture.
- **Builds ≠ caches.** `cache.py` keeps fallback-tag, best-effort semantics; `builds.py` is immutable and must-exist with its own media type. The media type identifies the writer in both (`…cache.v1+zstd`, `…build.v1+raw`); restore/pull don't filter on it, so older manifests still pull.
- **The ORAS cache media type identifies the wrapper package, not the consuming repo.** `cache.save()` pushes with `application/vnd.ci-devkit.cache.v1+zstd`. Restore doesn't filter on media type, so older `vnd.unity-devkit.*` manifests still pull — the identifier tracks the tool that wrote the cache, not the project whose bytes are inside it.
- **CI tooling prints to stdout by design** — step output is the operator interface; the `print` ignore rides the org-wide PLE-336 deferral like the sibling devkits and will never convert to structured logging here.

## See also

- [`bashrun`](https://github.com/outernet-foundation/bashrun) — the shell-exec helpers everything here shells out through.
