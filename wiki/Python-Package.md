# Python Package

`shellharbor-watchdog` adds a pip-installable Python launcher for the existing
Linux Bash monitor. The import/module name is `shellharbor_watchdog`; do not
confuse it with PyPI's unrelated `watchdog` filesystem-event library.

## Requirements and boundaries

- Python 3.11+ on Linux, including WSL. Native Windows/macOS execution is rejected
  with a clear message and exit code `2`.
- Bash 4.3+, Mike Farah yq v4, curl, flock, and GNU coreutils on `PATH`.
- Existing optional tools remain required only for enabled features.

The Python package has no Python runtime dependencies. It does not download
scripts at startup, auto-install OS tools, rewrite checks, change state formats,
create a daemon, or register cron/systemd jobs. Native and container deployments
still work without Python.

## Install from PyPI

The published package is available from the ordinary production index:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install shellharbor-watchdog==1.7.9
.venv/bin/python -m shellharbor_watchdog --version
```

No TestPyPI or additional index is needed. Install the Linux dependencies listed
above separately; the package does not install OS tools.

## Install from a checkout

From the repository root on Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/python -m shellharbor_watchdog --version
.venv/bin/shellharbor-watchdog validate -c examples/python-package.yaml
.venv/bin/shellharbor-watchdog --dry-run -c examples/python-package.yaml
```

The example checks only `true`; validation and the dry run do not write service
state. For production, replace the example with a reviewed configuration using
absolute paths owned by the monitoring service account.

For an already built local wheel, no index or Python dependency downloads are
needed at installation time:

```bash
.venv/bin/python -m pip install --no-index --no-deps \
  dist/shellharbor_watchdog-*-py3-none-any.whl
```

The wheel's version always comes from the repository's `VERSION`; use the
matching filename when building another release. Ordinary `pip install .`
requires access to the build backend unless it is already available; use the
hash-locked build instructions below for CI/offline artifact installation.

## Commands and config lookup

```bash
shellharbor-watchdog validate -c /etc/watchdog/config.yaml
shellharbor-watchdog -c /etc/watchdog/config.yaml
shellharbor-watchdog status -c /etc/watchdog/config.yaml --json
python -m shellharbor_watchdog --dry-run -c /etc/watchdog/config.yaml
shellharbor-watchdog-discover --help
python -m shellharbor_watchdog.discover --help
```

Both launchers pass arguments as an argv array without shell interpolation.
An `execve` replaces Python with Bash: there is no extra supervisor, output
capture, signal translation, or exit-code remapping. Streams and the existing
`0` / `1` / `2` semantics belong to the Bash engine.

`-c` takes precedence over `WATCHDOG_CONFIG`. If the environment variable is
unset or empty, the Python launchers use `config.yaml` in the current directory.
They do not change directory or write to site-packages. Existing configuration,
secret `*_env` fields, dry-run, maintenance, templates, and notification behavior
remain the Bash engine's responsibility.

For a scheduler, use an absolute executable path such as
`/opt/watchdog-venv/bin/shellharbor-watchdog` and an explicit `-c` path. Keep the
virtual environment, config, and parent directories protected from untrusted
writes; do not rely on a scheduler's current directory or activate a user shell.

## Build and test

The backend is Hatchling. The build configuration force-includes the original
generated script, discovery script, `VERSION`, example config, and schema into
private package resources; no second tracked copy of the Bash engine exists.
The source archive has an explicit allowlist so local credentials, AI-KIT files,
Git metadata, caches, and unrelated artifacts are not shipped.

On Linux x86_64 with Python 3.12 and the ordinary Watchdog dependencies:

```bash
python3 -m venv .venv-package
.venv-package/bin/python -m pip install --require-hashes --only-binary=:all: \
  -r .github/requirements-packaging.txt
bash scripts/build-watchdog.sh --check
.venv-package/bin/python tests/python_launcher.py
.venv-package/bin/python -m build --no-isolation
.venv-package/bin/python -m twine check --strict dist/*
.venv-package/bin/python tests/python_package.py
```

The Python package workflow tests the launcher on Python 3.11/3.12 and validates
wheel/sdist builds, a byte-identical rebuild without the checkout, installation
into a fresh venv, runtime exit codes, signals, literal argv, config precedence,
and bundled metadata. It uploads artifacts for inspection but never to PyPI.

## Manual TestPyPI / PyPI publication

Publication is separate from building, GitHub releases, and container publishing.
The `Publish Python package` workflow has only a manual trigger and defaults to
TestPyPI. Adding files, building locally, or creating a GitHub release does not
upload distributions to either index.

1. Register your PyPI/TestPyPI accounts. The repository's GitHub environments
   `testpypi` and `pypi` allow deployments only from the `main` branch. Production
   `pypi` additionally requires approval by `shellharbor`; the owner can approve
   their own manually dispatched run. Confirm these settings before publishing.
2. Configure a pending Trusted Publisher for a new project (or a Trusted Publisher
   on an existing project) separately on each index:
   - Project: `shellharbor-watchdog`.
   - Owner: `shellharbor`.
   - Repository: `watchdog`.
   - Workflow filename: `pypi-publish.yml`.
   - Environment: `testpypi` or `pypi`, matching the index.
3. Commit the packaging files, prepare a new release with matching `VERSION`,
   documentation, chart, and changelog. Merge the preparation PR only after its
   required Bash/Python/CodeQL checks pass and an authorized reviewer approves
   it; keep the approval gate enabled. Then push its new `vX.Y.Z` tag. Do not
   move a previously published tag to add packaging support.
4. In GitHub Actions, manually run **Publish Python package** from `main`, enter
   the existing release tag in the `tag` input, and choose `testpypi`. Do not
   select the tag as the workflow's execution branch: the environment admits
   `main` only, while the build checks out and verifies the supplied tag.
   Inspect the resulting artifact and project.
5. After verification, manually run again for `pypi` and approve its environment.

The read-only build job checks the tag/version, builds and tests distributions,
and uploads only wheel/sdist artifacts. The separate publishing job downloads
those artifacts without checking out or executing the project, and alone gets
`id-token: write`. PyPI Trusted Publishing uses OIDC without a stored API token;
the publishing action also requests package attestations. Existing releases are
not skipped or overwritten. Initial name availability is not a reservation, and
actual OIDC publication is verified only by a real authorized run.

See the official [Trusted Publishing guide](https://docs.pypi.org/trusted-publishers/)
and [pending publisher instructions](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/).

## Verified PyPI publication

Version [1.7.9](https://pypi.org/project/shellharbor-watchdog/1.7.9/) was
published on 2026-10-23 by
[GitHub Actions run 39975552350](https://github.com/shellharbor/watchdog/actions/runs/39975552350),
using the existing immutable `v1.7.9` tag. The owner explicitly confirmed the
production Trusted Publisher and approved the `pypi` deployment in GitHub.
The publisher is now active for `shellharbor/watchdog`, `pypi-publish.yml`, and
environment `pypi`; no API-token secret was created.

The build passed release preflight, launcher/installed-package tests, and strict
Twine validation. Published wheel/sdist SHA-256 values match both this run's
artifacts and the TestPyPI trial. PyPI's Integrity API reports the expected
GitHub repository/workflow/environment in one publish attestation per file.
This metadata check over HTTPS is not an independent local cryptographic
verification of the attestations.

A fresh non-root Linux/Python 3.11 container with a read-only root filesystem
installed `shellharbor-watchdog==1.7.9` only from `https://pypi.org/simple/`,
without an extra index or Python runtime dependencies. Console/module versions,
both discovery entrypoints, validation, dry-run state behavior, a healthy cycle,
and saved-state JSON status passed. Validation created no runtime paths;
dry-run retained the native operational log/lock but no service state.

Do not rerun the completed upload, overwrite its filenames, or move its tag.
Future package versions require a new reviewed release tag and a new manually
approved publication. GitHub releases, Docker images, and release-archive
signatures remain separate workflows.

[GitHub release v1.7.9](https://github.com/shellharbor/watchdog/releases/tag/v1.7.9)
was subsequently published on 2026-11-04 from the unchanged source tag. This
triggered the existing archive-signing and container workflows, not another
PyPI upload.

## Verified TestPyPI trial

Version [1.7.9](https://test.pypi.org/project/shellharbor-watchdog/1.7.9/) was
published on 2026-10-23 by the manual
[GitHub Actions run](https://github.com/shellharbor/watchdog/actions/runs/39956141897).
Both wheel and source archive match the tested CI artifacts by SHA-256, and
TestPyPI exposes publish attestations identifying the expected repository,
workflow, and `testpypi` environment. This is not a production PyPI publication.

Try it on Linux/WSL with the ordinary Watchdog dependencies already installed:

```bash
python3 -m venv .venv-testpypi
.venv-testpypi/bin/python -m pip --isolated install \
  --index-url https://test.pypi.org/simple/ --no-deps --only-binary=:all: \
  shellharbor-watchdog==1.7.9
.venv-testpypi/bin/shellharbor-watchdog --version
.venv-testpypi/bin/python -m shellharbor_watchdog --version
.venv-testpypi/bin/shellharbor-watchdog-discover --help
```

No additional index is needed because this package has no Python runtime
dependencies. A non-root, read-only-root Linux container verified installation,
validation, a dry run without service state, a healthy cycle, and saved-state
status. As in the native engine, the dry run retains its operational log/lock;
`validate` creates no runtime files. TestPyPI data may be pruned: use the
[test-index guide](https://packaging.python.org/en/latest/guides/using-testpypi/)
for experimentation, not production deployment.
