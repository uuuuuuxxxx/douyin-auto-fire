import json
import base64
import gzip
import os
import subprocess
import sys
import textwrap
import random
from pathlib import Path

import pytest


WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/send.yml"


def run_restore(tmp_path, raw, multi_account=False, part2=""):
    step = WORKFLOW.read_text(encoding="utf-8").split(
        "      - name: Restore single-account browser login state\n", 1
    )[1].split("      - name: Run\n", 1)[0]
    script = textwrap.dedent(step.split("python - <<'PY'\n", 1)[1].split("\n          PY", 1)[0])
    if multi_account:
        (tmp_path / "config").mkdir()
        (tmp_path / "config/accounts.json").write_text('{"accounts": []}')
    env = dict(os.environ, SINGLE_ACCOUNT_STORAGE_STATE=raw, SINGLE_ACCOUNT_STORAGE_STATE_PART2=part2, PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, "-c", script], cwd=tmp_path, env=env, capture_output=True, text=True, encoding="utf-8")


def test_absent_state_preserves_cookie_mode(tmp_path):
    result = run_restore(tmp_path, "")
    assert result.returncode == 0
    assert not (tmp_path / "storage-state.json").exists()


def test_restores_browser_state_without_logging_credentials(tmp_path):
    state = {"cookies": [{"name": "sessionid", "value": "PRIVATE_TEST_VALUE"}], "origins": [{"origin": "https://www.douyin.com", "localStorage": [{"name": "test", "value": "PRIVATE_TEST_VALUE"}]}]}
    result = run_restore(tmp_path, json.dumps(state))
    assert result.returncode == 0
    assert json.loads((tmp_path / "storage-state.json").read_text(encoding="utf-8")) == state
    assert "PRIVATE_TEST_VALUE" not in result.stdout + result.stderr


@pytest.mark.parametrize("raw", ["PRIVATE_TEST_VALUE", "[]", '{"cookies":[],"origins":[]}', '{"cookies":[{}]}'])
def test_rejects_invalid_or_empty_state_without_exposing_it(tmp_path, raw):
    result = run_restore(tmp_path, raw)
    assert result.returncode != 0
    assert not (tmp_path / "storage-state.json").exists()
    assert "PRIVATE_TEST_VALUE" not in result.stdout + result.stderr


def test_rejects_single_state_for_multiple_accounts(tmp_path):
    result = run_restore(tmp_path, '{"cookies":[{"name":"sessionid","value":"PRIVATE_TEST_VALUE"}],"origins":[]}', multi_account=True)
    assert result.returncode != 0
    assert not (tmp_path / "storage-state.json").exists()
    assert "PRIVATE_TEST_VALUE" not in result.stdout + result.stderr


def test_restores_compressed_state_split_across_secrets(tmp_path):
    state = {"cookies": [{"name": "sessionid", "value": "PRIVATE_TEST_VALUE"}], "origins": []}
    encoded = base64.b64encode(gzip.compress(json.dumps(state).encode())).decode()
    middle = len(encoded) // 2
    result = run_restore(tmp_path, f"gzip:{len(encoded)}:" + encoded[:middle], part2=encoded[middle:])
    assert result.returncode == 0
    assert json.loads((tmp_path / "storage-state.json").read_text(encoding="utf-8")) == state
    assert "PRIVATE_TEST_VALUE" not in result.stdout + result.stderr


@pytest.mark.parametrize("raw", ["gzip:PRIVATE_TEST_VALUE", "gzip:" + base64.b64encode(b"not gzip").decode()])
def test_rejects_invalid_compressed_state_without_exposing_it(tmp_path, raw):
    result = run_restore(tmp_path, raw)
    assert result.returncode != 0
    assert not (tmp_path / "storage-state.json").exists()
    assert "PRIVATE_TEST_VALUE" not in result.stdout + result.stderr


def test_upload_and_restore_state_larger_than_one_secret(tmp_path, monkeypatch):
    from scripts.upload_storage_state import upload

    state = {"cookies": [{"name": "sessionid", "value": "PRIVATE_TEST_VALUE"}], "origins": [{"origin": "https://www.douyin.com", "localStorage": [{"name": "test", "value": random.Random(42).randbytes(45000).hex()}]}]}
    path = tmp_path / "input.json"
    path.write_text(json.dumps(state), encoding="utf-8")
    uploaded = {}

    def capture(args, *, input, check):
        assert len(input) <= 48_000
        uploaded[args[3]] = input.decode()

    with monkeypatch.context() as patch:
        patch.setattr("scripts.upload_storage_state.subprocess.run", capture)
        upload(path, "example/example")
    result = run_restore(tmp_path, uploaded["DOUYIN_STORAGE_STATE"], part2=uploaded["DOUYIN_STORAGE_STATE_PART2"])
    assert result.returncode == 0
    assert json.loads((tmp_path / "storage-state.json").read_text(encoding="utf-8")) == state


def test_compressed_single_secret_ignores_old_continuation(tmp_path):
    state = {"cookies": [{"name": "sessionid", "value": "PRIVATE_TEST_VALUE"}], "origins": []}
    encoded = base64.b64encode(gzip.compress(json.dumps(state).encode())).decode()
    result = run_restore(tmp_path, f"gzip:{len(encoded)}:{encoded}", part2="obsolete continuation")
    assert result.returncode == 0
    assert json.loads((tmp_path / "storage-state.json").read_text(encoding="utf-8")) == state
