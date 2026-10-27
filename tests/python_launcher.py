"""Unit checks for the Python launcher's literal-argv and no-supervisor contract."""

from contextlib import redirect_stderr
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shellharbor_watchdog import cli, discover


class ReplacedProcess(Exception):
    """Stand in for execve's successful process replacement."""


class LauncherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="watchdog-python-launcher-")
        self.addCleanup(self.temporary.cleanup)
        self.runtime = Path(self.temporary.name) / "runtime with spaces"
        self.runtime.mkdir()
        for name in ("service-watchdog.sh", "watchdog-discover.sh", "VERSION"):
            (self.runtime / name).write_text("synthetic fixture\n", encoding="utf-8")
        self.platform = patch.object(cli.sys, "platform", "linux").start()
        self.addCleanup(patch.stopall)
        patch.object(cli, "RUNTIME_DIRECTORY", self.runtime).start()
        self.which = patch.object(cli.shutil, "which", return_value="/test tools/bash").start()
        self.execute = patch.object(cli.os, "execve", side_effect=ReplacedProcess).start()

    def launch(self, arguments: list[str], environment: dict[str, str] | None = None,
               entrypoint=cli.main) -> tuple:
        with patch.dict(os.environ, environment or {}, clear=True):
            with self.assertRaises(ReplacedProcess):
                entrypoint(arguments)
        return self.execute.call_args.args

    def test_arguments_are_not_interpreted_or_reordered(self) -> None:
        arguments = ["status", "-c", "/config with spaces/$(touch marker).yaml", "--json", ""]
        executable, forwarded, _ = self.launch(arguments)
        self.assertEqual(executable, "/test tools/bash")
        self.assertEqual(forwarded, [executable, str(self.runtime / "service-watchdog.sh"), *arguments])

    def test_discovery_uses_its_own_bundled_script(self) -> None:
        _, forwarded, _ = self.launch(["--source", "systemd"], entrypoint=discover.main)
        self.assertEqual(forwarded[1:], [str(self.runtime / "watchdog-discover.sh"), "--source", "systemd"])

    def test_environment_is_preserved_and_caller_is_not_modified(self) -> None:
        original = {"WATCHDOG_CONFIG": "/private/config.yaml", "SMTP_PASSWORD": "synthetic-test-secret",
                    "NO_COLOR": "1", "PATH": "/test/path"}
        with patch.dict(os.environ, original, clear=True):
            with self.assertRaises(ReplacedProcess):
                cli.main(["validate"])
            self.assertEqual(dict(os.environ), original)
        self.assertEqual(self.execute.call_args.args[2], original)

    def test_unset_and_empty_config_use_current_directory(self) -> None:
        for environment in ({}, {"WATCHDOG_CONFIG": ""}):
            with self.subTest(environment=environment):
                _, _, forwarded = self.launch(["--help"], environment)
                self.assertEqual(forwarded["WATCHDOG_CONFIG"], str(Path.cwd() / "config.yaml"))

    def test_default_arguments_come_from_sys_argv(self) -> None:
        with patch.object(sys, "argv", ["shellharbor-watchdog", "validate", "-c", "config.yaml"]):
            with self.assertRaises(ReplacedProcess):
                cli.main()
        self.assertEqual(self.execute.call_args.args[1][2:], ["validate", "-c", "config.yaml"])

    def test_explicit_empty_arguments_do_not_read_sys_argv(self) -> None:
        with patch.object(sys, "argv", ["shellharbor-watchdog", "unexpected"]):
            _, arguments, _ = self.launch([])
        self.assertEqual(len(arguments), 2)

    def test_unsupported_platform_and_missing_bash_fail_with_two(self) -> None:
        for platform, bash in (("win32", "/test/bash"), ("darwin", "/test/bash"), ("linux", None)):
            with self.subTest(platform=platform, bash=bash):
                with patch.object(cli.sys, "platform", platform), patch.object(cli.shutil, "which", return_value=bash):
                    with redirect_stderr(io.StringIO()) as errors:
                        self.assertEqual(cli.main(["--help"]), 2)
                    self.assertIn("Bash 4.3+", errors.getvalue())
        self.execute.assert_not_called()

    def test_missing_runtime_or_version_fails_without_execution(self) -> None:
        for name in ("service-watchdog.sh", "VERSION"):
            with self.subTest(name=name):
                path = self.runtime / name
                path.unlink()
                with redirect_stderr(io.StringIO()) as errors:
                    self.assertEqual(cli.main([]), 2)
                self.assertIn("Reinstall", errors.getvalue())
                path.write_text("synthetic fixture\n", encoding="utf-8")
        self.execute.assert_not_called()

    def test_startup_error_does_not_echo_secrets_or_arguments(self) -> None:
        self.execute.side_effect = OSError("synthetic-secret-in-an-exception")
        with redirect_stderr(io.StringIO()) as errors:
            self.assertEqual(cli.main(["synthetic-secret-in-an-argument"]), 2)
        self.assertNotIn("synthetic-secret", errors.getvalue())
        self.assertIn("Cannot execute", errors.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
