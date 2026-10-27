"""Deterministic seed/invariant regressions for the real fuzzing harness."""

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("fuzz_harness", ROOT / ".clusterfuzzlite" / "fuzz_harness.py")
harness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harness)


class FuzzingTests(unittest.TestCase):
    def test_serializers_round_trip_all_bash_control_characters(self):
        harness.check_serializers("".join(chr(value) for value in range(1, 32)))

    def test_unicode_and_shell_input_is_literal(self):
        harness.check_serializers('"<&>\\\n雪 $(touch /tmp/never-run) `id`')

    def test_validation_does_not_execute_command_or_create_state(self):
        harness.check_configuration(b"$(touch /tmp/never-run)", structured=True)

    def test_invalid_yaml_preserves_exit_contract(self):
        for payload in (b"services: []", b"services: [", b"\x00\xff", b"templates: {a: {template: a}}\nservices: []"):
            with self.subTest(payload=payload):
                harness.check_configuration(payload)

    def test_committed_seed_corpus(self):
        for path in sorted((ROOT / ".clusterfuzzlite" / "corpus").iterdir()):
            with self.subTest(seed=path.name):
                harness.check_input(path.read_bytes())
        harness.check_input(b"")
        harness.check_input(b"a" * (harness.MAX_INPUT + 1))


if __name__ == "__main__":
    unittest.main(verbosity=2)
