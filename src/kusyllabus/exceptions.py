"""Exception hierarchy for kusyllabus."""

from __future__ import annotations


class KuSyllabusError(Exception):
    """Base class for all kusyllabus errors."""


class KuSyllabusHTTPError(KuSyllabusError):
    """Raised for HTTP errors not handled by the client (5xx after retries, 4xx other than 404)."""

    def __init__(self, status_code: int, url: str, message: str = "") -> None:
        self.status_code = status_code
        self.url = url
        super().__init__(message or f"HTTP {status_code} for {url}")


class SyllabusNotFound(KuSyllabusError):
    """Raised when a requested lectureNo does not exist (server returns 404).

    The library normally returns ``None`` instead of raising this; it exists for
    callers that explicitly opt into raise-on-missing behaviour.
    """

    def __init__(self, lecture_no: int | str) -> None:
        self.lecture_no = lecture_no
        super().__init__(f"Syllabus not found: lectureNo={lecture_no}")


class KuSyllabusParseError(KuSyllabusError):
    """Raised when an HTML response cannot be parsed into the expected shape."""

    def __init__(self, message: str, html_excerpt: str = "") -> None:
        self.html_excerpt = html_excerpt
        super().__init__(message)
