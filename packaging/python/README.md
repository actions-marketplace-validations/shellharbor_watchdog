# ShellHarbor Watchdog

A Python launcher and installable distribution of
[ShellHarbor Watchdog](https://github.com/shellharbor/watchdog), the Linux
one-shot Bash service monitor. This is **not** the unrelated `watchdog` Python
filesystem-event library.

The package bundles the existing monitor, offline discovery tool, configuration
example, and JSON Schema. It does not rewrite the monitoring engine, start a
daemon, install system packages, register a scheduler, or download code at runtime.

## Requirements

- Python 3.11+ on Linux (including WSL).
- Bash 4.3+, Mike Farah yq v4, curl, flock, and GNU coreutils on `PATH`.
- Optional feature-specific tools remain required only for enabled features.

There are no Python runtime dependencies. Native Windows and macOS execution
are not supported; installation alone does not make the Bash engine portable.

## Installation

After the package has been published to PyPI:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install shellharbor-watchdog
.venv/bin/shellharbor-watchdog --version
```

For a local checkout before publication:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install .
```

Do not use `pip install watchdog`; that installs a different project.

## Usage

Create and review your own YAML configuration, then pass its path explicitly:

```bash
shellharbor-watchdog validate -c /etc/watchdog/config.yaml
shellharbor-watchdog --dry-run -c /etc/watchdog/config.yaml
shellharbor-watchdog -c /etc/watchdog/config.yaml
shellharbor-watchdog status -c /etc/watchdog/config.yaml --json
shellharbor-watchdog notify-test -c /etc/watchdog/config.yaml --channel telegram
```

Or run as a Python module:

```bash
python -m shellharbor_watchdog validate -c /etc/watchdog/config.yaml
python -m shellharbor_watchdog status -c /etc/watchdog/config.yaml --json
python -m shellharbor_watchdog.discover --help
shellharbor-watchdog-discover --help
```

Arguments are forwarded literally without `eval`, `shell=True`, or a `bash -c`
command string. The launcher replaces itself with Bash, preserving streams,
signals, and the existing `0` / `1` / `2` exit codes. `WATCHDOG_CONFIG` remains
supported; when it is unset or empty, the Python launchers use `config.yaml` in
the caller's current directory. `-c` takes precedence. Package resources are
never used as a writable configuration or state directory.

For cron/systemd, use the absolute installed executable path and an explicit
`-c` path. Installing this package does not schedule monitoring automatically.

## Configuration and features

The [configuration reference](https://github.com/shellharbor/watchdog/blob/main/README.md)
and [Wiki](https://github.com/shellharbor/watchdog/tree/main/wiki) describe HTTP,
TCP, command, disk, DNS, ping, TLS, remediation, notification routing, history,
maintenance, Prometheus, and Kubernetes deployment. Existing YAML and state
formats are unchanged. Keep secrets in the existing `*_env` fields, not in
command-line arguments or committed configuration.

## License

MIT. [Source and issues](https://github.com/shellharbor/watchdog).
