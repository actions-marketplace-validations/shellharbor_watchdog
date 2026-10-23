#!/usr/bin/env python3
"""Atheris/libFuzzer entrypoint; failures produce replayable crash inputs."""

import sys

import atheris

with atheris.instrument_imports():
    from fuzz_harness import check_input


def main() -> None:
    atheris.Setup(sys.argv, check_input)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
