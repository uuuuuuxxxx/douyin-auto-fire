from __future__ import annotations

import copy
import json
import os
from pathlib import Path


def apply_friend_list(config: dict, friends: list[str]) -> dict:
    if not isinstance(config, dict):
        raise ValueError("任务配置必须是对象")
    if not isinstance(friends, list) or not friends or any(not isinstance(name, str) or not name.strip() for name in friends):
        raise ValueError("好友名单必须是非空字符串数组")
    names = list(dict.fromkeys(friends))
    result = copy.deepcopy(config)
    if "targets" in result:
        targets = result["targets"]
        if not isinstance(targets, list) or not targets or any(not isinstance(target, dict) for target in targets):
            raise ValueError("targets 必须是非空对象数组")
        existing = {target.get("name"): target for target in targets}
        if len(targets) != 1 and any(name not in existing for name in names):
            raise ValueError("多好友自定义消息配置缺少新好友的消息模板，请更新 DOUYIN_CONFIG")
        result["targets"] = [dict(copy.deepcopy(existing.get(name, targets[0])), name=name) for name in names]
    else:
        result["friends"] = names
    return result


def main() -> None:
    config = json.loads(os.environ["DOUYIN_CONFIG"])
    raw_friends = os.environ.get("DOUYIN_FRIENDS", "")
    if raw_friends:
        config = apply_friend_list(config, json.loads(raw_friends))
    path = Path("config.json")
    path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
    path.chmod(0o600)
    print("任务配置已保存；好友名单已更新。" if raw_friends else "任务配置已保存。")


if __name__ == "__main__":
    main()
