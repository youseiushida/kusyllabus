"""Tests for the CP932 encode/decode helpers."""

from __future__ import annotations

from kusyllabus.encoding import build_query, decode_response, quote_value


def test_quote_value_encodes_japanese_in_cp932() -> None:
    # Captured from the live HAR: 人文・社会科学... encoded as CP932.
    import urllib.parse

    encoded = quote_value("人文・社会科学科目群／哲学・思想")
    # First 6 bytes correspond to "人文" in CP932 → 0x90 0x6C 0x95 0x76 (人 = 0x906C, 文 = 0x95B6).
    assert encoded.startswith("%90l%95%B6")
    # Round-trip through the upstream codec produces the original string.
    raw = urllib.parse.unquote_to_bytes(encoded)
    assert raw.decode("cp932") == "人文・社会科学科目群／哲学・思想"


def test_quote_value_ascii_passes_through() -> None:
    assert quote_value("thermodynamics") == "thermodynamics"


def test_build_query_preserves_array_keys() -> None:
    """weekSchedule[31] uses square brackets that must not be percent-encoded."""
    qs = build_query([("condition.weekSchedule[31]", "true")])
    assert qs == "condition.weekSchedule[31]=true"


def test_build_query_empty_values_kept() -> None:
    """The browser submits empty fields; we faithfully reproduce that shape."""
    qs = build_query([("condition.departmentNo", ""), ("condition.keyword", "")])
    assert qs == "condition.departmentNo=&condition.keyword="


def test_build_query_mixed_japanese_and_ascii() -> None:
    qs = build_query(
        [
            ("condition.openSyllabusTitle", "哲学"),
            ("condition.keyword", "physics"),
            ("page", "2"),
        ]
    )
    # "哲学" = %93N%8Aw in CP932 (0x93 0x4E 0x8A 0x77).
    assert qs == "condition.openSyllabusTitle=%93N%8Aw&condition.keyword=physics&page=2"


def test_decode_response_handles_cp932_bytes() -> None:
    raw = "全学共通科目".encode("cp932")
    assert decode_response(raw) == "全学共通科目"


def test_decode_response_replaces_undecodable_bytes() -> None:
    # 0xFF is not a valid CP932 lead byte; ensure we don't crash.
    assert decode_response(b"abc\xff") != ""
