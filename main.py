"""Quick demo of the kusyllabus library.

Run with:

    uv run main.py
"""

from __future__ import annotations

import asyncio
import sys

# Make sure non-ASCII (Japanese) text prints cleanly on Windows consoles.
sys.stdout.reconfigure(encoding="utf-8")

from kusyllabus import (
    AsyncKuSyllabusClient,
    DayOfWeek,
    KuSyllabusClient,
    LanguageNo,
    SearchCondition,
    flatten_all_leaves,
)


def sync_demo() -> None:
    print("=== sync: search English Wednesday-1 lectures ===")
    cond = SearchCondition(language_no=LanguageNo.ENGLISH)
    cond.add_slot(DayOfWeek.WEDNESDAY, 1)
    with KuSyllabusClient() as ku:
        result = ku.search(cond, page=1)
        print(f"  total slots: {result.total} (showing first {len(result.rows)})")
        for row in result.rows[:5]:
            print(f"  [{row.lecture_no}] {row.title} -{', '.join(row.instructors)}")

        if result.rows:
            syl = ku.get_syllabus(result.rows[0].lecture_no)
            if syl:
                print("  first syllabus overview:")
                print("   ", (syl.overview_purpose or "")[:120], "...")


async def async_demo() -> None:
    print()
    print("=== async: fetch 3 syllabi concurrently ===")
    async with AsyncKuSyllabusClient() as ku:
        tree = await ku.get_all_tree()
        leaves = [n for n in flatten_all_leaves(tree) if n.kind == "open_syllabus"]
        ids = [n.lecture_no for n in leaves[:3]]
        syllabi = await ku.fetch_many_syllabi(ids, max_at_once=3, max_per_second=5)
        for lecture_no, syl in zip(ids, syllabi, strict=True):
            title = syl.title if syl else "MISS"
            print(f"  [{lecture_no}] {title}")


if __name__ == "__main__":
    sync_demo()
    asyncio.run(async_demo())
