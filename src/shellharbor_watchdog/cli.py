"""Execute the bundled runtime without a shell command string or supervisor."""

from collections.abc import Sequence
import os
from pathlib import Path
import shutil
import sys


RUNTIME_DIRECTORY = Path(__file__).resolve().parent / "_runtime"


def _launch(script_name: str, argv: Sequence[str] | None = None) -> int:
    """Replace this process with Bash, retaining argv, streams, and exit status."""
    if sys.platform != "linux":
        print("ShellHarbor Watchdog requires Linux and Bash 4.3+. "
              "On Windows, run inside WSL or use the container image.", file=sys.stderr)
        return 2
    bash = shutil.which("bash")
    if bash is None:
        print("ShellHarbor Watchdog requires Bash 4.3+ on PATH.", file=sys.stderr)
        return 2
    try:
        script = RUNTIME_DIRECTORY / script_name
        if not script.is_file() or not (RUNTIME_DIRECTORY / "VERSION").is_file():
            print("The bundled Watchdog runtime is missing. Reinstall shellharbor-watchdog "
                  "from a wheel or source distribution.", file=sys.stderr)
            return 2
        environment = dict(os.environ)
        # A pip installation is not an operator configuration directory. Never
        # copy a config into site-packages or change the caller's working directory.
        if not environment.get("WATCHDOG_CONFIG"):
            environment["WATCHDOG_CONFIG"] = str(Path.cwd() / "config.yaml")
        arguments = list(sys.argv[1:] if argv is None else argv)
        os.execve(bash, [bash, str(script), *arguments], environment)
    except OSError:
        # Exception text/argv can contain operator data. Report no arguments or
        # environment values, especially when startup fails before Bash logging.
        print("Cannot execute the bundled Watchdog runtime with Bash.", file=sys.stderr)
        return 2
    return 2  # execve does not return on success.


def main(argv: Sequence[str] | None = None) -> int:
    """Run the monitor with its existing command-line interface."""
    return _launch("service-watchdog.sh", argv)
