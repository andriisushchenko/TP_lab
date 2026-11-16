import os
import subprocess
import sys
from pathlib import Path

RUNNER = Path(__file__).parent.parent / "conformance" / "run.py"


def _conformance(*command):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run(
        [sys.executable, str(RUNNER), *command], capture_output=True, text=True, encoding="utf-8", env=env,
    )


def test_our_implementation_passes():
    result = _conformance(sys.executable, "-m", "sipl")
    assert result.returncode == 0, result.stdout
    assert "FAIL" not in result.stdout


def test_wrong_implementation_fails():
    result = _conformance(sys.executable, "-c", "print('{}')")
    assert result.returncode == 1
    assert "PASS" not in result.stdout


def test_missing_command():
    assert _conformance("no_such_sipl").returncode == 2
