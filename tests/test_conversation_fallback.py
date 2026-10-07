from unittest.mock import AsyncMock, MagicMock, call

import pytest

from app.douyin import DouyinChat, PageOperationError


def setup_page(monkeypatch):
    page = MagicMock()
    page.wait_for_timeout = AsyncMock()
    search = MagicMock()
    search.click = AsyncMock()
    search.fill = AsyncMock()
    cancel = page.get_by_text.return_value
    cancel.count = AsyncMock(return_value=1)
    cancel.first.is_visible = AsyncMock(return_value=True)
    cancel.first.click = AsyncMock()
    monkeypatch.setattr('app.douyin.first_visible', AsyncMock(return_value=search))
    return page, search, cancel


@pytest.mark.asyncio
async def test_missing_search_result_opens_exact_conversation_and_confirms(monkeypatch):
    page, search, cancel = setup_page(monkeypatch)
    chat = DouyinChat(page)
    name = '\u2603\u00a0test\u00a0\u2603'
    row = MagicMock()
    row.click = AsyncMock()
    chat._search_result = AsyncMock(side_effect=[None, row])
    chat._confirm_opened = AsyncMock()

    await chat._open_target_once(name)

    assert chat._search_result.await_args_list == [call(name), call(name)]
    assert search.fill.await_args_list == [call(''), call(name), call('')]
    cancel.first.click.assert_awaited_once()
    row.click.assert_awaited_once_with(force=True)
    chat._confirm_opened.assert_awaited_once_with(name)


@pytest.mark.asyncio
async def test_missing_exact_conversation_stops_before_clicking(monkeypatch):
    page, _, _ = setup_page(monkeypatch)
    chat = DouyinChat(page)
    chat._search_result = AsyncMock(return_value=None)
    chat._confirm_opened = AsyncMock()

    with pytest.raises(PageOperationError, match='搜索不到目标好友'):
        await chat._open_target_once('Missing exact recipient')

    chat._confirm_opened.assert_not_awaited()
