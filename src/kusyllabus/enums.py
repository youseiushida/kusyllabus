"""Master enumerations for open-syllabus search parameters.

Every value below comes from the live `<select>` options served at
``/external/open_syllabus/top`` (both Japanese and English versions). Refresh by
re-fetching ``/top`` if the upstream master changes.
"""

from __future__ import annotations

from enum import IntEnum


# ---------------------------------------------------------------------------
# Department / Faculty / Graduate school (condition.departmentNo)
# ---------------------------------------------------------------------------
class DepartmentNo(IntEnum):
    """`condition.departmentNo`.

    Only ``LIBERAL_ARTS`` (80) actually exposes individual syllabi; all other
    departments return result counts but empty result tables. Use the other
    enum members for filtering/labelling only.
    """

    LIBERAL_ARTS = 80
    LETTERS = 1
    EDUCATION = 4
    LAW = 6
    ECONOMICS = 8
    SCIENCE = 10
    MEDICINE = 12
    MEDICINE_HUMAN_HEALTH = 117
    PHARMACEUTICAL = 14
    ENGINEERING = 16
    AGRICULTURE = 18
    INTEGRATED_HUMAN = 61
    GS_LETTERS = 2
    GS_EDUCATION = 3
    GS_LAW = 5
    LAW_SCHOOL = 114
    GS_ECONOMICS = 7
    GS_SCIENCE = 9
    GS_MEDICINE = 11
    GS_MEDICINE_HUMAN_HEALTH = 116
    GS_PHARMACEUTICAL = 15
    GS_ENGINEERING = 17
    GS_AGRICULTURE = 19
    GS_HUMAN_AND_ENVIRONMENTAL = 59
    GS_ENERGY = 62
    GS_ASIAN_AFRICAN = 64
    GS_INFORMATICS = 66
    GS_BIOSTUDIES = 69
    GS_GLOBAL_ENVIRONMENTAL = 71
    SCHOOL_OF_GOVERNMENT = 73
    GS_MANAGEMENT = 74
    GS_ADVANCED_INTEGRATED = 119

    @property
    def label_jp(self) -> str:
        return _DEPARTMENT_JP[self]

    @property
    def label_en(self) -> str:
        return _DEPARTMENT_EN[self]

    @classmethod
    def from_label(cls, label: str, lang: str = "ja") -> DepartmentNo | None:
        table = _DEPARTMENT_JP if lang == "ja" else _DEPARTMENT_EN
        for member, name in table.items():
            if name == label:
                return member
        return None


_DEPARTMENT_JP: dict[DepartmentNo, str] = {
    DepartmentNo.LIBERAL_ARTS: "全学共通科目",
    DepartmentNo.LETTERS: "文学部",
    DepartmentNo.EDUCATION: "教育学部",
    DepartmentNo.LAW: "法学部",
    DepartmentNo.ECONOMICS: "経済学部",
    DepartmentNo.SCIENCE: "理学部",
    DepartmentNo.MEDICINE: "医学部(医)",
    DepartmentNo.MEDICINE_HUMAN_HEALTH: "医学部(人間)",
    DepartmentNo.PHARMACEUTICAL: "薬学部",
    DepartmentNo.ENGINEERING: "工学部",
    DepartmentNo.AGRICULTURE: "農学部",
    DepartmentNo.INTEGRATED_HUMAN: "総合人間学部",
    DepartmentNo.GS_LETTERS: "文学研究科",
    DepartmentNo.GS_EDUCATION: "教育学研究科",
    DepartmentNo.GS_LAW: "法学研究科（法政理論専攻）",
    DepartmentNo.LAW_SCHOOL: "法科大学院",
    DepartmentNo.GS_ECONOMICS: "経済学研究科",
    DepartmentNo.GS_SCIENCE: "理学研究科",
    DepartmentNo.GS_MEDICINE: "医学研究科",
    DepartmentNo.GS_MEDICINE_HUMAN_HEALTH: "医学研究科（人間健康科学系専攻）",
    DepartmentNo.GS_PHARMACEUTICAL: "薬学研究科",
    DepartmentNo.GS_ENGINEERING: "工学研究科",
    DepartmentNo.GS_AGRICULTURE: "農学研究科",
    DepartmentNo.GS_HUMAN_AND_ENVIRONMENTAL: "人間・環境学研究科",
    DepartmentNo.GS_ENERGY: "エネルギー科学研究科",
    DepartmentNo.GS_ASIAN_AFRICAN: "アジア・アフリカ地域研究研究科",
    DepartmentNo.GS_INFORMATICS: "情報学研究科",
    DepartmentNo.GS_BIOSTUDIES: "生命科学研究科",
    DepartmentNo.GS_GLOBAL_ENVIRONMENTAL: "地球環境学舎",
    DepartmentNo.SCHOOL_OF_GOVERNMENT: "公共政策大学院",
    DepartmentNo.GS_MANAGEMENT: "経営管理大学院",
    DepartmentNo.GS_ADVANCED_INTEGRATED: "総合生存学館",
}

_DEPARTMENT_EN: dict[DepartmentNo, str] = {
    DepartmentNo.LIBERAL_ARTS: "Liberal Arts and General Education Courses",
    DepartmentNo.LETTERS: "Faculty of Letters",
    DepartmentNo.EDUCATION: "Faculty of Education",
    DepartmentNo.LAW: "Faculty of Law",
    DepartmentNo.ECONOMICS: "Faculty of Economics",
    DepartmentNo.SCIENCE: "Faculty of Science",
    DepartmentNo.MEDICINE: "Faculty of Medicine (Medicine)",
    DepartmentNo.MEDICINE_HUMAN_HEALTH: "Faculty of Medicine (Human Health Science)",
    DepartmentNo.PHARMACEUTICAL: "Faculty of Pharmaceutical Sciences",
    DepartmentNo.ENGINEERING: "Faculty of Engineering",
    DepartmentNo.AGRICULTURE: "Faculty of Agriculture",
    DepartmentNo.INTEGRATED_HUMAN: "Faculty of Integrated Human Studies",
    DepartmentNo.GS_LETTERS: "Graduate School of Letters",
    DepartmentNo.GS_EDUCATION: "Graduate School of Education",
    DepartmentNo.GS_LAW: "Graduate School of Law (Legal and Political Studies)",
    DepartmentNo.LAW_SCHOOL: "Law School",
    DepartmentNo.GS_ECONOMICS: "Graduate School of Economics",
    DepartmentNo.GS_SCIENCE: "Graduate School of Science",
    DepartmentNo.GS_MEDICINE: "Graduate School of Medicine (Medicine/Medical Sience/Public Health)",
    DepartmentNo.GS_MEDICINE_HUMAN_HEALTH: "Graduate School of Medicine (Human Health Science)",
    DepartmentNo.GS_PHARMACEUTICAL: "Graduate School of Pharmaceutical Sciences",
    DepartmentNo.GS_ENGINEERING: "Graduate School of Engineering",
    DepartmentNo.GS_AGRICULTURE: "Graduate School of Agriculture",
    DepartmentNo.GS_HUMAN_AND_ENVIRONMENTAL: "Graduate School of Human and Environmental Studies",
    DepartmentNo.GS_ENERGY: "Graduate School of Energy Science",
    DepartmentNo.GS_ASIAN_AFRICAN: "Graduate School of Asian and African Area Studies",
    DepartmentNo.GS_INFORMATICS: "Graduate School of Informatics",
    DepartmentNo.GS_BIOSTUDIES: "Graduate School of Biostudies",
    DepartmentNo.GS_GLOBAL_ENVIRONMENTAL: "Graduate School of Global Environmental Studies",
    DepartmentNo.SCHOOL_OF_GOVERNMENT: "School of Government",
    DepartmentNo.GS_MANAGEMENT: "Graduate School of Management",
    DepartmentNo.GS_ADVANCED_INTEGRATED: "Graduate School of Advanced Integrated Studies in Human Survivability",
}


# ---------------------------------------------------------------------------
# Class style (condition.courseNumberingJugyokeitaiNo)
# ---------------------------------------------------------------------------
class JugyokeitaiNo(IntEnum):
    LECTURE = 1
    SEMINAR = 2
    PRACTICE = 3
    EXPERIMENT = 4
    FIELD_WORK = 5
    GRADUATE_RESEARCH = 6
    OTHERS = 7

    @property
    def label_jp(self) -> str:
        return _JUGYOKEITAI_JP[self]

    @property
    def label_en(self) -> str:
        return _JUGYOKEITAI_EN[self]


_JUGYOKEITAI_JP: dict[JugyokeitaiNo, str] = {
    JugyokeitaiNo.LECTURE: "講義",
    JugyokeitaiNo.SEMINAR: "演習",
    JugyokeitaiNo.PRACTICE: "実習",
    JugyokeitaiNo.EXPERIMENT: "実験",
    JugyokeitaiNo.FIELD_WORK: "フィールドワーク",
    JugyokeitaiNo.GRADUATE_RESEARCH: "授業外活動",
    JugyokeitaiNo.OTHERS: "その他",
}

_JUGYOKEITAI_EN: dict[JugyokeitaiNo, str] = {
    JugyokeitaiNo.LECTURE: "Lecture",
    JugyokeitaiNo.SEMINAR: "Seminar",
    JugyokeitaiNo.PRACTICE: "Practice",
    JugyokeitaiNo.EXPERIMENT: "Experiment",
    JugyokeitaiNo.FIELD_WORK: "Field Work",
    JugyokeitaiNo.GRADUATE_RESEARCH: "Graduate Research",
    JugyokeitaiNo.OTHERS: "Others",
}


# ---------------------------------------------------------------------------
# Language of instruction (condition.courseNumberingLanguageNo)
# ---------------------------------------------------------------------------
class LanguageNo(IntEnum):
    JAPANESE = 1
    ENGLISH = 2
    BILINGUAL = 3
    OTHERS = 4

    @property
    def label_jp(self) -> str:
        return _LANGUAGE_JP[self]

    @property
    def label_en(self) -> str:
        return _LANGUAGE_EN[self]


_LANGUAGE_JP: dict[LanguageNo, str] = {
    LanguageNo.JAPANESE: "日本語",
    LanguageNo.ENGLISH: "英語",
    LanguageNo.BILINGUAL: "バイリンガル",
    LanguageNo.OTHERS: "その他",
}

_LANGUAGE_EN: dict[LanguageNo, str] = {
    LanguageNo.JAPANESE: "Japanese",
    LanguageNo.ENGLISH: "English",
    LanguageNo.BILINGUAL: "Bilingual",
    LanguageNo.OTHERS: "Others",
}


# ---------------------------------------------------------------------------
# Semester (condition.semesterNo)
# ---------------------------------------------------------------------------
class SemesterNo(IntEnum):
    FIRST = 1
    SECOND = 2
    YEAR_ROUND = 3
    INTENSIVE_FIRST = 4
    INTENSIVE_SECOND = 5
    INTENSIVE_YEAR_ROUND = 6
    FIRST_HALF_OF_FIRST = 7
    SECOND_HALF_OF_FIRST = 8
    FIRST_HALF_OF_SECOND = 9
    SECOND_HALF_OF_SECOND = 10
    IRREGULAR_YEAR_ROUND = 11
    IRREGULAR_FIRST = 12
    IRREGULAR_SECOND = 13
    SECOND_THEN_FIRST = 17

    @property
    def label_jp(self) -> str:
        return _SEMESTER_JP[self]

    @property
    def label_en(self) -> str:
        return _SEMESTER_EN[self]


_SEMESTER_JP: dict[SemesterNo, str] = {
    SemesterNo.FIRST: "前期",
    SemesterNo.SECOND: "後期",
    SemesterNo.YEAR_ROUND: "通年",
    SemesterNo.INTENSIVE_FIRST: "前期集中",
    SemesterNo.INTENSIVE_SECOND: "後期集中",
    SemesterNo.INTENSIVE_YEAR_ROUND: "通年集中",
    SemesterNo.FIRST_HALF_OF_FIRST: "前期前半",
    SemesterNo.SECOND_HALF_OF_FIRST: "前期後半",
    SemesterNo.FIRST_HALF_OF_SECOND: "後期前半",
    SemesterNo.SECOND_HALF_OF_SECOND: "後期後半",
    SemesterNo.IRREGULAR_YEAR_ROUND: "通年不定",
    SemesterNo.IRREGULAR_FIRST: "前期不定",
    SemesterNo.IRREGULAR_SECOND: "後期不定",
    SemesterNo.SECOND_THEN_FIRST: "後期前期",
}

_SEMESTER_EN: dict[SemesterNo, str] = {
    SemesterNo.FIRST: "First semester",
    SemesterNo.SECOND: "Second semester",
    SemesterNo.YEAR_ROUND: "Year-round",
    SemesterNo.INTENSIVE_FIRST: "Intensive, First semester",
    SemesterNo.INTENSIVE_SECOND: "Intensive, Second semester",
    SemesterNo.INTENSIVE_YEAR_ROUND: "Intensive, year-round",
    SemesterNo.FIRST_HALF_OF_FIRST: "The first half of first semester",
    SemesterNo.SECOND_HALF_OF_FIRST: "The second half of first semester",
    SemesterNo.FIRST_HALF_OF_SECOND: "The first half of second semester",
    SemesterNo.SECOND_HALF_OF_SECOND: "The second half of second semester",
    SemesterNo.IRREGULAR_YEAR_ROUND: "Irregular, year-round",
    SemesterNo.IRREGULAR_FIRST: "Irregular, First semester",
    SemesterNo.IRREGULAR_SECOND: "Irregular, Second semester",
    SemesterNo.SECOND_THEN_FIRST: "Second semester, first semester",
}


# ---------------------------------------------------------------------------
# Level (condition.courseNumberingLevelNo)
# ---------------------------------------------------------------------------
class LevelNo(IntEnum):
    INTRODUCTORY_UG = 1
    FUNDAMENTAL_UG = 2
    ADVANCED_UG = 3
    THESIS_UG = 4
    FUNDAMENTAL_G = 5
    ADVANCED_G = 6
    APPLIED_G = 7
    COMMON_G = 8
    JOINT_UG_G = 9

    @property
    def label_jp(self) -> str:
        return _LEVEL_JP[self]

    @property
    def label_en(self) -> str:
        return _LEVEL_EN[self]


_LEVEL_JP: dict[LevelNo, str] = {
    LevelNo.INTRODUCTORY_UG: "導入的な内容の科目（学部科目）",
    LevelNo.FUNDAMENTAL_UG: "基礎的な内容の科目（学部科目）",
    LevelNo.ADVANCED_UG: "発展的な内容の科目（学部科目）",
    LevelNo.THESIS_UG: "卒業論文・卒業研究関連の科目（学部科目）",
    LevelNo.FUNDAMENTAL_G: "基礎的な内容の科目（大学院科目）",
    LevelNo.ADVANCED_G: "発展的な内容の科目・特殊講義科目（大学院科目）",
    LevelNo.APPLIED_G: "応用的な内容の科目・特殊講義科目（大学院科目）",
    LevelNo.COMMON_G: "大学院共通内容の科目（大学院科目）",
    LevelNo.JOINT_UG_G: "学部・大学院共同で開講される科目等",
}

_LEVEL_EN: dict[LevelNo, str] = {
    LevelNo.INTRODUCTORY_UG: "Introductory Courses (Undergraduate Courses)",
    LevelNo.FUNDAMENTAL_UG: "Fundamental Courses (Undergraduate Courses)",
    LevelNo.ADVANCED_UG: "Advanced Courses (Undergraduate Courses)",
    LevelNo.THESIS_UG: "Thesis / Supervised Research (Undergraduate Courses)",
    LevelNo.FUNDAMENTAL_G: "Fundamental Courses (Graduate Courses)",
    LevelNo.ADVANCED_G: "Advanced Courses / Supervised Research (Graduate Courses)",
    LevelNo.APPLIED_G: "Applied Courses / Supervised Research (Graduate Courses)",
    LevelNo.COMMON_G: "Common Graduate Courses (Graduate Courses)",
    LevelNo.JOINT_UG_G: "Joint Courses (Undergraduate and Graduate Courses)",
}


# ---------------------------------------------------------------------------
# Academic field (condition.courseNumberingBunkaNo) — 86 values; dict-based.
# ---------------------------------------------------------------------------
BUNKA_NAMES_JP: dict[int, str] = {
    1: "情報学基礎",
    2: "計算基盤",
    3: "人間情報学",
    4: "情報学フロンティア",
    5: "地球環境学",
    6: "環境解析学",
    7: "環境保全学",
    8: "環境創成学",
    9: "デザイン学",
    10: "生活科学",
    11: "科学教育・教育工学",
    12: "科学社会学・科学技術史",
    13: "文化財科学・博物館学",
    14: "地理学",
    15: "社会・安全システム科学",
    16: "人間医工学",
    17: "健康・スポーツ科学",
    18: "子ども学",
    19: "エネルギー科学",
    20: "生体分子科学",
    21: "脳科学",
    22: "地域研究",
    23: "ジェンダー",
    24: "観光学",
    25: "哲学",
    26: "芸術学",
    27: "文学",
    28: "言語学",
    29: "史学",
    30: "人文地理学",
    31: "文化人類学",
    32: "法学",
    33: "政治学",
    34: "経済学",
    35: "経営学",
    36: "社会学",
    37: "心理学",
    38: "教育学",
    39: "外国語",
    40: "スポーツ実習",
    41: "ILASセミナー（教養・共通教育）",
    42: "ナノ･マイクロ科学",
    43: "応用物理学",
    44: "量子ビーム科学",
    45: "計算科学",
    46: "数学",
    47: "天文学",
    48: "物理学",
    49: "地球惑星科学",
    50: "プラズマ科学",
    51: "基礎化学",
    52: "複合化学",
    53: "材料化学",
    54: "神経科学",
    55: "実験動物学",
    56: "腫瘍学",
    57: "ゲノム科学",
    58: "生物資源保全学",
    59: "生物科学",
    60: "基礎生物学",
    61: "人類学",
    62: "機械工学",
    63: "電気電子工学",
    64: "土木工学",
    65: "建築学",
    66: "材料工学",
    67: "プロセス・化学工学",
    68: "総合工学",
    69: "生産環境農学",
    70: "農芸化学",
    71: "森林圏科学",
    72: "水圏応用科学",
    73: "社会経済農学",
    74: "農業工学",
    75: "動物生産化学",
    76: "境界農学",
    77: "薬学",
    78: "基礎医学",
    79: "臨床医学",
    80: "境界医学",
    81: "社会医学",
    82: "内科系臨床医学",
    83: "外科系臨床医学",
    84: "歯学",
    85: "看護学",
    86: "総合生存学",
}

BUNKA_NAMES_EN: dict[int, str] = {
    1: "Principles of informatic",
    2: "Computing technologies",
    3: "Humaninformatics",
    4: "Frontiers of informatics",
    5: "Global Environmental studies",
    6: "Environmental analyses and evaluation",
    7: "Environmental conservation",
    8: "Sustainable and environmental system development",
    9: "Design science",
    10: "Human life science",
    11: "Science education/ Educational technology",
    12: "Sociology/History of science and technology",
    13: "Cultural assets study and museology",
    14: "Geography",
    15: "Social/Safety system science",
    16: "Biomedical engineering",
    17: "Health/Sports science",
    18: "Childhood science",
    19: "Energy science",
    20: "Biomolecular science",
    21: "Brain sciences",
    22: "Area studies",
    23: "Gender",
    24: "Tourism Studies",
    25: "Philosophy",
    26: "Art studies",
    27: "Literature",
    28: "Linguistics",
    29: "History",
    30: "Human geography",
    31: "Cultural anthropology",
    32: "Law",
    33: "Politics",
    34: "Economics",
    35: "Management",
    36: "Sociology",
    37: "Psychology",
    38: "Education",
    39: "Foreign language",
    40: "Sports practice",
    41: "Seminars in Liberal Arts and Sciences",
    42: "Nano/Micro science",
    43: "Applied physics",
    44: "Quantum beam science",
    45: "Computational science",
    46: "Mathematics",
    47: "Astronomy",
    48: "Physics",
    49: "Earth and planetary science",
    50: "Plasma science",
    51: "Basic chemistry",
    52: "Applied chemistry",
    53: "Materials chemistry",
    54: "Neuroscience",
    55: "Laboratory animal science",
    56: "Oncology",
    57: "Genome science",
    58: "Conservation of biological resources",
    59: "Biological Science",
    60: "Basic biology",
    61: "Anthropology",
    62: "Mechanical engineering",
    63: "Electrical and electronic engineering",
    64: "Civil engineering",
    65: "Architecture and building engineering",
    66: "Material engineering",
    67: "Process/Chemical engineering",
    68: "Integrated engineering",
    69: "Plant production and environmental agriculture",
    70: "Agricultural chemistry",
    71: "Forest and forest products science",
    72: "Applied aquatic science",
    73: "Agricultural science in society and economy",
    74: "Agroengineering",
    75: "Animal life science",
    76: "Boundary agriculture",
    77: "Pharmacy",
    78: "Basic medicine",
    79: "Clinical medicine",
    80: "Boundary medicine",
    81: "Society medicine",
    82: "Clinical internal medicine",
    83: "Clinical surgery",
    84: "Dentistry",
    85: "Nursing",
    86: "Advanced and Integrated Studies in Human Survivability",
}


def bunka_label(no: int, lang: str = "ja") -> str | None:
    table = BUNKA_NAMES_JP if lang == "ja" else BUNKA_NAMES_EN
    return table.get(no)


# ---------------------------------------------------------------------------
# Day/period (condition.weekSchedule[XY])
# ---------------------------------------------------------------------------
class DayOfWeek(IntEnum):
    """First digit of ``condition.weekSchedule[XY]``."""

    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6
    # SUNDAY (7) returns 0 hits in observed data but is technically encodeable.
    SUNDAY = 7

    @property
    def label_jp(self) -> str:
        return _DAY_JP[self]

    @property
    def label_en(self) -> str:
        return _DAY_EN[self]


_DAY_JP: dict[DayOfWeek, str] = {
    DayOfWeek.MONDAY: "月",
    DayOfWeek.TUESDAY: "火",
    DayOfWeek.WEDNESDAY: "水",
    DayOfWeek.THURSDAY: "木",
    DayOfWeek.FRIDAY: "金",
    DayOfWeek.SATURDAY: "土",
    DayOfWeek.SUNDAY: "日",
}
_DAY_EN: dict[DayOfWeek, str] = {
    DayOfWeek.MONDAY: "Mon",
    DayOfWeek.TUESDAY: "Tue",
    DayOfWeek.WEDNESDAY: "Wed",
    DayOfWeek.THURSDAY: "Thu",
    DayOfWeek.FRIDAY: "Fri",
    DayOfWeek.SATURDAY: "Sat",
    DayOfWeek.SUNDAY: "Sun",
}


def week_schedule_index(day: DayOfWeek | int, period: int) -> int:
    """Compute the index used in ``condition.weekSchedule[XY]``.

    >>> week_schedule_index(DayOfWeek.WEDNESDAY, 1)
    31
    >>> week_schedule_index(1, 2)
    12
    """
    d = int(day)
    if not 1 <= d <= 7:
        raise ValueError(f"day must be 1..7, got {d}")
    if not 1 <= period <= 5:
        raise ValueError(f"period must be 1..5, got {period}")
    return d * 10 + period


def parse_day_period_label(label: str) -> tuple[DayOfWeek, int] | None:
    """Parse strings like '水1', 'Wed.1', 'Mon.3' into (DayOfWeek, period)."""
    label = label.strip()
    # JP form: '水1'
    if label and label[0] in _DAY_JP.values():
        for day, name in _DAY_JP.items():
            if label.startswith(name) and label[len(name) :].isdigit():
                return day, int(label[len(name) :])
    # EN form: 'Wed.1'
    if "." in label:
        day_str, _, p = label.partition(".")
        for day, name in _DAY_EN.items():
            if name == day_str and p.isdigit():
                return day, int(p)
    return None
