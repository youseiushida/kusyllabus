"""Async client coverage — single fetch, bulk fetch_many_syllabi."""

from __future__ import annotations

import httpx
import pytest

from kusyllabus import AsyncKuSyllabusClient


@pytest.mark.asyncio
async def test_async_get_syllabus(mock_transport: httpx.MockTransport) -> None:
    async with AsyncKuSyllabusClient(http_client=httpx.AsyncClient(transport=mock_transport)) as ku:
        syl = await ku.get_syllabus(63736)
    assert syl is not None
    assert syl.lecture_no == 63736


@pytest.mark.asyncio
async def test_async_fetch_many_returns_in_order(mock_transport: httpx.MockTransport) -> None:
    """Order of returned results must match the order of requested targets."""
    async with AsyncKuSyllabusClient(http_client=httpx.AsyncClient(transport=mock_transport)) as ku:
        results = await ku.fetch_many_syllabi(
            [63736, (26510, 1), 62409, 999_999],
            max_at_once=4,
            max_per_second=None,  # no throttle for the test
        )
    assert len(results) == 4
    assert results[0] is not None and results[0].lecture_no == 63736
    assert results[1] is not None and results[1].title.startswith("国語学")
    assert results[2] is not None and results[2].title == "社会学Ｉ"
    assert results[3] is None  # 404 surfaces as None


@pytest.mark.asyncio
async def test_async_get_all_tree(mock_transport: httpx.MockTransport) -> None:
    async with AsyncKuSyllabusClient(http_client=httpx.AsyncClient(transport=mock_transport)) as ku:
        tree = await ku.get_all_tree()
    assert len(tree) == 32
