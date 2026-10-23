# Changelog

After every task with file changes, briefly record what changed and why: features, fixes, internal work, dependencies, documentation, and AI-KIT. Keep new entries under `Unreleased` until a release is confirmed; use verified dates and versions. Tasks without file changes need no entry.

## Unreleased

### Fixed

- Updated the SHA-pinned official Cosign installer to v4.1.2 in CI and release
  signing. Its Sigstore-bundle verification supports the existing Cosign 3.1.3
  pin, instead of requesting the removed detached `.sig` asset. This repairs
  hosted CI without disabling integrity checks or changing the signing CLI.

### Added

- Optional `shellharbor-watchdog` Python 3.11+ package with monitor and discovery
  console/module entrypoints. It bundles the existing Bash runtime, forwards
  literal argv through process replacement, retains signals/exit codes, and
  defaults Python config lookup to the caller's `config.yaml` without writing
  to site-packages or changing native/container dependencies.
- Hatchling wheel/sdist builds using the root `VERSION`, explicit package
  resources and source-archive allowlists, hash-locked build tools, clean-install
  and reproducible-rebuild tests, Python 3.11/3.12 launcher CI, and a separate
  manual-only TestPyPI/PyPI Trusted Publishing workflow. No registry upload is
  performed automatically on pushes or GitHub releases.

### Changed

- Replaced obsolete required Go check contexts on `main` with the actual Bash
  regression/lint, Python 3.11/3.12 launcher, wheel/sdist installation, and
  GitHub Actions CodeQL checks, bound to the GitHub Actions integration.
  Preserved the required PR approval and every other existing ruleset setting
  so publication can proceed without bypassing review protection.
- Registered and verified the TestPyPI pending Trusted Publisher bound to
  `shellharbor/watchdog`, `pypi-publish.yml`, and `testpypi`. Recorded the
  remaining publication prerequisites and the mismatch between required
  main-branch status contexts and the actual Bash/Python CI; no package upload
  or branch-protection change was performed.
- Configured separate GitHub `testpypi` and `pypi` environments restricted to
  `main`, with explicit owner approval for production. Clarified the distinction
  between the workflow execution branch and the immutable release-tag input to
  avoid deployment-policy failures. Production publisher registration and
  distribution uploads remain separate, uncompleted steps.
- Extended dependency-update and supply-chain checks to the Python backend,
  packaging lock, and least-privilege publisher. Added a safe example and Python
  package Wiki guide; synchronized README, release instructions, project skills,
  local context/navigation, and the architecture decision for the new surface.

### AI-KIT

- 2026-10-05: separated the language policy: all authored project files and artifacts remain English, while chat with the user uses Russian for questions, plans, progress, explanations, review summaries, and final reports. Project artifacts shown in chat retain English. Synchronized instructions, bootstrap, context, continuity skill, engineering/router rules, README, wiki, and decision log to preserve this distinction.
- 2026-10-05: replaced the former Terra-based defaults with the user's Adaptive Model Router: Luna for bounded tasks, Sol 6.1 for engineering, and justified Astra escalation. Optimizes total cost to a correct result rather than the price of one call.
- 2026-10-05: added runtime capability verification, independent reasoning/service-tier/context decisions, standard/pro criteria, the large-input pricing boundary, cache/output budgets, conditional reviewers/delegation, diagnosed retries, and compact JSON router decisions. Distinguished policy fields from supported execution controls.
- 2026-10-05: synchronized bootstrap, agent/review rules, context and continuity skill, intent, navigation, and README; recorded the routing decision and consequences in a kit ADR. Runtime availability and switching remain explicitly unverified until project adaptation.
- v0.1: added agent instructions, context, a skill, stack and engineering rules, model routing, and the bootstrap prompt.
- Summarized the available voice context; added thin adapters, the skill registry, and stack skills; recovered the user's Laravel agreements from the earlier AI-Kit task.
- Added a Docker daemon check and a request for the user to start it for container-dependent tasks.
- Added a universal `.gitignore` for PHP/Laravel/Moodle/Go, development artifacts, secrets, and local AI-KIT files.
- Added local Go cache directories and `*.out` files to `.gitignore`.
- Clarified the `composer.lock` policy: versioned by default for applications, with an optional exclusion for libraries.
- Clarified that `go.mod` and `go.sum` remain versioned for Go modules.
- Added Python script rules and a skill; `.gitignore` excludes virtual environments, caches, coverage output, and build artifacts while keeping configuration and lockfiles versioned.
- Made `CHANGELOG.md` updates mandatory after every task with file changes to preserve the history of reasons and results, including internal changes and the kit itself.
- Added a mandatory Kubernetes-ready standard for new Dockerfiles, containers, and microservices: portable images, configuration, security, shutdown, health checks, storage, and minimal manifests. Integrated the rule into instructions, context, the skill, and bootstrap so services are ready for Kubernetes from the start.
- 2026-10-04: translated all AI-KIT documents, adapters, rules, templates, and the bootstrap prompt into English; established English as the language for future kit updates.
- 2026-10-04: extended the English language requirement to all authored project content and agent communication, including code, UI text, logs, Git messages, reviews, and reports, so future project work follows one language policy.

## [1.7.9] - 2026-10-15

### Added

- ClusterFuzzLite/Atheris mutation fuzzing for configuration validation and
  JSON, HTML, and Prometheus serialization boundaries. Includes a compiled
  standalone target, seed corpus, bounded execution, scheduled/PR checks, and
  deterministic regression tests.
- Deterministic tagged-source `watchdog-X.Y.Z.tar.gz` release archives,
  `SHA256SUMS`, and keyless Cosign/Sigstore signature bundles through GitHub
  OIDC. Signatures are verified against the exact release workflow/tag identity
  and issuer before upload. Reruns preserve valid existing assets and repair
  missing uploads without overwriting files.
- Supply-chain regression checks, offline signature/tampering tests, an
  evidence-based OpenSSF Scorecard audit, and fuzzing/signature verification
  documentation.

### Security

- Pinned GitHub Actions and the Bash compatibility image to immutable
  revisions; hash-locked CI Python dependencies and verified yq downloads
  before installation.
- Disabled persisted checkout credentials and narrowed workflow token
  permissions. Signing write permissions are limited to the release-signing
  job.
- Expanded Dependabot coverage to CI Python dependencies and all three
  Dockerfile locations. Updated the security policy to identify the current
  supported release through `VERSION`.

### Fixed

- Escaped uncommon JSON control characters below U+0020, fixing a defect
  exposed by fuzzing while preserving existing serialization behavior.
- Restored published changelog history alongside existing local AI-KIT notes
  so release metadata checks retain their version headings.
- Made the Helm default-image regression test derive its expected tag from
  `VERSION` instead of a stale hard-coded release.

### Changed

- Synchronized CLI release metadata, README archive instructions, deployment
  examples, and Helm chart `0.1.1` (`appVersion: 1.7.9`) for this release.
- Updated release preparation guidance and verified local project context and
  continuity skill. Signing is enabled for new releases containing the workflow;
  existing tags and assets are not retroactively replaced.
- Verified the freshly built v1.7.9 amd64 runtime in an isolated kind 0.30.0 /
  Kubernetes 1.34.0 cluster before publication: finite CronJob success,
  persistent PVC state, no Docker socket access, and invalid-config exit 2.
  Rechecked strict Helm lint and all six chart contract tests; recorded the
  result in local project context and removed the test cluster.

## [1.7.8] - 2026-10-04

### Added

- First-class Kubernetes support through a Helm 3 chart for Kubernetes 1.31+
  that runs the existing production Watchdog image as a suspended-by-default,
  finite CronJob or an explicit manual Job. It preserves Watchdog's one-shot
  exit-code lifecycle rather than introducing a controller or daemon.
- Durable state PVC support, operator-owned Secret environment references,
  pinned-image digest support, bounded `/tmp`, explicit resources, CronJob
  overlap protection, and an isolated non-root pod profile. The chart creates
  no RBAC resources and does not mount a service-account token, host paths,
  Docker socket, or privileged capabilities.
- Kubernetes CI coverage: strict Helm linting, rendered-chart safety/negative
  tests, and an actual runtime-image cycle in a private kind cluster that
  checks success, durable state, lack of Docker socket access, and invalid
  configuration exit handling.

## [1.7.6] - 2026-09-30

### Added

- Opt-in HTTP transport settings for private CA trust, mutual TLS client
  certificates, and authenticated HTTP(S) proxies. Proxy credentials are read
  only from paired environment variables and are written only to a temporary
  mode-`0600` curl configuration file.

## [1.7.5] - 2026-09-30

### Added

- Opt-in Prometheus scheduler heartbeat metric
  (`<prefix>_heartbeat_timestamp_seconds`), emitted only after Watchdog
  completes a full normal monitor run and deliberately separate from service
  health. The metric carries only configured static labels, and cannot be
  refreshed by dry runs, read-only commands, runtime errors, or partial runs;
  partial metrics rewrites retain the previous timestamp instead of removing it.
- Ready observability assets: an importable Grafana Watchdog overview dashboard,
  Prometheus rules for stale heartbeat/unavailable/degraded services, and a
  secret-free Alertmanager routing snippet.
- Limited, opt-in JSON assertions for HTTP checks through `expect.json`.
  Operators can match exact typed scalar fields or regex-match selected string
  fields through safe root/property/index paths, without evaluating expressions
  or exposing response bodies and values in Watchdog output.
- Per-service notification routing through `services[].notify.channels`, with
  opt-in severity and runbook context for templates, PagerDuty, and Opsgenie.
  Existing configurations continue to deliver through every globally enabled
  channel when routing is omitted.
- First-class production Docker distribution alongside native, cron, and
  systemd deployment: a pinned, non-root runtime image, a separately tagged
  Docker CLI variant, a least-privilege Compose example, and a container-aware
  configuration template.
- Release-driven multi-architecture (`linux/amd64`, `linux/arm64`) publication
  to GHCR, optional Docker Hub publication when repository credentials exist,
  semantic image tags, OCI metadata, BuildKit provenance, and SBOMs.
- Docker runtime regression coverage for a read-only/non-root healthy cycle,
  invalid configuration exit status, configuration-only healthcheck, graceful
  signal handling, and the separately opt-in Docker socket image.
- A reusable release preflight that validates the intended tag against
  `VERSION`, generated CLI version, README archive instructions, changelog
  heading, and installer metadata before a release is created. The release
  workflow and versioning test now invoke this same check.

### Fixed

- The Docker entrypoint now forwards stop signals through an active Watchdog
  check process tree before waiting for cleanup. Long-running checks therefore
  preserve Watchdog's documented runtime exit code instead of being forcibly
  killed after Docker's stop timeout.

## [1.7.2] - 2026-09-26

### Added

- A self-contained GitHub Action for read-only Watchdog configuration
  validation in pull requests and deployment workflows.

## [1.6.0] - 2026-09-26

### Added

- Optional DNS record checks through `dig` and ICMP reachability checks through
  Linux `ping`, including answer, packet-loss, and average-RTT thresholds.
- PagerDuty and Opsgenie on-call notifications with incident-ID deduplication
  and automatic recovery resolution.
- Remote HTTP remediation with timeout/status validation, secret-safe temporary
  request files, and exact method/URL allowlisting in enforce mode.

## [1.5.0] - 2026-09-26

### Added

- Opt-in Status Page observed-availability bars backed by existing JSONL or
  SQLite history. They render the latest sampled result across configurable
  trailing-day intervals without introducing a web service or UI dependency.

### Changed

- Watchdog's maintainable source is now split into ordered `lib/watchdog/`
  modules while the installer and deployments continue to use the generated,
  self-contained `service-watchdog.sh` distribution. The build and release
  checks reject a stale generated script.
- Watchdog now snapshots the parsed configuration in memory and serves simple
  scalar, type, length, and map-entry lookups from that cache. The cache is
  rebuilt after template expansion, inherited by parallel check workers, and
  safely falls back to `yq` for complex expressions.
- Added a regression test that proves template validation remains correct while
  bounding configuration-parser invocations.

### Fixed

- Restored cache matching for dotted configuration paths and numeric array
  indexes, and preserved empty cache fields while loading maps and sequences.
  Ordinary reads no longer fall back to `yq` or mistake configured services for
  an empty list.

## [1.4.0] - 2026-09-26

### Added

- Opt-in `tls_cert` checks that alert when a TLS leaf certificate has fewer
  than the configured whole days remaining before expiry. They support a
  custom port and SNI name, reuse normal transition notifications, and report
  the expiry timestamp and `days_remaining` without persisting certificate data.
- A schema-annotated TLS certificate example, negative schema coverage, and
  deterministic OpenSSL-shim regression tests.

## [1.3.0] - 2026-09-26

### Added

- An OpenSSF Scorecard GitHub Actions workflow that publishes signed supply-chain
  security results to GitHub Code Scanning and the public Scorecard service,
  plus a live README badge.
- A CI compatibility gate that compiles every Bash source with Bash 4.3, the
  project's documented minimum supported Bash version.

### Security

- SMTP credentials are now supplied to curl through an ephemeral mode-`0600`
  configuration file instead of process arguments. The file is removed after
  delivery, and SMTP error output redacts the password before it reaches logs.

## [1.2.0] - 2026-09-26

### Added

- Smart HTTP checks: direct request headers with secret-safe `value_env`,
  optional response content-type and bounded body-regex assertions, and a
  `max_total_ms` latency SLO.
- HTTP latency gauges for Prometheus plus a schema-annotated Smart HTTP example
  and dedicated regression coverage for assertions, secret redaction,
  degradation, no-remediation behavior, and invalid configuration.

### Changed

- A successful HTTP response that exceeds `max_total_ms` is now represented as
  `degraded`, with transition alerts and metrics but without remediation,
  circuit-breaker, backoff, flapping, escalation, or unavailable-counter side
  effects.

## [1.1.8] - 2026-09-26

### Added

- A root `VERSION` file as the single release-version source for the CLI,
  installer, documentation, and release validation.
- GitHub community documents for security reporting, contributing, support,
  release management, and a Contributor Covenant Code of Conduct, plus focused
  issue and pull-request templates.
- `tests/run-all.sh`, the authoritative full regression runner. It rejects an
  unregistered test script before executing the complete deterministic suite.
- Version-metadata regression coverage and a release-tag workflow that verifies
  the Git tag, `VERSION`, CLI output, README archive link, and changelog entry.

### Changed

- GitHub Actions now runs Bash syntax checks and ShellCheck for every test
  script, followed by the complete regression suite on pushes and pull requests.
- The Quick Start, installer, test documentation, project skill, and Wiki now
  describe the version-file and authoritative test-runner workflow.

### Fixed

- The webhook regression test no longer combines `export` with command
  substitution, keeping the full suite compatible with ShellCheck.

## [1.1.7] - 2026-09-26

### Added

- A GitHub-ready `wiki/` documentation set with runnable examples for checks,
  alerts, remediation, reliability controls, status/history, discovery,
  federation, deployment, and troubleshooting.

### Changed

- Linked the project Wiki from the README and added repository rules requiring
  Wiki guidance and examples to remain synchronized with project changes.

## [1.1.6] - 2026-09-26

### Added

- Opt-in `clamav` scanning and `threshold` checks for journald, log files,
  socket states, and direct count commands, with template and hook variables.
- Security-check regression tests and a worked configuration example.
- Opt-in per-check history in JSONL or optional SQLite storage, with daily or
  single-file retention and read-only `--report` / `--trend` terminal views.
- History and trend regression coverage in CI, plus a configuration example.
- Opt-in `disk` health checks for filesystem free space, with GiB and percent
  thresholds and the existing failure/recovery notification channels.
- Disk-space regression coverage and an all-channel configuration example.
- Draft 2020-12 JSON Schema for the monitor configuration, with editor
  annotations in the example YAML files and CI checks for valid and invalid
  configurations.
- `notify-test` sends explicit test messages through enabled email and webhook
  channels without running checks or changing monitoring state.
- Read-only `status` command with terminal and JSON summaries, maintenance and
  remediation-block visibility, and optional orphaned state files.
- Regression tests for both commands in GitHub Actions.

### Fixed

- Filesystem `only_if` conditions now compare the actual free-space percentage
  instead of the used-space percentage reported by `df`.

## [1.1.4] - 2026-09-25

### Added

- Consolidated release documentation for the renamed ShellHarbor Watchdog
  project, including HTTP/TCP/command monitoring, secure argv remediation,
  email and webhook notifications, and systemd/cron deployment.
- Opt-in maintenance windows, escalation, circuit breakers, dependency chains,
  conditional checks, templates, parallel checks, Prometheus textfile metrics,
  static status pages, federation, and offline Docker Compose/systemd discovery.
- Draft 2020-12 configuration JSON Schema, `notify-test`, read-only `status`,
  examples, automated tests, and GitHub Actions/CodeQL workflows.

## [1.0.6] - 2026-08-15

### Added

- Built-in SMTP email notifications with YAML-configured connection settings,
  recipients, and failure/recovery templates.
- Transition-only delivery: one failure message per incident and one recovery
  message when the service becomes healthy again.
- Automated coverage for email delivery and duplicate suppression.

## [1.0.3] - 2026-08-15

### Added

- HTTP, TCP, and command-based health checks.
- Configurable retries, timeouts, remediation cooldowns, and post-action checks.
- Failure and recovery hooks with structured environment variables.
- Persistent service state and a global non-blocking execution lock.
- Dry-run and single-service modes.
- systemd service/timer units and cron documentation.
- Ready-to-adapt configurations in the `examples` directory.
- GitHub Actions smoke testing and ShellCheck validation.
- `-V` and `--version` options.

### Changed

- Improved installer dependency checks, runtime directory creation, and summary.
- Quick Start now uses the stable `v1.0.3` source archive.
- Expanded repository ignore rules and troubleshooting documentation.

[Unreleased]: https://github.com/shellharbor/watchdog/compare/v1.7.9...HEAD
[1.7.9]: https://github.com/shellharbor/watchdog/compare/v1.7.8...v1.7.9
[1.7.8]: https://github.com/shellharbor/watchdog/compare/v1.7.6...v1.7.8
[1.7.6]: https://github.com/shellharbor/watchdog/compare/v1.7.5...v1.7.6
[1.7.5]: https://github.com/shellharbor/watchdog/compare/v1.7.4...v1.7.5
[1.4.0]: https://github.com/shellharbor/watchdog/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/shellharbor/watchdog/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/shellharbor/watchdog/compare/v1.1.8...v1.2.0
[1.1.8]: https://github.com/shellharbor/watchdog/compare/v1.1.7...v1.1.8
[1.1.7]: https://github.com/shellharbor/watchdog/compare/v1.1.6...v1.1.7
[1.1.6]: https://github.com/shellharbor/watchdog/compare/v1.1.4...v1.1.6
[1.1.4]: https://github.com/shellharbor/watchdog/compare/v1.0.6...v1.1.4
[1.0.6]: https://github.com/shellharbor/watchdog/compare/v1.0.3...v1.0.6
[1.0.3]: https://github.com/shellharbor/watchdog/releases/tag/v1.0.3
