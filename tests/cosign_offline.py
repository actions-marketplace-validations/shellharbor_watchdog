"""Real cryptographic regression using disposable keys, with no OIDC/log upload."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class CosignTests(unittest.TestCase):
    def test_valid_signature_passes_and_tampering_or_wrong_key_fails(self):
        cosign = os.environ.get("COSIGN", "cosign")
        self.assertIsNotNone(shutil.which(cosign), "Cosign is required for this integration test")
        with tempfile.TemporaryDirectory(prefix="watchdog-cosign-") as directory:
            root = Path(directory)
            env = dict(os.environ, COSIGN_PASSWORD="")

            def invoke(*args):
                return subprocess.run([cosign, *map(str, args)], cwd=root, env=env,
                                      capture_output=True, text=True, timeout=60)

            for name in ("test", "wrong"):
                result = invoke("generate-key-pair", "--output-key-prefix", root / name)
                self.assertEqual(result.returncode, 0, result.stderr)
            artifact = root / "artifact"
            artifact.write_bytes(b"synthetic archive bytes\n")
            bundle = root / "artifact.sigstore.json"
            result = invoke("sign-blob", "--yes", "--key", root / "test.key",
                            "--tlog-upload=false", "--use-signing-config=false",
                            "--bundle", bundle, artifact)
            self.assertEqual(result.returncode, 0, result.stderr)
            # These flags are confined to disposable-key tests. Published
            # releases use OIDC identity/issuer and full transparency checking.
            verify = ("verify-blob", "--key", root / "test.pub", "--bundle", bundle,
                      "--insecure-ignore-tlog", artifact)
            result = invoke(*verify)
            self.assertEqual(result.returncode, 0, result.stderr)
            wrong_key = list(verify)
            wrong_key[2] = root / "wrong.pub"
            self.assertNotEqual(invoke(*wrong_key).returncode, 0)
            artifact.write_bytes(b"tampered archive bytes\n")
            self.assertNotEqual(invoke(*verify).returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
