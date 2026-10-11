# build-artifact-registry

## What this is

Registry primitives for pushing and pulling build artifacts, locally or remotely: ORAS-backed
artifact I/O (`builds`, `cache`), ORAS CLI provisioning (`setup_oras`), and the registry
credential chain (`registry_auth`). Purely registry concerns — no presentation, no runner
knowledge: nothing here names a `GITHUB_*` variable or assumes a CI environment, and ghcr is a
registry choice passed as a parameter, not platform coupling. The dependency layering:
`bashrun` → build-artifact-registry → the binding and domain devkits.

The package is `build_artifact_registry` (src-layout under
`src/build_artifact_registry/`); all dependencies resolve from PyPI (`bashrun`,
`pydantic`, `pydantic-settings`; git-source pins only in scratch branches testing unreleased
changes). Runtime dependency it must never take: any domain devkit or the binding — this
package floors them all. The predecessor `ci-devkit` distribution is frozen on PyPI forever,
never yanked; consumers holding old pins keep resolving it and migrate by relocking onto this
line.

## Release flow

release-devkit's `AGENTS.md` owns the three-workflow contract; this repo follows it unchanged.
Repo-specific facts: release-devkit (renaming to github-actions-devkit) runtime-depends on this
package, so it is never a project dependency here — a project-level edge would be a cycle; and
API-breaking changes ship with a manually bumped `major_minor` (patch-auto assumes additive
changes).

This repo cannot take python-devkit as a dependency (python-devkit's current line
runtime-depends on this family; uv's resolver rejects the name-shadowing as a
self-dependency), so its own preflight consumes python-devkit through the `tools/devkit/`
sidecar: a `package = false` project named `build-artifact-registry-devkit` that
exact-pins `python-devkit` — the suffixed root name stays distinct from every distribution in
python-devkit's closure, letting the dependency resolve to PyPI inside the sidecar's isolated
env with no shadowing. `--project` uses the sidecar env but leaves cwd at the repo root, so
preflight's child `uv run` calls (sync, ruff, basedpyright, …) re-discover this repo's real
project and run in its `.venv`. The committed `tools/devkit/uv.lock` is the single version
surface, checked with `uv lock --check --project tools/devkit`.

## Shape

| Module | Role |
|---|---|
| `builds.py` | OCI build artifacts over ORAS, separate from the cache: `build_reference(registry, project, platform, tag)` composes the shared shelf address `{registry}/{project}-{platform}:{tag}` (lowercased end-to-end); `push_build` pushes files as layers stamped `application/vnd.build-artifact-registry.build.v1+raw`; `pull_artifact` pulls immutable artifacts (no fallback tags), returns `True`, and raises when absent unless `required=False` makes absence a `False` return — the one-call form for consumers whose artifact is legitimately missing; `list_build_tags` queries. |
| `registry_auth.py` | `ensure_registry_login(registry, *, username, token)` — the credential chain: explicit parameter → `REGISTRY_USERNAME`/`REGISTRY_TOKEN` environment → ambient docker config (credential helper / store / auth entry). Prints which source resolved; no `GITHUB_`-shaped input anywhere. |
| `cache.py` | OCI artifact cache over ORAS: `restore(registry, name, tag, target, *, required, fallback_tags)` pulls a tar+zstd artifact by tag with fallbacks; `save(registry, name, tag, source, paths)` packs glob-resolved paths and pushes. Both authenticate through the neutral chain on entry — the same door `builds` uses — so no caller can reach an ORAS call unauthenticated. A registry refusal (denied/unauthorized/forbidden in the pull output) is a loud fatal, never a miss; only absent or transient failures fall through the fallback chain. Registry names are lowercased (OCI rule vs GitHub case). Best-effort miss semantics — the deliberate contrast with `builds`. |
| `setup_oras.py` | `install_oras(version, *, registry)` — best-effort ORAS CLI provisioning (downloads to `~/.local/bin` / `~/.cache/build-artifact-registry/oras` when absent; clear failure when un-installable) plus zstd provisioning; when `registry` is passed it logs in through the neutral credential chain, otherwise provisioning is registry-free. |

## Constraints

- **The module surface is cross-repo Python API.** The import paths and signatures above are
  contract, not internals — the binding devkit and domain devkits import them directly, with
  script names and flags equally public per the stable-CLI-API doctrine.
- **ORAS lives only here.** Domain devkits contain no `oras` CLI knowledge; the builds module
  is the single door for build-artifact I/O, and the reference convention (`build_reference`)
  lives here so upload and consumption sides cannot drift apart.
- **No runner knowledge.** Registries, references, and credentials are the vocabulary;
  workflow YAML maps runner secrets onto the neutral `REGISTRY_*` environment. If a second
  CI platform ever arrives, the auth seam upgrades to a per-platform CredentialProvider — one
  implementor today is ceremony, not architecture.
- **Builds ≠ caches.** `cache.py` keeps fallback-tag, best-effort semantics; `builds.py` is
  immutable and must-exist with its own media type. The media type identifies the writer in
  both (`…cache.v1+zstd`, `…build.v1+raw`); restore/pull don't filter on it, so older
  manifests written as `vnd.unity-devkit.*` or `vnd.ci-devkit.*` still pull — the identifier
  tracks the tool that wrote the artifact, not the project whose bytes are inside it.
- **CI tooling prints to stdout by design** — step output is the operator interface; the
  `print` ignore rides the org-wide PLE-336 deferral like the sibling devkits and will never
  convert to structured logging here.

## See also

- [`bashrun`](https://github.com/outernet-foundation/bashrun) — the shell-exec helpers everything here shells out through.
