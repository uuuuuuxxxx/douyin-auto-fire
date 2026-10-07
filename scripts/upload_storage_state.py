from __future__ import annotations

import argparse
import base64
import gzip
import json
import subprocess
from pathlib import Path


def upload(path: Path, repository: str) -> None:
    state = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(state, dict) or not state.get("cookies") or not isinstance(state.get("origins"), list):
        raise SystemExit("登录状态不完整，请重新扫码登录")
    raw = json.dumps(state, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    if len(raw) > 16 * 1024 * 1024:
        raise SystemExit("登录状态超过 16 MB，尚未上传")
    # Leave room for encrypted/base64 payload overhead at the GitHub API.
    limit = 34_000
    if len(raw) <= limit:
        first, second = raw, b""
    else:
        encoded = base64.b64encode(gzip.compress(raw))
        packed = b"gzip:" + str(len(encoded)).encode("ascii") + b":" + encoded
        if len(packed) > 2 * limit:
            raise SystemExit("压缩状态仍超过两个 GitHub Secret 的容量，尚未上传")
        first, second = packed[:limit], packed[limit:]
    # Write the continuation first so a new primary secret is never published
    # before its continuation exists. Plain JSON ignores any old continuation.
    if second:
        subprocess.run(["gh", "secret", "set", "DOUYIN_STORAGE_STATE_PART2", "--repo", repository], input=second, check=True)
    subprocess.run(["gh", "secret", "set", "DOUYIN_STORAGE_STATE", "--repo", repository], input=first, check=True)
    print("浏览器登录状态已上传到 GitHub Secrets；未发送消息。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="安全上传浏览器登录状态，自动适配 GitHub Secret 大小限制")
    parser.add_argument("--repo", required=True, help="GitHub 仓库，例如 owner/douyin-auto-fire")
    parser.add_argument("--state", type=Path, default=Path("storage-state.json"))
    args = parser.parse_args()
    upload(args.state, args.repo)
