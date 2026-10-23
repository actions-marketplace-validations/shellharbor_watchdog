# ADR 0004: Ship a Python launcher without replacing the Bash runtime

- Date: 2026-10-23
- Status: accepted

## Context

The user requested Python-based startup and a PyPI package. Watchdog already
has a generated, self-contained Bash runtime with established config, state,
notification, signal, and exit-code behavior. PyPI's name `watchdog` belongs to
an unrelated filesystem-event library. Python is currently optional for native
and container deployments.

## Options

- Rewrite the monitoring engine in Python: a large behavioral migration not
  requested by the user, with unnecessary state and notification risks.
- Download or locate an external Bash script at runtime: introduces an
  uncontrolled runtime code dependency and makes installed packages incomplete.
- Bundle the existing runtime and replace the Python launcher process with Bash.

## Decision

Use distribution `shellharbor-watchdog`, module `shellharbor_watchdog`, Python
3.11+, and a `src/` layout. Console scripts and `python -m` pass literal argv to
the packaged Bash files with `os.execve`. The launcher does not supervise a
child, remap exit codes, capture streams, or install OS dependencies. Linux,
Bash 4.3+, and the existing external tools remain required.

Use Hatchling force-inclusion to package the existing generated monitor,
discovery script, `VERSION`, config example, and schema, without maintaining a
second runtime copy. Read the package version from the root `VERSION`. Explicitly
allowlist sdist content and verify byte-identical wheel rebuilds from that sdist.

The Python interface defaults to the caller's `config.yaml`, not a writable file
inside site-packages. Explicit `-c` and `WATCHDOG_CONFIG` retain their precedence.
The Bash engine and native deployment defaults are unchanged.

Keep ordinary package CI read-only. Publishing is a separate manual workflow,
defaulting to TestPyPI. A read-only job builds/tests the selected release tag;
an artifact-only job uses environment-bound PyPI Trusted Publishing with OIDC.
No API-token secret or automatic push/release publication is introduced.

## Consequences

- pip installs contain the runtime; no checkout or runtime network download is
  needed. Native/container users do not gain a Python dependency.
- The Python launcher is a delivery surface, not a portable Windows/macOS
  rewrite or a public in-process monitoring API.
- CI build tooling has a separate Python 3.12/Linux hash lock. Backend and lock
  updates must stay synchronized; no Python runtime dependencies are introduced.
- PyPI/TestPyPI account registration, environment protection, and Trusted
  Publisher registration remain explicit operator work. A local build neither
  reserves the name nor proves actual OIDC publication.
- Removing the Python package does not remove operator config, state, timers,
  native installations, or containers.

## Verification

`tests/python_launcher.py` covers argv, config lookup, errors, and secret-safe
startup. `tests/python_package.py` tests metadata/resources, isolated installation,
sdist rebuilding, real monitoring exits, signals, and process identity.
`tests/supply_chain.py` guards publisher permissions and dependency locks.
See [Python Package](../../wiki/Python-Package.md) for runnable procedures.
