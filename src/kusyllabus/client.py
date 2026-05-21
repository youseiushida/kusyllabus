"""Sync and async HTTP clients for the Kyoto University open syllabus.

The two client classes share the same surface area; pick whichever matches
your application:

* :class:`KuSyllabusClient` — blocking, uses :class:`httpx.Client`. Drop-in
  for scripts, REPLs, and synchronous CLIs.
* :class:`AsyncKuSyllabusClient` — uses :class:`httpx.AsyncClient` and offers
  ``fetch_many_syllabi`` for high-concurrency bulk retrieval (driven by
  aiometer).
"""

from __future__ import annotations

import functools
from collections.abc import AsyncIterator, Iterable, Iterator, Sequence
from typing import Self

import aiometer
import httpx
from tenacity import (
    AsyncRetrying,
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from kusyllabus.conditions import SearchCondition
from kusyllabus.encoding import build_query, decode_response
from kusyllabus.exceptions import KuSyllabusHTTPError
from kusyllabus.models import (
    AllTreeNode,
    SearchResult,
    Syllabus,
    SyllabusTitleOption,
)
from kusyllabus.parsers import (
    parse_all_tree,
    parse_search_result,
    parse_syllabus,
    parse_syllabus_titles,
)

BASE_URL = "https://www.k.kyoto-u.ac.jp/external/open_syllabus/"
DEFAULT_USER_AGENT = "kusyllabus/0.1 (+https://github.com/nezowarui/kusyllabus)"
DEFAULT_TIMEOUT = 30.0
DEFAULT_RETRY_ATTEMPTS = 3
"""Retry attempts for 5xx / transient network errors. 1 means no retry."""

_RETRYABLE_HTTP_STATUSES = frozenset({500, 502, 503, 504})


class _RetryableError(Exception):
    """Sentinel used inside the tenacity retry loop."""


def _retry_kwargs(attempts: int) -> dict:
    return {
        "stop": stop_after_attempt(attempts),
        "wait": wait_exponential_jitter(initial=0.5, max=8.0),
        "retry": retry_if_exception_type((_RetryableError, httpx.TransportError)),
        "reraise": True,
    }


# ---------------------------------------------------------------------------
# Common helpers (URL building, error mapping)
# ---------------------------------------------------------------------------


def _build_search_url(
    condition: SearchCondition, *, page: int | None, display_lang: str | None
) -> str:
    params = condition.to_query_params(page=page)
    if display_lang:
        params.append(("display_lang", display_lang))
    return f"{BASE_URL}search?{build_query(params)}"


def _build_top_url(display_lang: str | None) -> str:
    if display_lang:
        return f"{BASE_URL}top?display_lang={display_lang}"
    return f"{BASE_URL}top"


def _build_all_url(display_lang: str | None) -> str:
    if display_lang:
        return f"{BASE_URL}all?display_lang={display_lang}"
    return f"{BASE_URL}all"


def _build_titles_url(department_no: int | str) -> str:
    return f"{BASE_URL}open_syllabus_titles?departmentNo={department_no}"


def _build_syllabus_url(
    lecture_no: int,
    *,
    department_no: int | None,
    display_lang: str | None,
) -> str:
    if department_no is None:
        url = f"{BASE_URL}la_syllabus?lectureNo={lecture_no}"
    else:
        url = f"{BASE_URL}department_syllabus?lectureNo={lecture_no}&departmentNo={department_no}"
    if display_lang:
        url += f"&display_lang={display_lang}"
    return url


def _check_response(response: httpx.Response) -> str | None:
    """Convert a raw response into decoded text, or signal None / raise.

    * 200 → decoded body (CP932 → str).
    * 404 → ``None`` (caller decides how to surface the miss).
    * 500/502/503/504 → raises :class:`_RetryableError` so the tenacity
      decorator re-runs.
    * Anything else → :class:`KuSyllabusHTTPError`.
    """
    if response.status_code == 200:
        return decode_response(response.content)
    if response.status_code == 404:
        return None
    if response.status_code in _RETRYABLE_HTTP_STATUSES:
        raise _RetryableError(f"HTTP {response.status_code} from {response.url}")
    raise KuSyllabusHTTPError(
        response.status_code, str(response.url), f"unexpected status {response.status_code}"
    )


# ---------------------------------------------------------------------------
# Sync client
# ---------------------------------------------------------------------------


class KuSyllabusClient:
    """Synchronous client wrapping :class:`httpx.Client`.

    Use as a context manager to ensure the underlying client is closed:

    >>> with KuSyllabusClient() as ku:                # doctest: +SKIP
    ...     result = ku.search(SearchCondition(keyword="thermodynamics"))
    """

    def __init__(
        self,
        *,
        base_url: str = BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        user_agent: str = DEFAULT_USER_AGENT,
        retry_attempts: int = DEFAULT_RETRY_ATTEMPTS,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url
        self.retry_attempts = retry_attempts
        self._owns_http_client = http_client is None
        self._http = http_client or httpx.Client(
            timeout=timeout,
            headers={
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
                "Accept-Language": "ja,en;q=0.9",
                "Accept-Encoding": "gzip, deflate",
            },
            follow_redirects=True,
        )

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_http_client:
            self._http.close()

    # ----- public methods --------------------------------------------------

    def search(
        self,
        condition: SearchCondition | None = None,
        *,
        page: int = 1,
        display_lang: str | None = None,
    ) -> SearchResult:
        """Run a search and parse the result page.

        ``page`` must be ``>= 1`` (the server returns HTTP 500 for ``page <= 0``).
        """
        cond = condition or SearchCondition()
        url = _build_search_url(cond, page=page, display_lang=display_lang)
        html = self._get(url)
        if html is None:
            return SearchResult(total=0, page=page, rows=[])
        return parse_search_result(html, page=page)

    def iter_search_pages(
        self,
        condition: SearchCondition | None = None,
        *,
        display_lang: str | None = None,
        start_page: int = 1,
    ) -> Iterator[SearchResult]:
        """Iterate over result pages until the server returns no more rows.

        The server reports ``total`` but only the LIBERAL_ARTS department
        actually populates result rows. For other departments this iterator
        yields exactly one empty page (since rows are empty from page 1).
        """
        page = start_page
        while True:
            result = self.search(condition, page=page, display_lang=display_lang)
            yield result
            if not result.rows or not result.has_next_page:
                return
            page += 1

    def get_syllabus(
        self,
        lecture_no: int,
        *,
        department_no: int | None = None,
        display_lang: str | None = None,
    ) -> Syllabus | None:
        """Fetch a single syllabus.

        ``department_no`` selects between the two backend endpoints:

        * ``None`` → ``/la_syllabus?lectureNo=N`` (Liberal-arts / general
          education syllabi).
        * any ``int`` → ``/department_syllabus?lectureNo=N&departmentNo=D``
          (per-faculty syllabi). The matching ``department_no`` for a
          ``lectureNo`` is available from :class:`AllTreeNode` leaves.

        Returns ``None`` when the lecture does not exist (server 404).
        """
        url = _build_syllabus_url(
            lecture_no, department_no=department_no, display_lang=display_lang
        )
        html = self._get(url)
        if html is None:
            return None
        return parse_syllabus(
            html,
            lecture_no=lecture_no,
            display_lang=display_lang or "ja",
        )

    def get_all_tree(self, *, display_lang: str | None = None) -> list[AllTreeNode]:
        """Fetch and parse ``/all`` — every department's full course list."""
        url = _build_all_url(display_lang)
        html = self._get(url)
        if html is None:
            return []
        return parse_all_tree(html)

    def get_syllabus_titles(self, department_no: int) -> list[SyllabusTitleOption]:
        """Fetch the academic-area dropdown for a given department."""
        html = self._get(_build_titles_url(department_no))
        if html is None:
            return []
        return parse_syllabus_titles(html)

    def get_top_html(self, *, display_lang: str | None = None) -> str:
        """Fetch the top page (raw HTML). Useful for refreshing master data."""
        html = self._get(_build_top_url(display_lang))
        return html or ""

    # ----- internal --------------------------------------------------------

    def _get(self, url: str) -> str | None:
        for attempt in Retrying(**_retry_kwargs(self.retry_attempts)):
            with attempt:
                response = self._http.get(url)
                return _check_response(response)
        return None  # unreachable; tenacity reraise=True


# ---------------------------------------------------------------------------
# Async client
# ---------------------------------------------------------------------------


class AsyncKuSyllabusClient:
    """Asynchronous client wrapping :class:`httpx.AsyncClient`.

    Use as an async context manager:

    >>> async with AsyncKuSyllabusClient() as ku:          # doctest: +SKIP
    ...     syllabi = await ku.fetch_many_syllabi([61323, 61325], max_at_once=8)
    """

    def __init__(
        self,
        *,
        base_url: str = BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        user_agent: str = DEFAULT_USER_AGENT,
        retry_attempts: int = DEFAULT_RETRY_ATTEMPTS,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url
        self.retry_attempts = retry_attempts
        self._owns_http_client = http_client is None
        self._http = http_client or httpx.AsyncClient(
            timeout=timeout,
            headers={
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
                "Accept-Language": "ja,en;q=0.9",
                "Accept-Encoding": "gzip, deflate",
            },
            follow_redirects=True,
        )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_http_client:
            await self._http.aclose()

    # ----- public methods --------------------------------------------------

    async def search(
        self,
        condition: SearchCondition | None = None,
        *,
        page: int = 1,
        display_lang: str | None = None,
    ) -> SearchResult:
        cond = condition or SearchCondition()
        url = _build_search_url(cond, page=page, display_lang=display_lang)
        html = await self._get(url)
        if html is None:
            return SearchResult(total=0, page=page, rows=[])
        return parse_search_result(html, page=page)

    async def iter_search_pages(
        self,
        condition: SearchCondition | None = None,
        *,
        display_lang: str | None = None,
        start_page: int = 1,
    ) -> AsyncIterator[SearchResult]:
        page = start_page
        while True:
            result = await self.search(condition, page=page, display_lang=display_lang)
            yield result
            if not result.rows or not result.has_next_page:
                return
            page += 1

    async def get_syllabus(
        self,
        lecture_no: int,
        *,
        department_no: int | None = None,
        display_lang: str | None = None,
    ) -> Syllabus | None:
        url = _build_syllabus_url(
            lecture_no, department_no=department_no, display_lang=display_lang
        )
        html = await self._get(url)
        if html is None:
            return None
        return parse_syllabus(
            html,
            lecture_no=lecture_no,
            display_lang=display_lang or "ja",
        )

    async def fetch_many_syllabi(
        self,
        targets: Sequence[int | tuple[int, int | None]],
        *,
        max_at_once: int = 8,
        max_per_second: float | None = 5.0,
        display_lang: str | None = None,
    ) -> list[Syllabus | None]:
        """Fetch many syllabi concurrently with bounded concurrency.

        Each ``target`` is either an ``int`` (``lectureNo`` for the open
        ``la_syllabus`` endpoint) or a ``(lectureNo, department_no)`` tuple.
        Results are returned in the same order as ``targets``; missing pages
        appear as ``None``.

        Concurrency and rate limits come from aiometer to avoid hammering the
        server during the registration-window peak. Override by passing your
        own ``http_client`` with appropriate limits if needed.
        """
        normalized: list[tuple[int, int | None]] = []
        for t in targets:
            if isinstance(t, tuple):
                normalized.append((t[0], t[1]))
            else:
                normalized.append((int(t), None))

        async def _one(lecture_no: int, department_no: int | None) -> Syllabus | None:
            return await self.get_syllabus(
                lecture_no,
                department_no=department_no,
                display_lang=display_lang,
            )

        return await aiometer.run_all(
            [functools.partial(_one, lecture_no, dept_no) for lecture_no, dept_no in normalized],
            max_at_once=max_at_once,
            max_per_second=max_per_second,
        )

    async def get_all_tree(self, *, display_lang: str | None = None) -> list[AllTreeNode]:
        url = _build_all_url(display_lang)
        html = await self._get(url)
        if html is None:
            return []
        return parse_all_tree(html)

    async def get_syllabus_titles(self, department_no: int) -> list[SyllabusTitleOption]:
        html = await self._get(_build_titles_url(department_no))
        if html is None:
            return []
        return parse_syllabus_titles(html)

    async def get_top_html(self, *, display_lang: str | None = None) -> str:
        html = await self._get(_build_top_url(display_lang))
        return html or ""

    # ----- internal --------------------------------------------------------

    async def _get(self, url: str) -> str | None:
        async for attempt in AsyncRetrying(**_retry_kwargs(self.retry_attempts)):
            with attempt:
                response = await self._http.get(url)
                return _check_response(response)
        return None  # unreachable; tenacity reraise=True


# ---------------------------------------------------------------------------
# Convenience: spin up a temporary client and run one call.
# ---------------------------------------------------------------------------


def _flatten_leaves(tree: Iterable[AllTreeNode]) -> Iterator[AllTreeNode]:
    """Yield every leaf node (where ``lecture_no`` is set) under an ``/all`` tree."""
    for node in tree:
        if node.lecture_no is not None:
            yield node
        if node.children:
            yield from _flatten_leaves(node.children)


def flatten_all_leaves(tree: Iterable[AllTreeNode]) -> list[AllTreeNode]:
    """Public wrapper around :func:`_flatten_leaves` returning a list."""
    return list(_flatten_leaves(tree))


__all__ = [
    "BASE_URL",
    "AsyncKuSyllabusClient",
    "KuSyllabusClient",
    "flatten_all_leaves",
]
