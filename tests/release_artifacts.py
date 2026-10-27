"""Release archive and fail-closed signing/upload regression tests."""

import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("package_release", ROOT / "scripts" / "package-release.py")
packaging = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packaging)


class ArchiveTests(unittest.TestCase):
    def repository(self, root):
        root.mkdir()
        for args in (("init",), ("config", "user.name", "Synthetic Test"),
                     ("config", "user.email", "test@example.invalid")):
            packaging.git(root, *args)
        (root / "VERSION").write_text("1.2.3\n")
        (root / "service-watchdog.sh").write_text("#!/bin/bash\nprintf healthy\n")
        packaging.git(root, "add", "VERSION", "service-watchdog.sh")
        packaging.git(root, "commit", "-m", "Synthetic release")
        packaging.git(root, "tag", "v1.2.3")

    def test_deterministic_archive_uses_committed_sources_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            self.repository(repo)
            (repo / "secret.env").write_text("synthetic-untracked-secret")
            (repo / "service-watchdog.sh").write_text("dirty checkout changes")
            first = packaging.package(repo, "v1.2.3", root / "first")
            second = packaging.package(repo, "v1.2.3", root / "second")
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with tarfile.open(first) as archive:
                self.assertNotIn("watchdog-1.2.3/secret.env", archive.getnames())
                script = archive.extractfile("watchdog-1.2.3/service-watchdog.sh").read()
                self.assertIn(b"printf healthy", script)
                self.assertNotIn(b"dirty", script)
            digest = hashlib.sha256(first.read_bytes()).hexdigest()
            self.assertEqual((first.parent / "SHA256SUMS").read_text(), f"{digest}  {first.name}\n")
            with self.assertRaises(FileExistsError):
                packaging.package(repo, "v1.2.3", root / "first")

    def test_invalid_missing_and_mismatched_tag_cannot_package(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            self.repository(repo)
            packaging.git(repo, "tag", "v9.9.9")
            for tag, error in (("--output=/tmp/unsafe", ValueError),
                               ("v9.9.9", ValueError), ("v8.8.8", subprocess.CalledProcessError)):
                with self.subTest(tag=tag), self.assertRaises(error):
                    packaging.package(repo, tag, root / "artifacts")
            self.assertFalse((root / "artifacts").exists())


class SigningTests(unittest.TestCase):
    def run_signer(self, mode="new", verify_failure=False, bad_ref=False,
                   bad_repo=False, bad_checksum=False, missing_file=False,
                   bad_tag=False, sign_failure=False):
        with tempfile.TemporaryDirectory(prefix="watchdog-sign-test-") as directory:
            root = Path(directory)
            artifacts = root / "artifacts"
            artifacts.mkdir()
            archive = artifacts / "watchdog-1.2.3.tar.gz"
            archive.write_bytes(b"synthetic committed archive")
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            (artifacts / "SHA256SUMS").write_text(f"{digest}  {archive.name}\n")
            if bad_checksum:
                archive.write_bytes(b"tampered bytes")
            if missing_file:
                archive.unlink()
            binaries = root / "bin"
            binaries.mkdir()
            tools = {
                "cosign": '''#!/usr/bin/env python3
import os, pathlib, sys
args = sys.argv[1:]
with open(os.environ['TEST_COMMANDS'], 'a') as log:
    log.write('cosign ' + ' '.join(args) + '\\n')
if args[0] == 'sign-blob':
    if os.environ['TEST_SIGN_FAILURE'] == 'true':
        sys.exit(1)
    pathlib.Path(args[args.index('--bundle') + 1]).write_text('synthetic bundle')
else:
    assert args[args.index('--certificate-identity') + 1] == 'https://github.com/shellharbor/watchdog/.github/workflows/release-signing.yml@refs/tags/v1.2.3'
    assert args[args.index('--certificate-oidc-issuer') + 1] == 'https://token.actions.githubusercontent.com'
    if os.environ['TEST_VERIFY_FAILURE'] == 'true':
        sys.exit(1)
    if pathlib.Path(args[args.index('--bundle') + 1]).read_text() != 'synthetic bundle':
        sys.exit(1)
''',
                "gh": '''#!/usr/bin/env python3
import os, pathlib, shutil, sys
args = sys.argv[1:]
with open(os.environ['TEST_COMMANDS'], 'a') as log:
    log.write('gh ' + ' '.join(args) + '\\n')
mode = os.environ['TEST_MODE']
names = ['watchdog-1.2.3.tar.gz', 'SHA256SUMS', 'watchdog-1.2.3.tar.gz.sigstore.json', 'SHA256SUMS.sigstore.json']
if args[1] == 'view':
    if mode in ('existing', 'different', 'bad-signature'):
        print('\\n'.join(names))
    elif mode == 'partial':
        print(names[0])
elif args[1] == 'download':
    name = args[args.index('--pattern') + 1]
    target = pathlib.Path(args[args.index('--dir') + 1]) / name
    shutil.copyfile(pathlib.Path(os.environ['TEST_ARTIFACTS']) / name, target)
    if mode == 'different' and not name.endswith('.json'):
        target.write_text('different bytes')
    if mode == 'bad-signature' and name.endswith('.json'):
        target.write_text('invalid bundle')
else:
    assert '--clobber' not in args
    pathlib.Path(os.environ['TEST_UPLOADED']).write_text(' '.join(args))
''',
            }
            for name, text in tools.items():
                path = binaries / name
                path.write_text(text)
                path.chmod(0o755)
            uploaded = root / "uploaded"
            commands = root / "commands"
            env = dict(os.environ, GITHUB_REPOSITORY="other/watchdog" if bad_repo else "shellharbor/watchdog",
                       GITHUB_REF="refs/heads/main" if bad_ref else "refs/tags/v1.2.3",
                       TEST_COMMANDS=str(commands), TEST_UPLOADED=str(uploaded),
                       TEST_ARTIFACTS=str(artifacts), TEST_MODE=mode,
                       TEST_VERIFY_FAILURE=str(verify_failure).lower(),
                       TEST_SIGN_FAILURE=str(sign_failure).lower())
            env["PATH"] = str(binaries) + os.pathsep + env["PATH"]
            result = subprocess.run(["bash", str(ROOT / "scripts" / "sign-release.sh"),
                                     str(artifacts), "invalid-tag" if bad_tag else "v1.2.3"], env=env, text=True,
                                    capture_output=True, timeout=30)
            output = uploaded.read_text() if uploaded.exists() else ""
            calls = commands.read_text() if commands.exists() else ""
            return result, output, calls

    def test_new_assets_are_signed_verified_then_uploaded(self):
        result, output, calls = self.run_signer()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("SHA256SUMS.sigstore.json", output)
        self.assertLess(calls.index("cosign verify-blob"), calls.index("gh release upload"))

    def test_invalid_signature_never_uploads(self):
        result, output, _ = self.run_signer(verify_failure=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(output, "")

    def test_existing_verified_assets_are_not_replaced(self):
        result, output, _ = self.run_signer(mode="existing")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(output, "")

    def test_partial_upload_can_be_repaired(self):
        result, output, _ = self.run_signer(mode="partial")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("watchdog-1.2.3.tar.gz ", output)
        self.assertIn("watchdog-1.2.3.tar.gz.sigstore.json", output)

    def test_different_assets_and_wrong_ref_cannot_upload(self):
        for kwargs in ({"mode": "different"}, {"bad_ref": True}):
            with self.subTest(kwargs=kwargs):
                result, output, _ = self.run_signer(**kwargs)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(output, "")

    def test_bad_metadata_and_checksum_cannot_reach_signer(self):
        for kwargs in ({"bad_repo": True}, {"bad_tag": True},
                       {"bad_checksum": True}, {"missing_file": True}):
            with self.subTest(kwargs=kwargs):
                result, output, calls = self.run_signer(**kwargs)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(output, "")
                self.assertEqual(calls, "")

    def test_signing_failure_and_bad_existing_bundle_never_upload(self):
        for kwargs in ({"sign_failure": True}, {"mode": "bad-signature"}):
            with self.subTest(kwargs=kwargs):
                result, output, _ = self.run_signer(**kwargs)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(output, "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
