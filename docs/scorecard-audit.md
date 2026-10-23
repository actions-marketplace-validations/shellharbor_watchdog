# OpenSSF Scorecard audit

Reviewed on 2026-10-14 against the [public report](https://api.scorecard.dev/projects/github.com/shellharbor/watchdog)
dated 2026-10-10, for commit `0b30f41b7d4a8e747ef2902ef84c2a6a1c7c506f`.
Scorecard v5.5.0 reported an overall score of **6.2/10**. This is a historical
baseline, not a prediction of the score after these changes are published.

## Findings and disposition

| Check | Reported score | Verified result and action |
| --- | --- | --- |
| Pinned-Dependencies | 3 | Replaced mutable Action tags with verified full commit SHAs; pinned the Bash 4.3 image digest; locked every CI Python dependency by version and wheel SHA-256. CI verifies yq's pinned SHA-256 before installing it. Dockerfile base images were already digest-pinned. |
| Token-Permissions | 9 | Moved CodeQL's `security-events: write` to its analysis job. Removed unused `attestations: write` and `id-token: write` from Docker publication; GHCR retains only the required package write permission. Checkout no longer persists credentials. |
| Dependency-Update-Tool | 10 | Dependabot existed, but its Composer entry did not match this Bash project. It now monitors Actions, the CI Python lock, and both Dockerfiles. |
| Security-Policy | 10 | SECURITY.md exists, but its supported-version table incorrectly referred to 1.1.x. It now refers to the latest release recorded in VERSION. |
| Dangerous-Workflow | 10 | No dangerous patterns reported. Workflow inputs used by shell commands remain environment variables; no privileged pull-request checkout was introduced. |
| Binary-Artifacts | 10 | No binary artifacts reported. Generated Bash is reviewable source; local tool binaries must not be committed. |
| Vulnerabilities | 10 | No known vulnerabilities reported by this check. This is not proof that all code or container packages are vulnerability-free. |
| SAST | 10 | CodeQL is detected and remains enabled. |
| License | 10 | MIT license is detected. |
| Packaging | 10 | The container publication workflow is detected and remains enabled. |
| CI-Tests | 10 | Recent merged PRs had CI tests. Existing regressions remain enabled; an additional supply-chain regression check now protects the CI configuration. |
| Branch-Protection | 0 | Protection for main was not detected. This requires GitHub repository settings, not a YAML assertion. No remote settings were changed. |
| Code-Review | 0 | No approved changesets were detected. Only actual human review can address this finding; bot/AI review is not a replacement. |
| Maintained | 0 | The report explicitly says the repository is younger than 90 days. Do not generate empty commits to change this signal. |
| Contributors | 0 | The report did not detect contributions from multiple organizations. Additional accounts or invented company affiliations do not provide independent review. |
| CII-Best-Practices | 0 | No Best Practices enrollment was detected. Registration and evidence-backed answers require the maintainer's participation. No badge or enrollment was fabricated. |
| Fuzzing | 0 | Added actual ClusterFuzzLite/Atheris build/run integration with bounded validation and serialization targets. A compiled local run executed 364 mutations; public detection remains pending publication. |
| Signed-Releases | -1 | The baseline releases had no uploaded assets. Added deterministic tagged-source archives, SHA256SUMS, and keyless Cosign bundles with exact workflow/tag identity verification. Local crypto/tampering tests pass; GitHub OIDC signing and public detection require the first release containing this workflow. |

Scorecard also reported incomplete shell parsing for valid lifecycle arithmetic
in `lib/watchdog/50-lifecycle.sh` and the generated script. That is a limitation
of the scanner; runtime syntax must not be changed merely to conceal it.

## Repository verification

On CPython 3.12 / Linux x86_64, use an isolated environment:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: \
  -r .github/requirements-ci.txt
.venv/bin/python -m pip check
.venv/bin/python tests/supply_chain.py
```

The test rejects mutable Action references, broad or unexpected token grants,
persisted checkout credentials, and unlocked pip installs. It executes the
actual yq installation step with isolated download/installation shims and
proves that a bad checksum or failed download prevents installation.

When updating a dependency, verify its upstream commit/digest or release wheel
hash, update transitive Python pins together, and rerun the schema and
infrastructure tests. Do not remove `--require-hashes` to make an update pass.
Dependabot proposes changes; passing CI and maintainer review are still needed.

## Maintainer actions outside the checkout

For main, configure a GitHub ruleset that blocks force pushes and deletion,
requires pull requests, and requires the always-running CI `test` check. Require
an actual second-person approval when a reviewer is available. Do not make the
path-filtered Kubernetes job mandatory for every PR without an always-running
aggregate check, because unrelated PRs would wait for a check that never runs.

Best Practices enrollment and genuine human reviews need maintainer work.
Fuzzing and signing now have real repository integrations; their public status
must still be confirmed. See the [operating guide](fuzzing-and-release-signatures.md).
After the repository changes land on main, Scorecard runs on push or can be launched
manually; its public report and badge may update later.

References: [Scorecard checks](https://github.com/ossf/scorecard/blob/c395761df6afe1a69e476bc60a013a94bcbc153f/docs/checks.md),
[pip secure installs](https://pip.pypa.io/en/stable/topics/secure-installs/), and
[Scorecard publication restrictions](https://github.com/ossf/scorecard-action#publishing-results).
