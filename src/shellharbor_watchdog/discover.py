"""Launch offline discovery with the existing Bash command-line interface."""

from collections.abc import Sequence

from .cli import _launch


def main(argv: Sequence[str] | None = None) -> int:
    """Run through the console script or ``python -m shellharbor_watchdog.discover``."""
    return _launch("watchdog-discover.sh", argv)


if __name__ == "__main__":
    raise SystemExit(main())
