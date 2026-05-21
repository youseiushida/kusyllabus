# kusyllabus

[![PyPI version](https://img.shields.io/pypi/v/kusyllabus.svg)](https://pypi.org/project/kusyllabus/)
[![Python 3.12+](https://img.shields.io/pypi/pyversions/kusyllabus.svg)](https://pypi.org/project/kusyllabus/)
[![CI](https://github.com/youseiushida/kusyllabus/actions/workflows/ci.yml/badge.svg)](https://github.com/youseiushida/kusyllabus/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/youseiushida/kusyllabus/blob/main/LICENSE)

京都大学の[オープンシラバス](https://www.k.kyoto-u.ac.jp/external/open_syllabus/top)をログインせずに叩く Python ライブラリ + agent-native CLI。
検索・全件ツリー・個別シラバス (全学共通 / 各学部)・学科分類マスタまでを型付きで扱える。

> **責務の境界**: 履修登録・成績照会など SSO ログインが必要な KULASIS 本体は対象外です。
> 京大 SSO セッションが必要な場合は [kuauth](https://pypi.org/project/kuauth/) を使い、認証済み session で KULASIS のエンドポイントを自前で叩いてください (詳細は[スコープ外](https://github.com/youseiushida/kusyllabus#スコープ外--sso-認証が必要な操作))。

```python
from kusyllabus import KuSyllabusClient, SearchCondition, DayOfWeek, LanguageNo

with KuSyllabusClient() as ku:
    cond = SearchCondition(language_no=LanguageNo.ENGLISH).add_slot(DayOfWeek.WEDNESDAY, 1)
    result = ku.search(cond)                # 1 GET
    print(f"{result.total} 件ヒット")

    for row in result.rows[:5]:             # 1ページ=10件固定 (upstream仕様)
        print(f"[{row.lecture_no}] {row.title}  --  {', '.join(row.instructors)}")
```

実行例 (2026 年 5 月時点):

```
21 件ヒット
[61585] The History of Eastern Thought I-E2  --  CATT， Adam Alvah
[61612] Introduction to World Religions-E2  --  DANESHGAR，Majid
[62419] Advanced Lecture for Pedagogy II-E2  --  BROTHERHOOD Thomas
[63902] Introduction to Urban Geography-E2  --  BAARS, Roger
[63735] Basic Physical Chemistry (quantum theory)-E2  --  Nguyen Thanh Phuc
```

> upstream は **1ページ 10件固定**・`sort` 系パラメータも無視。
> 全件取りたいときは `iter_search_pages()` か、より効率的な `/all` 1リクエストで階層ツリー取得 (`ku.get_all_tree()`)。

---

## インストール

Python 3.12+ 必須。

```sh
uv tool install kusyllabus   # CLI として使う (グローバル install)
uv add kusyllabus            # ライブラリとして自分のプロジェクトに追加
```

開発版:

```sh
git clone https://github.com/youseiushida/kusyllabus.git
cd kusyllabus
uv sync --all-groups
```

Windows で日本語出力が文字化けする場合は環境変数を設定 (CLI は自動で `sys.stdout` を UTF-8 に再構成するので通常不要):

```sh
PYTHONIOENCODING=utf-8 uv run python main.py
```

---

## CLI

ライブラリと同じ機能を `kusyllabus` コマンドから叩ける。出力は **デフォルトで人間向け Rich 表示**、
`--json` で機械可読 JSON に切替。10原則の [agent-native CLI](https://github.com/youseiushida/kusyllabus/blob/main/docs/RULE1.md) 設計準拠。
詳細仕様は [docs/SKILL.md](https://github.com/youseiushida/kusyllabus/blob/main/docs/SKILL.md)。

```sh
kusyllabus search list --slot wed1 --language 2 --limit 20         # 水1の英語授業
kusyllabus --json search list -k thermodynamics --limit 50          # JSON 出力
kusyllabus --json syllabus get 63736                                # 単一シラバス詳細
kusyllabus syllabus get 26510 --department 1                        # 学部シラバス (要 departmentNo)
kusyllabus --json all leaves --kind open --limit 0                  # 全 3105 件の (lectureNo, title)
kusyllabus syllabus fetch-all --out open.jsonl --kind open --force  # 並列で全件ダウンロード
kusyllabus --json titles list -d 80                                 # 学科分類オプション
kusyllabus master departments                                       # 学部マスタ enum
kusyllabus profile save eng-wed --language 2 --slot-index 31 --force
kusyllabus --profile eng-wed search list                            # 保存した条件を再利用
kusyllabus jobs list                                                # fetch-all 等の進捗台帳
kusyllabus --json agent-context                                     # エージェント用カタログ
kusyllabus feedback add "describe a friction point"                 # 改善提案 (ローカル+upstream)
```

主要グローバルフラグ: `--json` (envvar `KUSYLLABUS_JSON`) / `--profile NAME` (envvar `KUSYLLABUS_PROFILE`) / `--no-color` / `--quiet`。
コマンド単位で `--limit` (件数バウンド) / `--deliver=stdout|file:<path>|webhook:<url>` (出力配送) / `--force` (破壊操作の明示同意) / `--wait` (非同期ジョブをブロッキング化)。

`kusyllabus agent-context` を tools catalog として読み込めば、Claude Desktop / Cursor / OpenAI agents から型安全に呼び出せる。

---

## 設計方針

### 1 メソッド呼び出し = 1 HTTP リクエスト

オープンシラバスのサーバ仕様を実通信で検証したうえで、ライブラリの全公開メソッドは
原則として **1 メソッド = 1 リクエスト**。**暗黙の preflight・暗黙の N+1 ファンアウトは無い**:
`iter_search_pages()` の全ページ走査や `fetch_many_syllabi()` の並列取得はユーザが明示的に opt-in したときのみ。

| メソッド | 通信内容 |
|---------|---------|
| `ku.search(condition, page=N)` | 1 GET |
| `ku.iter_search_pages(condition)` | N GET (`next` リンクが切れるまで) |
| `ku.get_syllabus(lecture_no)` | 1 GET (`/la_syllabus`; 404 → `None`) |
| `ku.get_syllabus(lecture_no, department_no=D)` | 1 GET (`/department_syllabus`) |
| `ku.get_all_tree()` | **1 GET** で 3 階層ツリー全件 (約 2.3 MB / 11671 件) |
| `ku.get_syllabus_titles(department_no)` | 1 GET (学科分類のドロップダウン) |
| `ku.get_top_html()` | 1 GET (マスタ再生成用) |
| `aku.fetch_many_syllabi(targets, ...)` | N GET (並列度は `max_at_once` / `max_per_second` で制御) |

### Stateless GET only — Cookie/CSRF 不要

オープンシラバス全エンドポイントは認証なしの純粋 GET。Cookie/CSRF トークンも要らないので、
プロセス間 fan-out や横並列も自由。**ライブラリは何も状態を持たず、各リクエストは独立**。

### 文字エンコーディングは自動往復

upstream は **windows-31j (Shift_JIS) のみ**。クエリの日本語値は CP932 でパーセントエンコード、
レスポンスは CP932 でデコードする — どちらも `kusyllabus.encoding` が透過に処理する。
ユーザは Python の `str` だけを触ればよい。

### Retry と障害ハンドリング

- 5xx / 一過性のネットワークエラー: tenacity で指数 backoff + jitter (デフォルト最大 3 回)
- 404: `None` を返す (例: `ku.get_syllabus(999_999)` → `None`)
- 4xx (404以外) / 退却後の 5xx: `KuSyllabusHTTPError` を raise

---

## クイックリファレンス

### 検索 (簡易)

```python
result = ku.search(SearchCondition(keyword="thermodynamics"))
print(result.total)                # 該当件数
for row in result.rows:            # 1ページ目 (10件固定)
    print(row.lecture_no, row.title)
```

### 検索 (詳細条件 — fluent)

```python
from kusyllabus import SearchCondition, DayOfWeek, LanguageNo, SemesterNo, LevelNo

cond = (SearchCondition(
            language_no=LanguageNo.ENGLISH,
            semester_no=SemesterNo.FIRST,
            level_no=LevelNo.INTRODUCTORY_UG,
            keyword="physics",
        )
        .add_slot(DayOfWeek.WEDNESDAY, 1)
        .add_slot(DayOfWeek.MONDAY, 2))   # 複数 slot は OR 結合

result = ku.search(cond, display_lang="en")
```

使える条件: `department_no` / `open_syllabus_title` / `open_syllabus_title_en` / `jugyokeitai_no` /
`language_no` / `semester_no` / `level_no` / `bunka_no` (1..86) / `teacher_name` / `keyword` /
`syutyu` (集中講義のみ) / `week_schedule` (set of XY 整数; `add_slot()` 推奨)。

### ページング

```python
# 自動: 全ページを走査
for page in ku.iter_search_pages(cond):
    for row in page.rows:
        print(row.lecture_no, row.title)

# 手動: 1ページずつ
result = ku.search(cond, page=1)
if result.has_next_page:
    result = ku.search(cond, page=2)
```

`page` は 1 始まり (upstream は `page <= 0` で HTTP 500 を返す)。1 ページ 10 件固定で
`size` / `limit` / `perPage` 等はサーバ側で無視される。

### 個別シラバス

```python
syl = ku.get_syllabus(63736)            # 全学共通: /la_syllabus
syl = ku.get_syllabus(26510, department_no=1)   # 学部: /department_syllabus
syl_en = ku.get_syllabus(63736, display_lang="en")

print(syl.title)                        # "Basic Physical Chemistry (thermodynamics)-E2"
print(syl.course_number)                # "U-LAS13 10004 LE60"
print(syl.year_semester)                # "2026・後期"
print(syl.days_and_periods)             # "水1"
print(syl.credits, syl.class_style)     # "2単位" "講義"

for t in syl.teachers:                  # 複数教員あり得る
    print(f"  {t.department} / {t.job_title} / {t.name}")

print(syl.overview_purpose)             # 授業の概要・目的
print(syl.objectives)                   # 到達目標
print(syl.schedule_and_contents)        # 授業計画と内容
print(syl.evaluation)                   # 成績評価の方法・観点
print(syl.textbooks, syl.references)    # 教科書, 参考書等
print(syl.related_urls)                 # ["https://...", ...]
print(syl.youtube_movie_ids)            # 埋込 YouTube の ID

# パース漏れがないかは raw_labels で確認可能
print(list(syl.raw_labels.keys()))
```

### 全件ツリー (`/all`) と並列バルク取得

```python
import asyncio
from kusyllabus import AsyncKuSyllabusClient, flatten_all_leaves

async def main():
    async with AsyncKuSyllabusClient() as aku:
        tree = await aku.get_all_tree()            # 1 GET で 32 学部 × 343 学科分類 × 11671 leaves
        opens = [n for n in flatten_all_leaves(tree) if n.kind == "open_syllabus"]
        targets = [(n.lecture_no, n.department_no) for n in opens[:50]]

        # aiometer で並列度+RPS を制限しつつ N GET
        syllabi = await aku.fetch_many_syllabi(
            targets, max_at_once=8, max_per_second=5,
        )
        for syl in syllabi:
            if syl:
                print(syl.lecture_no, syl.title)

asyncio.run(main())
```

`/all` のツリーには 2 種類の leaf が混じる:

- `kind == "open_syllabus"` (3105 件): `/la_syllabus?lectureNo=N` で取得 — **全学共通科目のみ**
- `kind == "department_syllabus"` (8566 件): `/department_syllabus?lectureNo=N&departmentNo=D` で取得 — 各学部

### 学科分類マスタ (`/open_syllabus_titles`)

```python
opts = ku.get_syllabus_titles(80)         # departmentNo=80 (全学共通)
for o in opts:
    print(o.value)                        # "人文・社会科学科目群／哲学・思想" 等
```

学科分類は学部ごとに別オプションセット (60+ / 38 / …)。`condition.openSyllabusTitle` に渡す値は
**この `value` 文字列そのまま** (CP932 でエンコードされて wire に乗る)。

### マスタ enum (静的、API 呼び出し不要)

```python
from kusyllabus import DepartmentNo, JugyokeitaiNo, LanguageNo, SemesterNo, LevelNo, DayOfWeek
from kusyllabus.enums import BUNKA_NAMES_JP, BUNKA_NAMES_EN, bunka_label, week_schedule_index

DepartmentNo.LIBERAL_ARTS.label_jp      # "全学共通科目"
DepartmentNo.LIBERAL_ARTS.label_en      # "Liberal Arts and General Education Courses"
DepartmentNo.from_label("文学部")        # → DepartmentNo.LETTERS

bunka_label(25, "ja")                   # "哲学"
week_schedule_index(DayOfWeek.WEDNESDAY, 1)   # 31
```

---

## スコープ外 — SSO 認証が必要な操作

kusyllabus は **匿名カタログアクセス専用**。次の操作は対象外:

- **KULASIS 本体**: 履修登録 / 履修取消 / 成績照会 / 出席記録
- **個人化された機能**: お気に入り / 履修登録カート / 時間割表

京大 SSO 認証セッションが必要なら、姉妹ライブラリ **[kuauth](https://pypi.org/project/kuauth/)** が KULASIS を含む京大 SP の認証セッションを提供する:

```python
from kuauth import KyotoUAuth, KULASIS

with KyotoUAuth(username="a0XXXXXX", password="...") as auth:
    r = KULASIS(auth).get("/student/...")
    # 必要なエンドポイント (履修登録 POST 等) を HAR で特定して自前で叩く
```

kusyllabus と kuauth は **直接統合しない方針** です。kusyllabus は **匿名アクセス前提の単純な API surface** を保ち、SSO 認証ロジックは kuauth に分離します。両方使いたい場合は kuauth のセッションで生 HTTP を叩く形で書いてください。

---

## ドキュメント

- [docs/api-schema.md](https://github.com/youseiushida/kusyllabus/blob/main/docs/api-schema.md) — オープンシラバス HTTP スキーマの完全リバース調査結果
- [docs/SKILL.md](https://github.com/youseiushida/kusyllabus/blob/main/docs/SKILL.md) — エージェント向け CLI スキルマニフェスト (3-layer introspection の Layer 3)


---

## ライセンス

MIT (詳細は `LICENSE`)。
