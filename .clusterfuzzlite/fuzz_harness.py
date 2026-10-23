"""Black-box invariants for real Bash validation and output serialization."""

import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
PACKAGED = hasattr(sys, "_MEIPASS")
RESOURCE = Path(sys._MEIPASS) / "watchdog" if PACKAGED else ROOT
BIN = Path(sys._MEIPASS) / "bin" if PACKAGED else None
BRIDGE = RESOURCE / "bridge.sh" if PACKAGED else ROOT / ".clusterfuzzlite" / "bridge.sh"
MAX_INPUT = 4096


def environment(directory: Path) -> dict:
    result = {"PATH": str(BIN) if BIN else "/usr/local/bin" + os.pathsep + os.defpath, "LC_ALL": "C.UTF-8",
              "TMPDIR": str(directory)}
    # PyInstaller bundles shared libraries; do not inherit host credentials or
    # preload the fuzz engine into the external, unsanitized Bash subprocess.
    if PACKAGED:
        result["LD_LIBRARY_PATH"] = str(sys._MEIPASS)
    return result


def run(argv: list, env: dict, directory: Path) -> subprocess.CompletedProcess:
    with subprocess.Popen(argv, cwd=directory, env=env, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, start_new_session=True) as process:
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
            raise AssertionError("Watchdog input exceeded the five-second process deadline") from None
    return subprocess.CompletedProcess(argv, process.returncode, stdout, stderr)


def check_serializers(text: str) -> None:
    # Bash strings cannot represent NUL. Every other Unicode/control character
    # is passed as one literal argv item; input is never interpreted as code.
    text = text.replace("\x00", "")
    with tempfile.TemporaryDirectory(prefix="watchdog-fuzz-strings-") as directory:
        root = Path(directory)
        env = environment(root)
        for operation in ("json", "html", "prometheus"):
            result = run(["bash", str(BRIDGE), str(RESOURCE), operation, text], env, root)
            if result.returncode:
                raise AssertionError(f"{operation} serializer failed: {result.stderr[:1000]!r}")
            output = result.stdout.decode("utf-8")
            if operation == "json":
                assert json.loads('"' + output + '"') == text, "JSON did not preserve the input"
            elif operation == "html":
                expected = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
                assert output == expected, "Unsafe HTML text/double-quoted attribute escaping"
            else:
                expected = text.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')
                assert output == expected, "Invalid Prometheus label escaping"


def check_configuration(data: bytes, structured: bool = False) -> None:
    with tempfile.TemporaryDirectory(prefix="watchdog-fuzz-config-") as directory:
        root = Path(directory)
        guard = root / "guard"
        guard.mkdir()
        marker = root / "unexpected-execution"
        probe = '#!/bin/sh\nprintf unexpected > "$WATCHDOG_FUZZ_MARKER"\nexit 99\n'
        for tool in ("probe", "curl", "dig", "ping", "openssl", "clamscan", "journalctl", "ss"):
            path = guard / tool
            path.write_text(probe, encoding="utf-8")
            path.chmod(0o755)
        if structured:
            text = data.decode("utf-8", errors="replace").replace("\x00", "")
            config = {
                "settings": {"state_directory": str(root / "state"),
                             "log_file": str(root / "watchdog.log"), "lock_file": str(root / "lock")},
                "services": [{"name": "fuzz-service", "check": {
                    "type": "command", "commands": [{"command": [str(guard / "probe"), text]}]},
                    "hooks": {"on_failure": [{"command": [str(guard / "probe")]}]}}],
            }
            data = json.dumps(config, ensure_ascii=True).encode()
        path = root / "config.yaml"
        path.write_bytes(data)
        before = set(root.rglob("*"))
        env = environment(root)
        env["PATH"] = str(guard) + os.pathsep + env["PATH"]
        env["WATCHDOG_FUZZ_MARKER"] = str(marker)
        result = run(["bash", str(RESOURCE / "service-watchdog.sh"), "validate", "-c", str(path)], env, root)
        assert result.returncode in (0, 2), f"Invalid validation exit: {result.returncode}: {result.stderr[:1000]!r}"
        if structured:
            assert result.returncode == 0, f"Valid command fixture was rejected: {result.stderr[:1000]!r}"
        assert not marker.exists(), "validate executed a check, notification, or hook"
        assert set(root.rglob("*")) == before, "validate created runtime files"


def check_input(data: bytes) -> None:
    if not data or len(data) > MAX_INPUT:
        return
    mode = data[0] % 3
    if mode == 0:
        check_serializers(data[1:].decode("utf-8", errors="replace"))
    else:
        check_configuration(data[1:], structured=mode == 2)
