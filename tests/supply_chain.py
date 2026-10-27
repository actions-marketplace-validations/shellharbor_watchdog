"""Offline regression checks for CI supply-chain and credential boundaries."""

from __future__ import annotations

import copy
import hashlib
import os
from pathlib import Path
import re
import subprocess
import tempfile
import tomllib
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
ACTION_PIN = re.compile(r"[^@\s]+@[0-9a-f]{40}\Z")
IMAGE_PIN = re.compile(r"[^@\s]+@sha256:[0-9a-f]{64}\Z")
WRITE_PERMISSIONS = {
    ("codeql.yml", "analyze"): {"security-events"},
    ("scorecard.yml", "analysis"): {"security-events", "id-token"},
    ("docker-publish.yml", "publish-ghcr"): {"packages"},
    ("release-signing.yml", "sign"): {"contents", "id-token"},
    ("pypi-publish.yml", "publish"): {"id-token"},
}


def workflow_errors(name: str, workflow: dict) -> list[str]:
    """Reject mutable actions and credentials beyond each job's actual needs."""
    errors = []
    expected = "read-all" if name == "scorecard.yml" else {"contents": "read"}
    if workflow.get("permissions") != expected:
        errors.append(f"{name}: workflow token must be read-only")
    for job_name, job in workflow["jobs"].items():
        permissions = job.get("permissions", {})
        if not isinstance(permissions, dict):
            errors.append(f"{name}/{job_name}: use explicit job permissions")
        else:
            writes = {key for key, value in permissions.items() if value == "write"}
            if writes != WRITE_PERMISSIONS.get((name, job_name), set()):
                errors.append(f"{name}/{job_name}: unexpected write permissions")
        for step in job.get("steps", []):
            action = step.get("uses", "")
            if action and not action.startswith("./"):
                pinned = (
                    IMAGE_PIN.fullmatch(action[9:])
                    if action.startswith("docker://")
                    else ACTION_PIN.fullmatch(action)
                )
                if not pinned:
                    errors.append(f"{name}: mutable action {action}")
            if action.startswith("actions/checkout@"):
                if step.get("with", {}).get("persist-credentials") != "false":
                    errors.append(f"{name}: checkout must not persist credentials")
            script = step.get("run", "")
            if re.search(r"\bpip(?:3)?\s+install\b", script):
                if "--require-hashes" not in script:
                    errors.append(f"{name}: pip must verify package hashes")
            for image in re.findall(r"\bbash:4\.3\.48[^\s\\]*", script):
                if not IMAGE_PIN.fullmatch(image):
                    errors.append(f"{name}: mutable Bash compatibility image")
    return errors


def requirement_errors(text: str) -> list[str]:
    """Require complete exact-version and hash entries, including transitives."""
    errors = []
    entries = text.replace("\\\n", " ").splitlines()
    count = 0
    for entry in entries:
        entry = entry.strip()
        if not entry or entry.startswith("#"):
            continue
        count += 1
        if not re.fullmatch(
            r"[A-Za-z0-9_.-]+==[0-9][A-Za-z0-9.]*"
            r"(?:\s+--hash=sha256:[0-9a-f]{64})+", entry
        ):
            errors.append(f"Missing exact version or SHA-256: {entry}")
    if not count:
        errors.append("Empty CI dependency lock")
    return errors


def load_workflow(name: str) -> dict:
    # BaseLoader preserves GitHub's `on` and literal `false` with YAML 1.1.
    return yaml.load(
        (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )


class SupplyChainTests(unittest.TestCase):
    def test_all_workflows_enforce_supply_chain_contract(self) -> None:
        for path in sorted((ROOT / ".github" / "workflows").glob("*.y*ml")):
            with self.subTest(workflow=path.name):
                self.assertEqual(workflow_errors(path.name, load_workflow(path.name)), [])

    def test_mutable_action_and_container_are_rejected(self) -> None:
        workflow = load_workflow("ci.yml")
        workflow["jobs"]["test"]["steps"][0]["uses"] = "actions/checkout@v7"
        errors = workflow_errors("ci.yml", workflow)
        self.assertTrue(any("mutable action" in error for error in errors))
        step = next(step for step in workflow["jobs"]["test"]["steps"]
                    if "bash:4.3.48" in step.get("run", ""))
        step["run"] = "docker run --rm bash:4.3.48 bash --version"
        self.assertTrue(any("mutable Bash" in error
                            for error in workflow_errors("ci.yml", workflow)))
        workflow["jobs"]["test"]["steps"][0]["uses"] = "docker://alpine:latest"
        self.assertTrue(any("mutable action" in error
                            for error in workflow_errors("ci.yml", workflow)))

    def test_local_and_digest_actions_are_accepted(self) -> None:
        workflow = load_workflow("ci.yml")
        steps = workflow["jobs"]["test"]["steps"]
        steps.append({"uses": "./"})
        steps.append({"uses": "docker://alpine@sha256:" + "a" * 64})
        self.assertEqual(workflow_errors("ci.yml", workflow), [])

    def test_broad_tokens_and_persisted_credentials_are_rejected(self) -> None:
        baseline = load_workflow("ci.yml")
        for permissions in ({"contents": "write"}, "write-all"):
            workflow = copy.deepcopy(baseline)
            workflow["permissions"] = permissions
            self.assertTrue(workflow_errors("ci.yml", workflow))
            workflow = copy.deepcopy(baseline)
            workflow["jobs"]["test"]["permissions"] = permissions
            self.assertTrue(workflow_errors("ci.yml", workflow))
        workflow = copy.deepcopy(baseline)
        workflow["jobs"]["test"]["steps"][0]["with"]["persist-credentials"] = "true"
        self.assertTrue(any("persist credentials" in error
                            for error in workflow_errors("ci.yml", workflow)))

    def test_unlocked_pip_install_is_rejected(self) -> None:
        workflow = load_workflow("ci.yml")
        workflow["jobs"]["test"]["steps"].append({"run": "python -m pip install PyYAML"})
        self.assertTrue(any("verify package hashes" in error
                            for error in workflow_errors("ci.yml", workflow)))

    def test_ci_dependencies_have_exact_versions_and_hashes(self) -> None:
        for path in sorted((ROOT / ".github").glob("requirements*.txt")):
            with self.subTest(lockfile=path.name):
                self.assertEqual(requirement_errors(path.read_text(encoding="utf-8")), [])
        for invalid in ("", "PyYAML>=6", "PyYAML==6.0.2", "PyYAML==6 --hash=sha256:bad"):
            with self.subTest(requirement=invalid):
                self.assertTrue(requirement_errors(invalid))

    def test_python_backend_pin_and_manual_publishing_boundary(self) -> None:
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        lock = (ROOT / ".github" / "requirements-packaging.txt").read_text(encoding="utf-8")
        for requirement in project["build-system"]["requires"]:
            self.assertIn(requirement + " --hash=sha256:", lock)
        workflow = load_workflow("pypi-publish.yml")
        self.assertEqual(set(workflow["on"]), {"workflow_dispatch"})
        repository = workflow["on"]["workflow_dispatch"]["inputs"]["repository"]
        self.assertEqual(repository["default"], "testpypi")
        self.assertEqual(set(repository["options"]), {"testpypi", "pypi"})
        build, publish = workflow["jobs"]["build"], workflow["jobs"]["publish"]
        self.assertNotIn("id-token", build.get("permissions", {}))
        self.assertEqual(publish["needs"], "build")
        self.assertIn("shellharbor/watchdog", publish["if"])
        self.assertEqual(publish["environment"]["name"], "${{ inputs.repository }}")
        self.assertFalse(any("run" in step for step in publish["steps"]))
        self.assertFalse(any(step.get("uses", "").startswith("actions/checkout@")
                             for step in publish["steps"]))
        uploader = next(step for step in publish["steps"]
                        if step.get("uses", "").startswith("pypa/gh-action-pypi-publish@"))
        self.assertNotIn("password", uploader.get("with", {}))
        self.assertNotIn("skip-existing", uploader.get("with", {}))

    def test_docker_base_images_are_pinned(self) -> None:
        for path in (ROOT / "Dockerfile", ROOT / "packaging" / "docker" / "Dockerfile",
                     ROOT / ".clusterfuzzlite" / "Dockerfile"):
            stages = set()
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.startswith("FROM "):
                    continue
                tokens = line.split()
                image = tokens[1]
                if image not in stages:
                    self.assertRegex(image, IMAGE_PIN)
                if len(tokens) >= 4 and tokens[2].upper() == "AS":
                    stages.add(tokens[3])

    def test_dependabot_covers_actual_dependency_manifests(self) -> None:
        config = yaml.load((ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8"),
                           Loader=yaml.BaseLoader)
        updates = {(item["package-ecosystem"], item["directory"])
                   for item in config["updates"]}
        self.assertTrue({("github-actions", "/"), ("pip", "/"), ("pip", "/.github"),
                         ("docker", "/"), ("docker", "/packaging/docker"),
                         ("docker", "/.clusterfuzzlite")} <= updates)

    def run_yq_install(self, valid_hash: bool, curl_exit: int = 0) -> None:
        step = next(step for step in load_workflow("ci.yml")["jobs"]["test"]["steps"]
                    if step.get("name") == "Install verified yq v4")
        with tempfile.TemporaryDirectory(prefix="watchdog-supply-chain-") as directory:
            root = Path(directory)
            binaries = root / "bin"
            binaries.mkdir()
            payload = root / "payload"
            payload.write_bytes(b"synthetic-yq-fixture\n")
            marker = root / "installed"
            shims = {
                "curl": '#!/usr/bin/env bash\nset -eu\n'
                        '[[ "$CURL_EXIT" == 0 ]] || exit "$CURL_EXIT"\n'
                        'cp -- "$TEST_PAYLOAD" "${@: -1}"\n',
                "sudo": '#!/usr/bin/env bash\nset -eu\n'
                        '[[ "$1" == install ]]\nprintf "%s\\n" "$@" > "$TEST_INSTALLED"\n',
            }
            for name, script in shims.items():
                target = binaries / name
                target.write_text(script, encoding="utf-8")
                target.chmod(0o755)
            env = dict(os.environ, **step["env"])
            env.update({
                "PATH": str(binaries) + os.pathsep + env["PATH"],
                "RUNNER_TEMP": str(root),
                "TEST_PAYLOAD": str(payload),
                "TEST_INSTALLED": str(marker),
                "CURL_EXIT": str(curl_exit),
                "YQ_SHA256": hashlib.sha256(payload.read_bytes()).hexdigest()
                if valid_hash else "0" * 64,
            })
            result = subprocess.run(["bash", "-c", step["run"]], env=env,
                                    capture_output=True, text=True, timeout=20)
            if valid_hash and not curl_exit:
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(marker.exists())
            else:
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(marker.exists(), "Unverified executable was installed")
            self.assertEqual(list(root.glob("watchdog-yq.*")), [], "Download was not cleaned up")

    def test_verified_download_can_be_installed(self) -> None:
        self.run_yq_install(valid_hash=True)

    def test_checksum_mismatch_prevents_installation(self) -> None:
        self.run_yq_install(valid_hash=False)

    def test_failed_download_prevents_installation(self) -> None:
        self.run_yq_install(valid_hash=True, curl_exit=22)

    def test_publication_metadata_preserves_flags_without_exposing_secrets(self) -> None:
        step = next(step for step in load_workflow("docker-publish.yml")["jobs"]["prepare"]["steps"]
                    if step.get("id") == "version")
        cases = (("false", "", "", "true", "false"),
                 ("true", "", "", "false", "false"),
                 ("false", "synthetic-user", "synthetic-token", "true", "true"),
                 ("false", "synthetic-user", "", "true", "false"),
                 ("false", "", "synthetic-token", "true", "false"))
        for prerelease, username, token, stable, enabled in cases:
            with self.subTest(prerelease=prerelease, credentials=enabled):
                with tempfile.TemporaryDirectory(prefix="watchdog-metadata-") as directory:
                    root = Path(directory)
                    (root / "VERSION").write_text("1.7.8\n", encoding="utf-8")
                    git = root / "git"
                    git.write_text('#!/usr/bin/env bash\nprintf "%s\\n" "' + "a" * 40 + '"\n',
                                   encoding="utf-8")
                    git.chmod(0o755)
                    output = root / "output"
                    env = dict(os.environ, RELEASE_TAG="v1.7.8", RELEASE_PRERELEASE=prerelease,
                               DOCKERHUB_USERNAME=username, DOCKERHUB_TOKEN=token,
                               GITHUB_OUTPUT=str(output))
                    env["PATH"] = str(root) + os.pathsep + env["PATH"]
                    result = subprocess.run(["bash", "-c", step["run"]], cwd=root, env=env,
                                            capture_output=True, text=True, timeout=20)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    values = dict(line.split("=", 1) for line in output.read_text().splitlines())
                    self.assertEqual(values, {"version": "1.7.8", "major": "1", "minor": "7",
                                              "revision": "a" * 40, "stable": stable,
                                              "dockerhub_enabled": enabled})
                    self.assertNotIn("synthetic-token", result.stdout + result.stderr + output.read_text())
                    env["RELEASE_TAG"] = "v0.0.0"
                    result = subprocess.run(["bash", "-c", step["run"]], cwd=root, env=env,
                                            capture_output=True, text=True, timeout=20)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(output.read_text().splitlines(),
                                     [f"{key}={value}" for key, value in values.items()])


if __name__ == "__main__":
    unittest.main(verbosity=2)
