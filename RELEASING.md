# Releasing ShellHarbor Watchdog

This project keeps release metadata deliberately simple and verifiable. The
root [`VERSION`](VERSION) file is the source for the CLI version; the README
and changelog are derived release documentation checked by CI.

## Release checklist

1. Confirm the working tree contains only intended changes.
2. Set `VERSION` to the next semantic version without the `v` prefix.
3. Add a dated `## [X.Y.Z]` section to [`CHANGELOG.md`](CHANGELOG.md).
4. Update the stable archive URL and extracted directory name in `README.md`.
5. Synchronize `charts/watchdog/Chart.yaml` `appVersion` and the Kubernetes
   example image tag with `VERSION`. Bump the chart's own `version` whenever
   its metadata or templates change. Update affected Wiki pages and examples.
6. Run the quality checks:

   ```bash
   bash ./scripts/build-watchdog.sh --check
   bash ./scripts/release-preflight.sh vX.Y.Z
   bash -n service-watchdog.sh watchdog-discover.sh install.sh scripts/build-watchdog.sh scripts/release-preflight.sh lib/watchdog/*.sh tests/*.sh
   shellcheck service-watchdog.sh watchdog-discover.sh install.sh scripts/build-watchdog.sh scripts/release-preflight.sh tests/*.sh
   bash ./tests/versioning.sh
   bash ./tests/run-all.sh
   # Check the chart's release image version and rendering safety:
   helm lint charts/watchdog --strict
   python3 ./tests/kubernetes_chart.py
   # When changing the Kubernetes runtime contract:
   python3 ./tests/kubernetes_integration.py
   ```

7. Commit the release metadata and create an annotated `vX.Y.Z` tag.
8. Push the commit and tag. The `Release metadata` workflow reruns the same
   preflight and verifies tag, `VERSION`, CLI output, README archive reference,
   changelog heading, and installer metadata.
9. Create the GitHub release from the verified tag and paste the matching
   changelog entry as its release notes.

10. Wait for `Signed release artifacts`. New release tags containing that
    workflow upload `watchdog-X.Y.Z.tar.gz`, `SHA256SUMS`, and a keyless Cosign
    `.sigstore.json` bundle for each. No signing private-key secret is required.
    The signer verifies exact workflow/tag identity and issuer before upload;
    a rerun retains valid existing files and repairs missing uploads only.
11. Download and verify the signed files using the
    [signature verification guide](docs/fuzzing-and-release-signatures.md).
    Confirm the separate Docker publication and Fuzzing checks also pass.

Test packaging and signing boundaries without publishing:

```bash
python3 tests/release_artifacts.py
# With Cosign 3.1.3 available; disposable keys only, no OIDC or public log upload:
python3 tests/cosign_offline.py
```

The first signed release must include the new scripts/workflow in its tag.
Existing tags are not retroactively moved or changed. Local tests cannot prove
GitHub OIDC signing; that part is confirmed by the first actual release run.

The `Kubernetes` workflow supplies pinned Helm, kind, kubectl, and PyYAML in an
isolated runner. It should be green for a Kubernetes-facing release; its kind
test uses a private kubeconfig and a temporary cluster only.

Do not move or retag an already published release. Publish a corrective patch
release instead.

## Optional Python distribution

The `shellharbor-watchdog` wheel/sdist version is read directly from `VERSION`;
no second version constant is maintained. The **Python package** workflow builds
and tests distributions but does not publish them. Run its checks before
choosing a tag for Python publication:

```bash
python3 tests/python_launcher.py
python3 -m pip install --require-hashes --only-binary=:all: -r .github/requirements-packaging.txt
python3 -m build --no-isolation
python3 -m twine check --strict dist/*
python3 tests/python_package.py
```

Use a clean Python 3.12 environment on Linux x86_64 for the packaging tool lock.
The install tests additionally need the ordinary Watchdog runtime dependencies.

PyPI/TestPyPI uploads require separate account/environment/Trusted Publisher
setup and a manual **Publish Python package** run. The workflow defaults to
TestPyPI, verifies the selected `vX.Y.Z` tag, and gives OIDC credentials only to
the artifact-only publish job. Dispatch the workflow from `main` and pass the
release tag as its `tag` input: both index environments allow only `main`.
Production `pypi` additionally requires approval by `shellharbor`.
It does not automatically upload on a GitHub
release. See [Python Package](wiki/Python-Package.md#manual-testpypi--pypi-publication)
for exact registration fields and first-publication steps. Do not reuse an
old tag that lacks these packaging files or overwrite an existing PyPI version.
