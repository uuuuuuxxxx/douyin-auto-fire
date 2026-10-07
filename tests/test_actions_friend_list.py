import copy

import pytest

from scripts.prepare_actions_config import apply_friend_list


def test_legacy_list_keeps_verified_message_and_settings():
    original = {"friends": ["原好友"], "messages": [{"type": "douyin_sticker", "value": "续火花"}], "stickers": {"续火花": {"name": "续火花"}}, "send_interval_seconds": {"min": 3, "max": 8}}
    before = copy.deepcopy(original)
    names = ["内向小学生", "ᖰ•\u00a0֊\u00a0•ᖳ", "内向小学生"]
    result = apply_friend_list(original, names)
    assert result["friends"] == names[:2]
    assert {key: value for key, value in result.items() if key != "friends"} == {key: value for key, value in original.items() if key != "friends"}
    assert original == before


def test_expands_single_target_without_changing_message_template():
    message = {"type": "douyin_sticker", "value": "续火花"}
    original = {"targets": [{"name": "原好友", "messages": [message]}], "stickers": {"续火花": {"name": "续火花"}}}
    result = apply_friend_list(original, ["甲", "乙"])
    assert result["targets"] == [{"name": "甲", "messages": [message]}, {"name": "乙", "messages": [message]}]
    result["targets"][0]["messages"].append({"type": "text", "value": "test"})
    assert len(result["targets"][1]["messages"]) == 1
    assert len(original["targets"][0]["messages"]) == 1


def test_retains_individual_messages_for_existing_targets():
    original = {"targets": [{"name": "甲", "messages": [{"type": "text", "value": "a"}]}, {"name": "乙", "messages": [{"type": "text", "value": "b"}]}]}
    assert apply_friend_list(original, ["乙", "甲"])["targets"] == original["targets"][::-1]


def test_refuses_to_guess_template_for_new_friend_in_multi_target_config():
    with pytest.raises(ValueError):
        apply_friend_list({"targets": [{"name": "甲"}, {"name": "乙"}]}, ["丙"])


@pytest.mark.parametrize("names", [[], [""], [" "], [None], "甲"])
def test_rejects_invalid_list(names):
    with pytest.raises(ValueError):
        apply_friend_list({"friends": ["原好友"]}, names)
