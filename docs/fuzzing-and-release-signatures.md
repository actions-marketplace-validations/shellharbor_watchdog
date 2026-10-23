# Fuzzing and release signatures

## Actual fuzzing targets

The `Fuzzing` workflow builds `.clusterfuzzlite/` with the official pinned SDK
and runs Atheris/libFuzzer for 180 seconds on pushes, PRs, a weekly schedule,
and manual dispatch. The seed corpus is committed; ClusterFuzzLite retains
failure artifacts for replay. Its input limit is 4096 bytes.

The target exercises real Bash functions and the real `validate` command:

- JSON must parse back to the original Bash-representable string, including
  control characters, quotes, slashes, newlines, and Unicode.
- HTML text/double-quoted attributes and Prometheus labels must escape their
  delimiter characters correctly.
- Validation must return 0 or 2, complete within five seconds, and create no
  runtime files or execute checks, hooks, or network notifications.
- Structured command fixtures must validate successfully without execution.

Instrumentation guides mutations through the Python harness/oracles. It does
not instrument Bash itself or establish complete Bash branch coverage.
Run the deterministic regressions with normal runtime dependencies available:

```bash
python3 tests/fuzzing.py
```

For a local SDK build and short fuzz run, use a dedicated temporary volume:

```bash
docker build -f .clusterfuzzlite/Dockerfile -t watchdog:fuzz-build .
docker volume create watchdog-fuzz-out
docker run --rm -v watchdog-fuzz-out:/out \
  -e FUZZING_LANGUAGE=python -e FUZZING_ENGINE=libfuzzer -e SANITIZER=address \
  watchdog:fuzz-build compile
docker run --rm -v watchdog-fuzz-out:/out watchdog:fuzz-build bash -c \
  'mkdir -p /out/corpus; cp /src/watchdog/.clusterfuzzlite/corpus/* /out/corpus; chmod +x /out/watchdog_fuzzer.pkg; chown -R 10001:10001 /out'
docker run --rm --network none --read-only --user 10001:10001 \
  --tmpfs /tmp:rw,exec,nosuid,nodev,size=256m -v watchdog-fuzz-out:/out \
  --entrypoint /out/watchdog_fuzzer \
  gcr.io/oss-fuzz-base/base-runner@sha256:29e4fcca00f6b844d732ee7427e86dae478db7f78d3ef7128ba1505ea4ab7126 \
  -max_total_time=60 -timeout=20 -rss_limit_mb=2048 /out/corpus
```

Replay a crash by passing its file instead of the corpus directory to that
same target. Retain the failing input and add a deterministic regression before
fixing code. Do not upload real credentials or production configurations as
corpus. The SDK builder is CI-only and is never published as Watchdog runtime.

## Signed release files

On a published release whose tag includes `release-signing.yml`, the workflow
validates metadata, packages only committed tag contents, then signs and
verifies these files with Cosign 3.1.3:

- `watchdog-X.Y.Z.tar.gz`
- `SHA256SUMS`
- `watchdog-X.Y.Z.tar.gz.sigstore.json`
- `SHA256SUMS.sigstore.json`

CI and release signing use the SHA-pinned official Cosign installer v4.1.2.
It verifies Cosign 3.x Sigstore bundles; older installer revisions that request
the removed detached `.sig` release asset are incompatible with this pin.

The bundles include signature/certificate/transparency information. The signing
job alone has `contents: write` and `id-token: write`. No private-key secret is
needed. The expected identity is the exact release workflow at `refs/tags/vX.Y.Z`,
and the issuer is `https://token.actions.githubusercontent.com`.

After downloading those four files, verify **before extracting or installing**:

```bash
version=X.Y.Z # Replace with an actually published signed release.
identity="https://github.com/shellharbor/watchdog/.github/workflows/release-signing.yml@refs/tags/v${version}"
cosign verify-blob --bundle SHA256SUMS.sigstore.json \
  --certificate-identity "$identity" \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com SHA256SUMS
cosign verify-blob --bundle "watchdog-${version}.tar.gz.sigstore.json" \
  --certificate-identity "$identity" \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  "watchdog-${version}.tar.gz"
sha256sum --check SHA256SUMS
```

Never bypass certificate identity, issuer, or transparency verification for a
published release. `tests/cosign_offline.py` intentionally uses disposable keys
and disables public log upload only for its local cryptographic regression;
it proves valid signatures pass and altered bytes/wrong keys fail.

A rerun verifies existing remote artifacts and uploads only missing files.
Different existing bytes or invalid signatures require maintainer investigation;
the workflow never uses `--clobber`. Old tags remain unchanged. Docker image
publication, SBOMs, and BuildKit provenance retain their separate workflow.

The first keyless signature and Scorecard's detection require a real GitHub
release run. Local crypto tests cannot create or prove a GitHub OIDC identity.
