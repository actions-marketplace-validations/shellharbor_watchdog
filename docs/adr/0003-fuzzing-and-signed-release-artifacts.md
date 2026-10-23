# ADR 0003: Fuzz Bash boundaries and sign immutable release artifacts

## Status

Accepted — 2026-10-14.

## Context

Watchdog is primarily Bash. Native Go/Python fuzzing detectors in Scorecard
filter out languages below their prominence threshold. Adding an unexecuted
fuzz function would neither exercise Watchdog nor reliably establish fuzzing.
Existing GitHub releases contain no uploaded files, so signature checks have
no artifact to assess. Container provenance is a separate delivery contract.

## Decision

Use an actual ClusterFuzzLite integration with an immutable official Python SDK
and its Atheris/libFuzzer engine. Bundle Watchdog, its source serializer helpers,
and required Linux binaries into the compiled target. Fuzz CLI validation and
JSON/HTML/Prometheus serialization properties with bounded inputs, deadlines,
temporary files, and guards against check/notification/hook execution.

Create a deterministic tar.gz from the resolved Git tag commit, never from the
working tree. Publish it with SHA256SUMS and a Cosign Sigstore bundle for each.
Sign through the GitHub release workflow's OIDC identity, verify the exact
workflow/tag identity and issuer, then upload. Existing identical artifacts or
valid bundles are retained; different bytes or invalid bundles stop the upload.

## Alternatives and consequences

- A pure property-test loop is useful but is not coverage-guided fuzzing.
  A native-language harness alone may remain undetected in this Bash project.
- ClusterFuzzLite builds require a substantial SDK image. Its compiler runs as
  root in a CI-only builder, an explicit exception to runtime-container rules.
  It is not a deployment image. Fuzzer execution can run non-root with network
  disabled and read-only root; PyInstaller needs executable temporary storage.
- Instrumentation covers the Python harness and its oracles. Bash itself is a
  subprocess and is not claimed to have ASan or line-coverage instrumentation.
- Keyless release signing avoids long-lived private-key secrets. GitHub OIDC
  and Sigstore are external requirements for publication; local tests use
  disposable keys without public transparency-log writes.
- Existing release tags are not moved and old artifacts are not replaced. The
  first signed release must contain these scripts and workflows in its tag.
- Scorecard detects integration/assets heuristically; its published score is
  not evidence that every path is safe. It must be checked after publication.
