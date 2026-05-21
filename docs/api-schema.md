# 京都大学オープンシラバス スキーマ仕様書

調査日: 2026-05-21  
対象: `https://www.k.kyoto-u.ac.jp/external/open_syllabus/`  
調査方法: 提供されたHARファイル(`har/all_*.har`, `har/search_*.har`, `har/search_en_*.har`)とHTML(`html/`)
の静的分析 + 直接HTTP通信による動的検証 (`out/` 配下に検証時のレスポンスを保存)

---

## 0. サマリー（CLI実装者向け最小事実）

| 項目 | 値 |
| --- | --- |
| ベースURL | `https://www.k.kyoto-u.ac.jp/external/open_syllabus/` |
| 認証 | **なし**（Cookie/CSRFトークン不要） |
| 全リクエスト | **GET** のみ |
| レスポンス文字コード | **windows-31j (Shift_JIS, MS932)** — UTF-8ではない |
| `Content-Type` | `text/html;charset=windows-31j` (常に) |
| JSON API | **なし**（`Accept: application/json` を送ってもHTMLが返る） |
| 1ページ件数 | **10件固定**（`size`/`limit`/`perPage` 等のパラメータは効かない） |
| ページング | クエリ `page=N` (1始まり) |
| ソート | **不可**（`sort`, `orderBy`, `order` パラメータは全て無視される） |
| 並列実行 | 可能（セッション無し・各リクエスト独立） |
| 公開範囲 | **全学共通科目 (`departmentNo=80`) の3105件のみ実体公開**。学部・大学院科目は件数のみ表示で詳細は閲覧不可 |
| URL中の日本語 | **CP932(Shift_JIS) でパーセントエンコード**（UTF-8ではない！） |
| 言語切替 | クエリ `display_lang=en` / `display_lang=jp` (どのページにも付与可) |

### CLI設計上の重要メモ
- レスポンスを読むには `response.content.decode('cp932')`（Pythonの場合）
- 検索キーワード等をURLに埋める時も `urllib.parse.quote(s, encoding='cp932')` を使う
- ソート不能なので「最新順」「コース番号順」などは取得後にクライアント側でソートする
- 並列に100リクエスト程度叩いても問題なし（試したが全成功・サーバ側レート制限の兆候なし）
- ただし「`page=0`」「`page=-1`」は **HTTP 500** を返すので 1 始まりにすること

---

## 1. エンドポイント一覧

| メソッド | パス | 用途 | 主要パラメータ |
| --- | --- | --- | --- |
| GET | `/external/open_syllabus/top` | 検索フォームのトップページ。`<select>` 各種の選択肢が埋め込み済み | `display_lang` |
| GET | `/external/open_syllabus/open_syllabus_titles` | 学部選択時にAJAXで呼ばれ、`<option>` HTMLフラグメントを返す | `departmentNo` (必須) |
| GET | `/external/open_syllabus/search` | 検索結果リスト | `condition.*` 群、`page`、`display_lang` |
| GET | `/external/open_syllabus/all` | 学部→学科分類→講義の階層ツリーで全件リスト（公開分のみ＝3105件） | `display_lang` |
| GET | `/external/open_syllabus/la_syllabus` | 個別シラバス詳細 | `lectureNo` (必須・数値5桁), `display_lang` |

すべて `text/html;charset=windows-31j` を返す。

### 共通レスポンスヘッダ
```
Server: nginx/1.18.0 (Ubuntu)
Content-Type: text/html;charset=windows-31j
Transfer-Encoding: chunked
cache-control: no-store
pragma: no-cache
expires: Thu, 01 Jan 1970 00:00:00 GMT
set-cookie: JSESSIONID=...; Path=/
set-cookie: SSESSIONID=...; Path=/; Secure
set-cookie: cserver=ku_ganymede; path=/
X-UA-Compatible: IE=edge
```
- バックエンド: JSP (`<div id="jsp_path">external/open_syllabus/xxx.jsp</div>` がHTML末尾にある)
- `JSESSIONID` などは発行されるが **送り返さなくても全機能動作する**

---

## 2. `/top` — トップページ／検索フォーム

### 2.1 リクエスト
```
GET /external/open_syllabus/top
GET /external/open_syllabus/top?display_lang=en
GET /external/open_syllabus/top?display_lang=jp
```

### 2.2 レスポンスから抽出できる固定マスタ
HTML内の `<select>` から、検索フォームに使える全コード値が取得できる。これは将来CLIの`--department=文学部`のような名前指定をコードに解決するために必要。下表は実通信で取得した最新の選択肢。

#### 学部・研究科 (`condition.departmentNo`)
| value | 名称(JP) |
| --- | --- |
| 80 | 全学共通科目 ★公開シラバス3105件あり |
| 1 | 文学部 |
| 4 | 教育学部 |
| 6 | 法学部 |
| 8 | 経済学部 |
| 10 | 理学部 |
| 12 | 医学部(医) |
| 117 | 医学部(人間) |
| 14 | 薬学部 |
| 16 | 工学部 |
| 18 | 農学部 |
| 61 | 総合人間学部 |
| 2 | 文学研究科 |
| 3 | 教育学研究科 |
| 5 | 法学研究科（法政理論専攻） |
| 114 | 法科大学院 |
| 7 | 経済学研究科 |
| 9 | 理学研究科 |
| 11 | 医学研究科 |
| 116 | 医学研究科（人間健康科学系専攻） |
| 15 | 薬学研究科 |
| 17 | 工学研究科 |
| 19 | 農学研究科 |
| 59 | 人間・環境学研究科 |
| 62 | エネルギー科学研究科 |
| 64 | アジア・アフリカ地域研究研究科 |
| 66 | 情報学研究科 |
| 69 | 生命科学研究科 |
| 71 | 地球環境学舎 |
| 73 | 公共政策大学院 |
| 74 | 経営管理大学院 |
| 119 | 総合生存学館 |

各学部の検索結果件数（取得日 2026-05-21）の総和は `11845`（`/search?` の条件なしと完全一致）。  
ただし **公開シラバス本体があるのは `80=全学共通科目` の 3105 件のみ**。他学部は件数だけ返って結果テーブルは空 (`<tr class="odd_normal">` が0行)。

#### 授業形態 (`condition.courseNumberingJugyokeitaiNo`)
| value | 名称 |
| --- | --- |
| 1 | 講義 |
| 2 | 演習 |
| 3 | 実習 |
| 4 | 実験 |
| 5 | フィールドワーク |
| 6 | 授業外活動 |
| 7 | その他 |

#### 使用言語 (`condition.courseNumberingLanguageNo`)
| value | 名称 |
| --- | --- |
| 1 | 日本語 |
| 2 | 英語 |
| 3 | バイリンガル |
| 4 | その他 |

#### 開講期 (`condition.semesterNo`)
| value | 名称 |
| --- | --- |
| 1 | 前期 |
| 2 | 後期 |
| 3 | 通年 |
| 4 | 前期集中 |
| 5 | 後期集中 |
| 6 | 通年集中 |
| 7 | 前期前半 |
| 8 | 前期後半 |
| 9 | 後期前半 |
| 10 | 後期後半 |
| 11 | 通年不定 |
| 12 | 前期不定 |
| 13 | 後期不定 |
| 17 | 年度集中 |

#### レベル (`condition.courseNumberingLevelNo`)
| value | 名称 |
| --- | --- |
| 1 | 導入的な内容の科目（学部科目） |
| 2 | 基礎的な内容の科目（学部科目） |
| 3 | 発展的な内容の科目（学部科目） |
| 4 | 卒業論文・卒業研究関連の科目（学部科目） |
| 5 | 基礎的な内容の科目（大学院科目） |
| 6 | 発展的な内容の科目・特殊講義科目（大学院科目） |
| 7 | 応用的な内容の科目・特殊講義科目（大学院科目） |
| 8 | 大学院共通内容の科目（大学院科目） |
| 9 | 学部・大学院共同で開講される科目等 |

#### 学修分野 (`condition.courseNumberingBunkaNo`) — 1〜86 (全86種)
代表的なものを抜粋:
| value | 名称 |
| --- | --- |
| 1 | 哲学基礎 |
| 2 | 計算機科学 |
| 3 | 人間情報学 |
| 10 | 数理科学 |
| 12 | 科学社会学・科学技術史 |
| 20 | 物性物理学 |
| 27 | 化学 |
| 28 | 生物学 |
| 32 | 法学 |
| 34 | 経済学 |
| 38 | 教育学 |
| 41 | ILASセミナー（基礎・教養共通） |
| 84 | 内科系臨床医学 |
| 86 | 看護専門学 |
| ... | （全86項目はトップページの `<select name="condition.courseNumberingBunkaNo">` を直接パース） |

#### 曜時限 (`condition.weekSchedule[XY]=true`)
チェックボックス形式の配列パラメータ。インデックス `XY` は：
- `X` = 曜日: `1=月, 2=火, 3=水, 4=木, 5=金, 6=土, 7=日`
- `Y` = 時限: `1, 2, 3, 4, 5`

例: 水曜1限 = `condition.weekSchedule[31]=true`、月曜2限 = `condition.weekSchedule[12]=true`

実通信で土曜(6)まで有効、日曜(7)・6限以降は0件（仕様上スロット無し）。  
**複数指定は OR条件**: 水1と月1を両方チェック → 両者の和集合 (実測: wed1=260, mon1=215, wed1+mon1=473)。

#### 集中講義 (`condition.syutyu`)
- `true` で集中講義のみフィルタ (2593件ヒット)
- `false` でフィルタなし（デフォルト）

### 2.3 学科分類 (`condition.openSyllabusTitle` / `condition.openSyllabusTitleEn`)
**学部依存・動的**。トップページの初期表示では空で、`<select id="select_departmentNo">` を変更したタイミングで AJAX (`/open_syllabus_titles?departmentNo=X`) が呼ばれて `<option>` が埋まる。

`value` 属性は数値IDではなく**学科分類名そのもの文字列**（CP932エンコードに注意）:
- 例 (dept=80): `value="人文・社会科学科目群／哲学・思想"`、`value="自然科学科目群／物理学"` …
- 例 (dept=1):  `value="哲学"`, `value="言語学"`, `value="日本史学"` …

CLI実装時は、`/open_syllabus_titles?departmentNo=X` を一度叩いて辞書を作っておくと便利。

---

## 3. `/open_syllabus_titles` — 学科分類AJAX

### リクエスト
```
GET /external/open_syllabus/open_syllabus_titles?departmentNo=80
X-Requested-With: XMLHttpRequest   ← 任意
```

### レスポンス（HTMLフラグメント）
```html
<option value="" class="form_disable">----</option>
<option value="人文・社会科学科目群／哲学・思想" >人文・社会科学科目群／哲学・思想</option>
<option value="人文・社会科学科目群／歴史・文明" >人文・社会科学科目群／歴史・文明</option>
...
```
- `departmentNo=` (空) は52バイトの「`----` のみ」短文を返す
- 学部毎に十数〜数十項目（dept=80で60件、dept=1で38件など）

---

## 4. `/search` — 検索結果リスト

### 4.1 リクエスト全パラメータ

すべて GET クエリ。**全て optional**（何もつけなくても `/search` は11845件のリストを返す）。

| パラメータ名 | 型 | 説明 / 値 |
| --- | --- | --- |
| `condition.departmentNo` | int | 学部/研究科コード。空文字または不指定で全件。**複数指定不可**（重複時は後勝ち or 無視で実質1値のみ有効） |
| `condition.openSyllabusTitle` | string | 日本語版の学科分類名（**CP932エンコード**で送る） |
| `condition.openSyllabusTitleEn` | string | 英語版の学科分類名 |
| `condition.courseNumberingJugyokeitaiNo` | int | 授業形態(1-7) |
| `condition.courseNumberingLanguageNo` | int | 使用言語(1-4) |
| `condition.semesterNo` | int | 開講期(1-17) |
| `condition.courseNumberingLevelNo` | int | レベル(1-9) |
| `condition.courseNumberingBunkaNo` | int | 学修分野(1-86) |
| `condition.teacherName` | string | 教員名(部分一致, JP表記, CP932) |
| `condition.teacherNameEn` | string | 教員名(英語版) |
| `condition.keyword` | string | キーワード(部分一致, JP, CP932) |
| `condition.keywordEn` | string | キーワード(英語版) |
| `condition.syutyu` | bool | 集中講義のみ (`true`/`false`) |
| `condition.weekSchedule[XY]` | bool | 曜時限チェックボックス。`X`=曜日(1-7), `Y`=時限(1-5)。複数指定は OR |
| `page` | int | 1始まり。`0` や負値は HTTP 500 |
| `display_lang` | string | `en` で英語UI、`jp` で日本語UI（既定） |
| `x`, `y` | int | `<input type="image">` のクリック座標。**サーバは無視するので送らなくてよい** |
| `sort` / `orderBy` / `order` | (any) | 受理されるが**無視**（並び順は固定） |
| `size` / `limit` / `perPage` / `rows` / `count` | (any) | 受理されるが**無視**（10件固定） |

### 4.2 文字エンコーディング上の注意

URLクエリに日本語を埋める時は **CP932(Shift_JIS)** でパーセントエンコードする。例:
- 「人文・社会科学科目群／芸術・文学・言語」(JP) → `%90l%95%B6%81E%8E%D0%89%EF%89%C8%8Aw%89%C8%96%DA%8CQ%81%5E%8C%7C%8Fp%81E%95%B6%8Aw%81E%8C%BE%8C%EA`

Python:
```python
import urllib.parse
v = urllib.parse.quote("人文・社会科学科目群／哲学・思想", encoding="cp932")
```

### 4.3 レスポンス構造（日本語UI）

```html
<!-- ヘッダ部 (検索フォーム) - /top と同じ select 群が初期値付きで再掲される -->
...
<!-- 検索結果サマリ -->
<center>
  <div style="width: 700px; text-align: left;">
    <img src="/img/subheading_search_result.gif" alt="検索結果"><br />
    検索結果は全部で<b>260</b>件です。     ← 件数
  </div>
</center>

<!-- ページネーション (両端: 前の10件 / 次の10件、中央: 数字リンク) -->
<table>...
  <a href="search?...&page=2" class="pager_link">2</a>
  ...
</table>

<!-- 結果テーブル -->
<table class="standard_list" style="width:860px;">
  <tr class="th_normal">
    <td>科目名</td><td>担当教員</td><td>学部／大学院</td><td>学科等</td>
    <td>授業形態</td><td>使用言語</td><td>開講期</td><td>曜時限</td>
    <td>レベル</td><td>学問分野</td><td></td>   <!-- 詳細ボタン -->
  </tr>
  <tr class="odd_normal">    <!-- 奇数行: odd_normal, 偶数行: even_normal -->
    <td>The History of Eastern Thought I-E2</td>
    <td>CATT， Adam Alvah</td>     <!-- 複数教員は <br /> 区切り -->
    <td>全学共通科目</td>
    <td>人文・社会科学科目群／哲学・思想</td>
    <td>講義</td>
    <td>英語</td>
    <td>前期</td>
    <td>水1</td>                   <!-- 複数曜時限は <br /> 区切り -->
    <td>導入的な内容の科目（学部科目）</td>
    <td>哲学</td>                  <!-- 複数分野は <br /> 区切り -->
    <td>
      <a href="la_syllabus?lectureNo=61585">
        <img src="/img/button_mini_detail.gif" />
      </a>
    </td>
  </tr>
  ...
</table>
```

### 4.4 レスポンス構造（英語UI: `display_lang=en`）

カラム名のみが英語化される（値はDB内の英語表記がある場合はそれが入る、無ければ日本語のまま）:

| 日本語カラム | 英語カラム |
| --- | --- |
| 科目名 | Course title |
| 担当教員 | Instructor |
| 学部／大学院 | Undergraduate / Graduate |
| 学科等 | Department, etc |
| 授業形態 | Course Type |
| 使用言語 | Language |
| 開講期 | Year/Term |
| 曜時限 | Day/Period |
| レベル | Level |
| 学問分野 | Academic Field |

曜時限の値も英語表記になる（`水1` → `Wed.1`、`月3` → `Mon.3`）。

### 4.5 ページネーション仕様

- 1ページ **固定10件**。クライアントから変更不可
- ページは `page=1` から始まる
- `page=0`, `page=-1` は **HTTP 500**
- 結果総数を超えるページは HTTP 200 で **0行＋ヘッダのみ**（25KB 程度の空ページが返る）
- ページ数の上限は `ceil(total/10)` だが、**dept=80 以外は本体の表示行が0なので、上限ページに意味がない**
- `/search?` 条件なしで `page=300` まで結果がある (=実体は 3105件 ≒ dept=80 の全件)

### 4.6 件数と公開状況の関係（最重要）

```
合計total (11845)
 ├── 全学共通(80): total=3105, 各ページに10件のシラバス行  ←★公開
 └── 他31学部・研究科: total合計=8740, 各ページは空     ←非公開
```

つまり、**学部や大学院科目で検索しても件数は出るが個別シラバスは見られない**。CLIは「指定された学部に公開シラバスがあるか」を `departmentNo=80` でしかヒットしないとして扱うべき。

---

## 5. `/all` — 階層形式の全件リスト

### リクエスト
```
GET /external/open_syllabus/all
GET /external/open_syllabus/all?display_lang=en
```

### レスポンス概要
- 約 **2.1MB** のHTML（英語版は2.4MB）
- 学部 → 学科分類 → シラバスの 3階層 ネスト
- 全シラバスリンク **3105件** (`la_syllabus?lectureNo=NNNNN`)
- 各リンクは `<a href="la_syllabus?lectureNo=61323">哲学Ｉ</a>` のように `lectureNo` と科目名(タイトル)のみを持つ

### 構造
```html
<div class="departmentName">全学共通科目<span class="departmentIcon">＋</span></div>
<div class="departmentSection">
  <div>
    <div class="openTitle">人文・社会科学科目群／哲学・思想<span class="openTitleIcon">＋</span></div>
    <div class="syllabusses">
      <div class="syllabusTitle">
        <a href="la_syllabus?lectureNo=61323">哲学Ｉ</a>
      </div>
      <div class="syllabusTitle">
        <a href="la_syllabus?lectureNo=61325">哲学Ｉ</a>
      </div>
      ...
    </div>
  </div>
  <div>
    <div class="openTitle">人文・社会科学科目群／歴史・文明<span class="openTitleIcon">＋</span></div>
    <div class="syllabusses">
      ...
    </div>
  </div>
</div>
```

**CLI実装ヒント**: 全シラバスIDを取得するのに最高効率のエンドポイント（1リクエストで完結）。各シラバスの詳細は `lectureNo` を `/la_syllabus?lectureNo=N` で順次取得する。

---

## 6. `/la_syllabus` — 個別シラバス詳細

### 6.1 リクエスト
```
GET /external/open_syllabus/la_syllabus?lectureNo=63736
GET /external/open_syllabus/la_syllabus?lectureNo=63736&display_lang=en
```

- `lectureNo` は **数値5桁**（観測範囲: 61000〜64999 程度）
- 存在しないIDは **HTTP 404 Not Found**（不正な値 `abc` や 空も同様）
- `display_lang=en` で英語版（フィールドラベルが英語化、本文がDBに英語で登録されている場合は英訳本文）

### 6.2 フィールド一覧（観測したラベル全23種）

シラバス本体は1個の `<table class="lesson_plan_sell">` 内に行ごとに格納されている。各セルは `<span class="lesson_plan_subheading">(ラベル名)</span>` で識別できる。

| 日本語ラベル | 英語ラベル (display_lang=en) | 内容例 |
| --- | --- | --- |
| 科目ナンバリング | Course number | `U-LAS13 10004 LE60` |
| 科目名 | Course title | `Basic Physical Chemistry (thermodynamics)-E2` |
| 英 訳 | (上の Course title に統合) | `Sociology I` |
| 所属部局 | Department of affiliation | `工学研究科` / `Graduate School of Engineering` |
| 職 名 | Job title | `講師` / `Senior Lecturer` |
| 氏 名 | Instructor's name | `Nguyen Thanh Phuc` |
| 使用言語 | Language of instruction | `英語` / `English` |
| 単位数 | Number of credits | `2単位` / `2 credits` |
| 授業形態 | Class style | `講義` / `Lecture` |
| 開講年度・開講期 | Year/semesters | `2026・後期` / `2026・Second semester` |
| 配当学年 | Target year | `主として１・２回生` |
| 対象学生 | Eligible students | `理系向` |
| 曜時限 | Days and periods | `水1` / `Wed.1` (複数は改行区切り) |
| 授業の概要・目的 | Overview and purpose of the course | 自由記述 |
| 到達目標 | Course objectives | 自由記述 |
| 授業計画と内容 | Course schedule and contents | 自由記述 |
| 履修要件 | Course requirements | 自由記述 ("特になし" 等) |
| 成績評価の方法・観点 | Evaluation methods and policy | 自由記述 |
| 教科書 | Textbooks | "使用しない" or 書誌情報 |
| 参考書等 | References, etc. | 書誌情報・複数行 |
| 授業外学修（予習・復習）等 | Study outside of class (preparation and review) | 自由記述 |
| 主要授業科目 | Essential courses | 関連授業の名前 |
| **関連URL** *(オプション)* | (英語名未確認) | 外部URLが `<a class="reference-url">` で含まれる |

オプション要素:
- **YouTube動画**: 一部のシラバスには `class="youtube-row"` ＋ `class="youtube-movie" data-movie-id="..."` の埋め込みが存在。クリックすると `https://www.youtube-nocookie.com/embed/{id}` を iframe で開く
- **参考URL**: `<a class="reference-url" href="...">...</a>` 形式
- **複数教員**: 「所属部局／職名／氏名」の3カラム表に複数行が並ぶ（例: `lectureNo=63481` は4教員）

### 6.3 科目ナンバリング (Course number) パーサ
`U-LAS00 10004 LJ34` の形式は京大の公式ナンバリング規則:
- 第1セグメント: `U-LAS00` 等 — 学部・学科目区分（`U` は学部、`LAS` は Liberal Arts and Sciences）
- 第2セグメント: 5桁数値 — 科目固有のシリアル
- 第3セグメント: `LJ34` / `LE60` / `SJ34` 等
  - 1文字目: 形式 (`L`=Lecture, `S`=Seminar)
  - 2文字目: 主使用言語 (`J`=Japanese, `E`=English, `B`=Both)
  - 3-4文字目: レベル+α (`34` 等の2桁数字)

### 6.4 サンプルHTML（日本語UI、`lectureNo=63736`）

```html
<table border="1" class="lesson_plan_sell" width="520" cellspacing="0" cellpadding="2">
  <tr>
    <td colspan="2" class="lesson_plan_sell upperGray">
      <table>
        <tr><td><span class="lesson_plan_subheading">(科目ナンバリング)</span></td>
            <td>U-LAS13 10004 LE60<br/></td></tr>
      </table>
    </td>
  </tr>
  <tr valign="top">
    <td class="lesson_plan_sell">
      <table>
        <tr><td><span class="lesson_plan_subheading">(科目名)</span></td>
            <td><b>Basic Physical Chemistry (thermodynamics)-E2 <br /></b></td></tr>
        <tr><td><span class="lesson_plan_subheading">(英 訳)</span></td>
            <td>Basic Physical Chemistry (thermodynamics)-E2</td></tr>
      </table>
    </td>
    <td class="lesson_plan_sell">
      <table>
        <tr>
          <td><span class="lesson_plan_subheading">(所属部局)</span></td>
          <td><span class="lesson_plan_subheading">(職 名)</span></td>
          <td><span class="lesson_plan_subheading">(氏 名)</span></td>
        </tr>
        <tr>
          <td>工学研究科</td><td>講師</td><td>Nguyen Thanh Phuc</td>
        </tr>
      </table>
    </td>
  </tr>
  <!-- 使用言語/単位数/授業形態/開講年度/配当学年/対象学生/曜時限 -->
  <!-- 授業の概要・目的、到達目標、授業計画と内容、履修要件、成績評価の方法・観点 -->
  <!-- 教科書、参考書等、授業外学修、主要授業科目 -->
</table>
```

---

## 7. URLクエリ実例集

| やりたいこと | URL |
| --- | --- |
| トップページ(日本語) | `/external/open_syllabus/top` |
| トップページ(英語) | `/external/open_syllabus/top?display_lang=en` |
| 全件ツリー | `/external/open_syllabus/all` |
| 条件なし検索 (1ページ目) | `/external/open_syllabus/search` |
| 水曜1限の科目 | `/external/open_syllabus/search?condition.weekSchedule%5B31%5D=true` |
| 水曜1限の2ページ目 | `/external/open_syllabus/search?condition.weekSchedule%5B31%5D=true&page=2` |
| 集中講義のみ | `/external/open_syllabus/search?condition.syutyu=true` |
| 英語授業のみ | `/external/open_syllabus/search?condition.courseNumberingLanguageNo=2` |
| 全学共通・前期 | `/external/open_syllabus/search?condition.departmentNo=80&condition.semesterNo=1` |
| キーワード「physics」 | `/external/open_syllabus/search?condition.keyword=physics` |
| 個別シラバス(JP) | `/external/open_syllabus/la_syllabus?lectureNo=63736` |
| 個別シラバス(EN) | `/external/open_syllabus/la_syllabus?lectureNo=63736&display_lang=en` |
| AJAX 学科分類 | `/external/open_syllabus/open_syllabus_titles?departmentNo=80` |

---

## 8. CLIツール設計のための推奨アーキテクチャ

### 8.1 推奨機能
1. **`list`**: `/all` 1リクエストで全3105件の `(lectureNo, title)` を取得・ローカルJSONキャッシュ
2. **`search`**: `/search` をラップ。条件名で叩く(`--department=全学共通`, `--day=mon --period=1` など)
3. **`get <lectureNo>`**: `/la_syllabus` を叩いて構造化JSONで出力
4. **`fetch-all`**: 並列に `/la_syllabus` を 3105件全件取得（並列度10程度推奨）
5. **`fields`**: マスタを `/top` から取得して `--departments`, `--bunka` 等のリスト表示
6. **`refresh-titles <department>`**: `/open_syllabus_titles` で学科分類リストをキャッシュ

### 8.2 言語名→コード解決の戦略
`departmentNo` などは数値だが、CLIでは `--department="工学部"` のように指定したい。  
初回起動時に `/top` をパースしてマスタテーブル(`name → value`)を作り、ローカルJSON にキャッシュ。

### 8.3 文字エンコーディング処理（最重要）
- リクエスト時: クエリ文字列の値は `urllib.parse.quote(value, encoding='cp932')` で必ず CP932 エンコード
- レスポンス時: `response.content.decode('cp932')` で必ず CP932 デコード
- 出力時: 標準出力に書く前に UTF-8 に再エンコード

```python
import urllib.parse, urllib.request

def search(params: dict, page: int = 1) -> str:
    qs_parts = []
    for k, v in params.items():
        # CP932 エンコード
        v_enc = urllib.parse.quote(str(v), encoding='cp932', safe='')
        k_enc = urllib.parse.quote(k, encoding='ascii', safe='[].')
        qs_parts.append(f"{k_enc}={v_enc}")
    qs_parts.append(f"page={page}")
    url = "https://www.k.kyoto-u.ac.jp/external/open_syllabus/search?" + "&".join(qs_parts)
    req = urllib.request.Request(url, headers={
        "User-Agent": "kusyllabus-cli/0.1",
        "Accept-Encoding": "gzip",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            import gzip; raw = gzip.decompress(raw)
        return raw.decode("cp932", errors="replace")
```

### 8.4 ページネーション戦略
全件取得は次のいずれか:
1. **`/all` を1回叩いてIDをすべて取得 → 各IDに対して `/la_syllabus`** を並列実行（推奨）
2. `/search` を `page=1..ceil(total/10)` で全ページ取得 → 各行から `lectureNo` を抽出

(1) の方が `/search` の同一ページ内重複行を気にせずに済む。

### 8.5 レート制限の観察
セッションなしで連続100リクエスト程度叩いても 429/503 は観測されず。  
ただし `loading_modal_body` 内に「履修登録期間中は処理に10分程度かかることがあります」とあるため、
3〜4月の履修登録ピーク時は重くなる可能性。常識的なバックオフ(指数 backoff, 並列度を低めに)を推奨。

### 8.6 既知の落とし穴
- `page=0` / `page=-1` で **HTTP 500** → 入力バリデーション必須
- `Accept: application/json` を投げても HTML が返る → JSON期待のフレームワークは使えない
- `condition.departmentNo` を複数指定しても1つしか有効にならない → 複数学部を一発で検索することは不可。複数学部はクライアント側で N 回叩いてマージ
- `sort` / `orderBy` 系は無視される → 並び替えはクライアント側で実施
- 「文学部」「工学部」など全学共通以外は **件数だけ返って中身は空** → CLI で『一致なし』と勘違いしないようUIで明示
- 学科分類 `condition.openSyllabusTitle` の値は文字列 (CP932 エンコード必須)
- レスポンスHTMLが `windows-31j` charset、`charset=Shift_JIS` と書かれてるバージョンもあるが同じ MS932

---

## 9. 観測したサーバ情報

- バックエンド: nginx 1.18.0 (Ubuntu) + JSP (`<div id="jsp_path">external/open_syllabus/la_syllabus.jsp</div>`)
- アプリ ID: `cserver=ku_ganymede`（複数台のうちの ganymede ノードへのスティッキー）
- ZK Framework っぽい命名 (`zk_logo_l.gif`, `zk_tab_back.gif` 等)
- Cookie は `JSESSIONID`, `SSESSIONID`, `cserver`。発行されるがクライアントから戻さなくても全機能OK
- 親システムは KULASIS (京都大学共通教務情報システム)。`open_syllabus` はそれの「学外公開」ビューに過ぎない

---

## 10. 参考: HARから抽出した実通信パターン

提供されたHARで観測されたURLは以下のとおり（重複・静的アセットは省略）:
```
GET /external/open_syllabus/top
GET /external/open_syllabus/top?display_lang=en
GET /external/open_syllabus/all
GET /external/open_syllabus/open_syllabus_titles?departmentNo=80
GET /external/open_syllabus/open_syllabus_titles?departmentNo=
GET /external/open_syllabus/search?condition.departmentNo=80&condition.weekSchedule[31]=true
    &condition.openSyllabusTitle=人文・社会科学科目群／芸術・文学・言語
    &condition.courseNumberingJugyokeitaiNo=2&condition.courseNumberingLanguageNo=1
    &condition.semesterNo=1&condition.courseNumberingLevelNo=1&condition.courseNumberingBunkaNo=1
    &condition.teacherName=&condition.keyword=&x=29&y=18
GET /external/open_syllabus/search?...&page=2
GET /external/open_syllabus/search?...&page=3
GET /external/open_syllabus/search?...&page=4
GET /external/open_syllabus/search?...&page=5
GET /external/open_syllabus/la_syllabus?lectureNo=63736
```

全リクエストは GET、リクエストボディなし、Cookie送信なし、CSRFトークンなし。

---

## 11. 検証用ファイル

実通信で取得したサンプルレスポンスは `out/` 配下に保存済み:

| ファイル | 内容 |
| --- | --- |
| `out/top_ja.html` | トップページ(日本語) |
| `out/top_en.html` | トップページ(英語) |
| `out/all.html` | 全件階層リスト(日本語, 2.1MB) |
| `out/all_en.html` | 全件階層リスト(英語, 2.4MB) |
| `out/titles_dept80.html` | dept=80 の学科分類フラグメント |
| `out/titles_dept1.html` | dept=1 の学科分類フラグメント |
| `out/search_wed1.html` | 水1限の検索結果1ページ目 |
| `out/search_en_p1.html` | 英語UI 検索結果1ページ目 |
| `out/la_63736.html` | 詳細(日本語): Basic Physical Chemistry |
| `out/la_63736_en.html` | 詳細(英語): 同上 |
| `out/la_62409.html` | 詳細: 朴沙羅 社会学I (日本語授業の例) |
| `out/la_61585.html` | 詳細: CATT Adam Alvah (英語授業の例) |
| `out/la_*.html` | 50件のサンプル詳細ページ (フィールド網羅検証用) |
