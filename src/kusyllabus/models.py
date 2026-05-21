"""Pydantic models for parsed open-syllabus content."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class _Model(BaseModel):
    """Base for project models: tolerant of extra fields and frozen attributes."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)


class Teacher(_Model):
    """A single instructor row inside a syllabus page."""

    department: str = ""
    """所属部局 / Department of affiliation."""

    job_title: str = ""
    """職名 / Job title."""

    name: str = ""
    """氏名 / Instructor's name."""


class Syllabus(_Model):
    """The full content of one ``/la_syllabus?lectureNo=N`` page."""

    lecture_no: int
    """The ``lectureNo`` used to fetch this syllabus."""

    display_lang: str = "ja"
    """``ja`` for the Japanese version, ``en`` for the English version of this page."""

    course_numbers: list[str] = Field(default_factory=list)
    """科目ナンバリング / Course numbers.

    One syllabus can carry multiple codes (e.g. cross-listed UG/G courses
    on the ``/department_syllabus`` endpoint render two ``U-ENG29 39074 LJ10`` /
    ``U-ENG29 39074 LJ55`` rows separated by ``<br/>``).
    """

    title: str = ""
    """科目名 / Course title in the page's display language."""

    title_en: str | None = None
    """英訳 / Course title in English (only present on the JP page)."""

    teachers: list[Teacher] = Field(default_factory=list)

    language: str | None = None
    """使用言語 / Language of instruction (e.g. ``日本語``, ``英語``)."""

    credits: str | None = None
    """単位数 / Number of credits (e.g. ``2単位`` / ``2 credits``)."""

    class_style: str | None = None
    """授業形態 / Class style (e.g. ``講義`` / ``Lecture``)."""

    year_semester: str | None = None
    """開講年度・開講期 / Year/semesters."""

    target_year: str | None = None
    """配当学年 / Target year."""

    eligible_students: str | None = None
    """対象学生 / Eligible students."""

    days_and_periods: str | None = None
    """曜時限 / Days and periods. Multiple slots are newline-separated."""

    overview_purpose: str | None = None
    """授業の概要・目的 / Overview and purpose of the course."""

    objectives: str | None = None
    """到達目標 / Course objectives."""

    schedule_and_contents: str | None = None
    """授業計画と内容 / Course schedule and contents."""

    requirements: str | None = None
    """履修要件 / Course requirements."""

    evaluation: str | None = None
    """成績評価の方法・観点 / Evaluation methods and policy."""

    textbooks: str | None = None
    """教科書 / Textbooks."""

    references: str | None = None
    """参考書等 / References, etc."""

    study_outside_of_class: str | None = None
    """授業外学修（予習・復習）等 / Study outside of class."""

    essential_courses: str | None = None
    """主要授業科目 / Essential courses."""

    related_urls: list[str] = Field(default_factory=list)
    """関連URL / Related URLs (extracted ``<a class='reference-url'>`` hrefs)."""

    youtube_movie_ids: list[str] = Field(default_factory=list)
    """Embedded YouTube IDs (``data-movie-id`` of ``.youtube-movie`` elements)."""

    raw_labels: dict[str, str] = Field(default_factory=dict)
    """Original ``(ラベル名)`` → cleaned text mapping captured during parsing.

    Useful for diagnostics or fields that haven't been mapped to a typed attribute.
    """

    @property
    def course_number(self) -> str | None:
        """First entry of :attr:`course_numbers` (backwards-compatible shorthand)."""
        return self.course_numbers[0] if self.course_numbers else None


class SearchResultRow(_Model):
    """One row from the ``/search`` result table.

    ``department_no`` carries the value harvested from the detail-button link:

    * ``None`` when the detail link points at ``la_syllabus?lectureNo=N``
      (liberal-arts pool — fetch with ``ku.get_syllabus(lecture_no)``).
    * an ``int`` when the link points at
      ``department_syllabus?lectureNo=N&departmentNo=D`` — you **must** pass
      ``department_no=D`` to ``ku.get_syllabus`` or you'll either 404 or, worse,
      receive a stale row from a long-recycled ``lectureNo``.
    """

    lecture_no: int
    department_no: int | None = None
    """``None`` for ``la_syllabus`` rows, the department code for ``department_syllabus``."""

    title: str
    instructors: list[str] = Field(default_factory=list)
    department: str = ""
    """学部/大学院 column."""
    department_group: str = ""
    """学科等 column (e.g. ``人文・社会科学科目群／哲学・思想``)."""
    class_style: str = ""
    language: str = ""
    semester: str = ""
    days_and_periods: list[str] = Field(default_factory=list)
    level: str = ""
    academic_fields: list[str] = Field(default_factory=list)


class SearchResult(_Model):
    """Parsed ``/search`` page including pagination metadata."""

    total: int
    """Total number of matching course-slots as reported by the server."""

    page: int
    """1-based current page number."""

    page_size: int = 10
    """Always 10 on the live server; included so callers don't hard-code it."""

    rows: list[SearchResultRow] = Field(default_factory=list)

    has_next_page: bool = False
    has_prev_page: bool = False
    last_page_with_rows: int | None = None
    """Largest page number that still contains at least one row.

    The server reports ``total`` but only renders rows for ``LIBERAL_ARTS``
    (departmentNo=80). For other departments, ``total`` is non-zero while
    every page is empty; this field exposes that distinction.
    """

    @property
    def page_count(self) -> int:
        """Total page count derived from ``total`` (``ceil(total/page_size)``)."""
        if self.total <= 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size


class SyllabusTitleOption(_Model):
    """One ``<option>`` returned by ``/open_syllabus_titles?departmentNo=N``."""

    value: str
    """String value of the ``<option>``. Use as ``condition.openSyllabusTitle``."""

    label: str
    """Display text of the ``<option>`` (same as ``value`` in observed data)."""


class AllTreeNode(_Model):
    """One node of the 3-level tree rendered by ``/all``.

    The tree is ``Department → OpenTitle → Syllabus``; each child is itself an
    ``AllTreeNode``. Leaf nodes have a ``lecture_no`` set; branches have
    ``children`` populated.

    Two flavours of leaf exist because ``/all`` mixes two endpoints:

    * Liberal-arts / general-education leaves link to
      ``la_syllabus?lectureNo=N`` (3105 items, fully public). ``kind`` is
      ``"open_syllabus"`` and ``department_no`` is ``None``.
    * Faculty / graduate-school leaves link to
      ``department_syllabus?lectureNo=N&departmentNo=D`` (~8600 items, also
      publicly fetchable). ``kind`` is ``"department_syllabus"`` and
      ``department_no`` carries the department code.
    """

    name: str
    """学部名 / 学科分類名 / 講義名 depending on depth."""

    lecture_no: int | None = None
    """Only set for leaf nodes."""

    department_no: int | None = None
    """Only set for ``department_syllabus`` leaves; required to refetch them."""

    kind: str = "branch"
    """``"branch"``, ``"open_syllabus"`` or ``"department_syllabus"``."""

    children: list[AllTreeNode] = Field(default_factory=list)
