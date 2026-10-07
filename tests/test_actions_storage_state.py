import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/send.yml"


def run_restore(tmp_path, raw, multi_account=False):
    step = WORKFLOW.read_text(encoding="utf-8").split(
        "      - name: Restore single-account browser login state\n", 1
    )[1].split("      - name: Run\n", 1)[0]
    script = textwrap.dedent(step.split("python - <<'PY'\n", 1)[1].split("\n          PY", 1)[0])
    if multi_account:
        (tmp_path / "config").mkdir()
        (tmp_path / "config/accounts.json").write_text('{"accounts": []}')
    env = dict(os.environ, SINGLE_ACCOUNT_STORAGE_STATE=raw, PYTHONIOENCODING="utf-8")
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
