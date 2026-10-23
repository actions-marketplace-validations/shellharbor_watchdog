"""Build/install boundary and actual Linux runtime checks for wheel and sdist."""

import argparse
from configparser import ConfigParser
from email.parser import BytesParser
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
import unittest
import venv
import zipfile


ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
DIST = ROOT / "dist"
RESOURCES = {
    "service-watchdog.sh": ROOT / "service-watchdog.sh",
    "watchdog-discover.sh": ROOT / "watchdog-discover.sh",
    "VERSION": ROOT / "VERSION",
    "config.example.yaml": ROOT / "config.example.yaml",
    "schema/watchdog.schema.json": ROOT / "schema" / "watchdog.schema.json",
}


def run(arguments: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(arguments, capture_output=True, text=True, timeout=120, check=False, **kwargs)


@unittest.skipUnless(sys.platform == "linux", "The bundled runtime requires Linux")
class PackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.directory = tempfile.TemporaryDirectory(prefix="watchdog-python-package-")
        cls.addClassCleanup(cls.directory.cleanup)
        cls.work = Path(cls.directory.name)
        wheels = list(DIST.glob(f"shellharbor_watchdog-{VERSION}-*.whl"))
        if len(wheels) != 1:
            raise AssertionError("Build exactly one current-version wheel before running package tests")
        cls.wheel = wheels[0]
        cls.sdist = DIST / f"shellharbor_watchdog-{VERSION}.tar.gz"
        cls.prefix = cls.work / "venv with spaces"
        venv.EnvBuilder(with_pip=True).create(cls.prefix)
        cls.python = str(cls.prefix / "bin" / "python")
        cls.console = str(cls.prefix / "bin" / "shellharbor-watchdog")
        cls.environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", WATCHDOG_CONFIG="")
        for key in ("PYTHONPATH", "PYTHONHOME"):
            cls.environment.pop(key, None)
        result = run([cls.python, "-m", "pip", "install", "--disable-pip-version-check",
                      "--no-index", "--no-deps", str(cls.wheel)], env=cls.environment)
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)

    def invoke(self, arguments: list[str], *, module=False, env=None, cwd=None) -> subprocess.CompletedProcess:
        prefix = [self.python, "-m", "shellharbor_watchdog"] if module else [self.console]
        return run([*prefix, *arguments], env=env or self.environment, cwd=cwd or self.work)

    def config(self, directory: Path, command="true") -> Path:
        path = directory / "config.yaml"
        path.write_text(json.dumps({
            "settings": {"log_file": str(directory / "watchdog.log"),
                         "lock_file": str(directory / "watchdog.lock"),
                         "state_directory": str(directory / "state"),
                         "default_attempts": 1, "default_retry_delay": 0},
            "services": [{"name": "python-runtime", "check": {
                "type": "command", "commands": [{"command": [command]}]}}],
        }), encoding="utf-8")
        return path

    def test_wheel_metadata_and_resources_match_repository(self) -> None:
        with zipfile.ZipFile(self.wheel) as archive:
            dist_info = f"shellharbor_watchdog-{VERSION}.dist-info/"
            metadata = BytesParser().parsebytes(archive.read(dist_info + "METADATA"))
            self.assertEqual(metadata["Name"], "shellharbor-watchdog")
            self.assertEqual(metadata["Version"], VERSION)
            self.assertEqual(metadata["Requires-Python"], ">=3.11")
            self.assertEqual(metadata.get_all("Requires-Dist", []), [])
            self.assertEqual(metadata["License-Expression"], "MIT")
            entries = ConfigParser()
            entries.read_string(archive.read(dist_info + "entry_points.txt").decode())
            self.assertEqual(entries["console_scripts"]["shellharbor-watchdog"], "shellharbor_watchdog.cli:main")
            self.assertEqual(entries["console_scripts"]["shellharbor-watchdog-discover"],
                             "shellharbor_watchdog.discover:main")
            for name, source in RESOURCES.items():
                self.assertEqual(archive.read("shellharbor_watchdog/_runtime/" + name), source.read_bytes())
            for name in archive.namelist():
                self.assertTrue(name.startswith(("shellharbor_watchdog/", dist_info)), name)
                self.assertFalse(any(part in {".git", ".env", "ai-kit", ".agents", "__pycache__"}
                                     for part in Path(name).parts), name)

    def test_sdist_rebuilds_the_same_wheel_without_checkout(self) -> None:
        extracted = self.work / "sdist"
        extracted.mkdir()
        with tarfile.open(self.sdist) as archive:
            # Artifacts are locally built; still reject links and unsafe paths.
            for item in archive.getmembers():
                target = (extracted / item.name).resolve()
                self.assertTrue(target.is_relative_to(extracted.resolve()))
                self.assertFalse(item.issym() or item.islnk())
                if Path(item.name).name in {"AGENTS.md", "PROJECT_CONTEXT.md", ".env", "SKILL.md"}:
                    self.fail("Private checkout content included in sdist: " + item.name)
            archive.extractall(extracted, filter="data")
        roots = list(extracted.iterdir())
        self.assertEqual(len(roots), 1)
        output = self.work / "rebuilt"
        result = run([sys.executable, "-m", "build", "--no-isolation", "--wheel", "--outdir", str(output),
                      str(roots[0])], env=self.environment, cwd=self.work)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        rebuilt = output / self.wheel.name
        self.assertEqual(hashlib.sha256(rebuilt.read_bytes()).digest(),
                         hashlib.sha256(self.wheel.read_bytes()).digest())

    def test_installed_console_and_modules_report_version_and_help(self) -> None:
        for module in (False, True):
            with self.subTest(module=module):
                result = self.invoke(["--version"], module=module)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), "service-watchdog.sh " + VERSION)
        for arguments in ([str(self.prefix / "bin" / "shellharbor-watchdog-discover"), "--help"],
                          [self.python, "-m", "shellharbor_watchdog.discover", "--help"]):
            result = run(arguments, env=self.environment, cwd=self.work)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Usage:", result.stdout)

    def test_validate_default_config_and_environment_are_read_only(self) -> None:
        with tempfile.TemporaryDirectory(dir=self.work) as name:
            directory = Path(name)
            path = self.config(directory)
            before = set(directory.rglob("*"))
            result = self.invoke(["validate"], cwd=directory)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(set(directory.rglob("*")), before)
            result = self.invoke(["validate"], env=dict(self.environment, WATCHDOG_CONFIG=str(path)))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(set(directory.rglob("*")), before)
            result = self.invoke(["validate", "-c", str(path)],
                                 env=dict(self.environment, WATCHDOG_CONFIG="/nonexistent/config.yaml"))
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_actual_runtime_preserves_healthy_failure_and_invalid_exits(self) -> None:
        for command, expected in (("true", 0), ("false", 1)):
            with self.subTest(command=command), tempfile.TemporaryDirectory(dir=self.work) as name:
                directory = Path(name)
                path = self.config(directory, command)
                result = self.invoke(["--dry-run", "-c", str(path)])
                self.assertEqual(result.returncode, expected, result.stderr)
                self.assertFalse((directory / "state" / "python-runtime.state").exists())
                result = self.invoke(["-c", str(path)])
                self.assertEqual(result.returncode, expected, result.stderr)
                self.assertTrue((directory / "state" / "python-runtime.state").is_file())
        with tempfile.TemporaryDirectory(dir=self.work) as name:
            path = self.config(Path(name))
            invalid = json.loads(path.read_text(encoding="utf-8"))
            invalid["services"] = []
            path.write_text(json.dumps(invalid), encoding="utf-8")
            result = self.invoke(["validate", "-c", str(path)])
            self.assertEqual(result.returncode, 2)
            self.assertIn("services", result.stdout + result.stderr)

    def test_literal_argv_streams_exit_codes_and_process_identity(self) -> None:
        with tempfile.TemporaryDirectory(dir=self.work) as name:
            directory = Path(name)
            bash = directory / "bash"
            bash.write_text('#!/bin/sh\nprintf "%s" "$$" > "$TEST_PID"\n'
                            'printf "%s\\0" "$@" > "$TEST_ARGV"\n'
                            'printf "fixture-out\\n"\nprintf "fixture-err\\n" >&2\n'
                            'exit "$TEST_EXIT"\n', encoding="utf-8")
            bash.chmod(0o755)
            arguments = ["-c", "$(touch unexpected-execution).yaml", "a b", "", "--json"]
            for code in (0, 1, 2):
                environment = dict(self.environment, PATH=str(directory) + os.pathsep + os.environ["PATH"],
                                   TEST_PID=str(directory / "pid"), TEST_ARGV=str(directory / "argv"),
                                   TEST_EXIT=str(code))
                with subprocess.Popen([self.console, *arguments], cwd=directory, env=environment,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as process:
                    stdout, stderr = process.communicate(timeout=10)
                    self.assertEqual(process.returncode, code)
                    self.assertEqual(int((directory / "pid").read_text()), process.pid)
                self.assertEqual(stdout, "fixture-out\n")
                self.assertEqual(stderr, "fixture-err\n")
                forwarded = (directory / "argv").read_bytes().split(b"\0")[:-1]
                self.assertEqual(Path(os.fsdecode(forwarded[0])).name, "service-watchdog.sh")
                self.assertEqual([os.fsdecode(item) for item in forwarded[1:]], arguments)
                self.assertFalse((directory / "unexpected-execution").exists())

    def test_sigterm_reaches_the_replaced_process(self) -> None:
        with tempfile.TemporaryDirectory(dir=self.work) as name:
            directory = Path(name)
            bash = directory / "bash"
            bash.write_text('#!/bin/sh\ntrap "exit 2" TERM\nprintf ready > "$TEST_READY"\n'
                            'while :; do sleep 0.1; done\n', encoding="utf-8")
            bash.chmod(0o755)
            ready = directory / "ready"
            environment = dict(self.environment, PATH=str(directory) + os.pathsep + os.environ["PATH"],
                               TEST_READY=str(ready))
            process = subprocess.Popen([self.console], env=environment, cwd=directory, start_new_session=True,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                deadline = time.monotonic() + 10
                while not ready.exists() and time.monotonic() < deadline and process.poll() is None:
                    time.sleep(0.02)
                self.assertTrue(ready.exists(), "Replacement process did not become ready")
                process.send_signal(signal.SIGTERM)
                process.communicate(timeout=5)
                self.assertEqual(process.returncode, 2)
            finally:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.communicate()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist-dir", type=Path, default=DIST)
    arguments, remaining = parser.parse_known_args()
    DIST = arguments.dist_dir.resolve()
    unittest.main(argv=[sys.argv[0], *remaining], verbosity=2)
