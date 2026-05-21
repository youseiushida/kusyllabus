# kusyllabus — Agent Skill

This is the long-form skill manifest for the `kusyllabus` CLI. It teaches an
agent (Claude Code, Cursor, Codex, etc.) what the tool does, which commands
to reach for, and the gotchas baked into the upstream syllabus system.

* **Layer 1 (human help)**: `kusyllabus --help` and `kusyllabus <noun> --help`.
* **Layer 2 (machine surface)**: `kusyllabus agent-context` — versioned JSON
  describing every command, every flag, every enum, profile names, and
  feedback channels. Read this first when you need exact syntax.
* **Layer 3 (this file)**: workflows and judgement calls that don't fit into
  `--help` text.

If anything below contradicts `agent-context`, trust `agent-context` — it is
generated from the live command surface, this file is human-curated.

---

## What the tool does

Wraps the **Kyoto University open syllabus** (`https://www.k.kyoto-u.ac.jp/external/open_syllabus/`):

* Search by department, language, semester, day/period, keyword, instructor.
* Fetch individual syllabi (course outline, instructors, evaluation, etc.).
* Walk the full Department → Title → Syllabus tree.
* Bulk-download every syllabus to a local JSONL file.

The upstream system serves only Shift_JIS HTML and has **no JSON API**. The
CLI parses that HTML and gives you typed, JSON-friendly output. There is no
auth — every request is anonymous GET.

## Two endpoint families (important)

The upstream system exposes syllabi behind two paths. The CLI hides this
behind a single `syllabus get` command, but you have to know which kind a
lecture belongs to:

| Kind | When | How to fetch |
| --- | --- | --- |
| `open_syllabus` | Liberal-arts / general-education courses (departmentNo=80). ~3105 entries. | `kusyllabus syllabus get <lectureNo>` |
| `department_syllabus` | Faculty / graduate-school courses. ~8566 entries. | `kusyllabus syllabus get <lectureNo> --department <departmentNo>` |

Discover which kind a lecture is via `kusyllabus all leaves --json`: each
leaf has `kind` and (for `department_syllabus`) `department_no` already
attached.

Search (`kusyllabus search list`) only returns rows for the liberal-arts
pool. Searches against other departments report a non-zero `total` but
return an empty `rows` array — that is the upstream behaviour, not a bug.

## Cardinal workflows

### Workflow 1 — answer "what does this syllabus cover?"

When the user gives you a `lectureNo`:

```bash
# Default: human-friendly panel
kusyllabus syllabus get 63736

# Agent-shaped (JSON to stdout)
kusyllabus --json syllabus get 63736
# {"lecture_no":63736,"title":"Basic Physical Chemistry (thermodynamics)-E2", ...}
```

If you don't know whether it's a `department_syllabus`:

```bash
# Lookup once via `all leaves`, then fetch with the right --department.
kusyllabus --json all leaves --limit 0 | jq '.leaves[] | select(.lecture_no==26510)'
kusyllabus --json syllabus get 26510 --department 1
```

Returns `null` and exits with code `4` when `lectureNo` doesn't exist.

### Workflow 2 — search for matching lectures

```bash
# English-medium courses on Wednesday period 1
kusyllabus --json search list --language 2 --slot wed1 --limit 20

# Same, but stash a profile so future calls don't repeat the flags
kusyllabus profile save eng-wed --language 2 --slot-index 31 --force
kusyllabus --profile eng-wed search list --limit 20
```

`--slot` accepts `mon1`/`wed3`/`金2`/`水1` (Japanese & English short forms)
or the 2-digit XY shorthand (`31` = Wed period 1).

`--limit N` pages internally until N rows are collected, then truncates and
sets `truncated: true` in the JSON payload with a hint.

### Workflow 3 — explore by structure

```bash
# Walk the tree for one department
kusyllabus all tree --department 80

# Flatten to a leaf list (good for piping)
kusyllabus --json all leaves --department 80 --kind open --limit 10
```

### Workflow 4 — bulk download every syllabus

This is the long-running command. It registers a row in the jobs ledger
(`kusyllabus jobs list`) and writes one syllabus per JSONL line.

```bash
# All liberal-arts syllabi (3105) with conservative rate limit
kusyllabus syllabus fetch-all --out ./out/open.jsonl --kind open \
  --concurrency 8 --rps 5 --force --wait

# Check progress / history later
kusyllabus jobs list
kusyllabus jobs get <job-id>
```

For a quick smoke-test, pass `--limit 10` to stop after ten records.

`--wait` (the default) blocks until done. `--no-wait` registers the job and
returns immediately, but the actual fetch only runs if you keep the process
alive — there is no background daemon, so prefer `--wait` and Ctrl-C if you
want to abort.

### Workflow 5 — discover available filters

The CLI ships every master enum as a subcommand of `master`:

```bash
kusyllabus master list                   # lists category names
kusyllabus master departments            # human table
kusyllabus --json master departments     # machine-shaped
kusyllabus master bunka --value 32       # one row
kusyllabus titles list --department 80   # academic-area dropdown for dept 80
```

When the upstream changes, regenerate enums by re-reading `top` (the CLI
ships them bundled, but `kusyllabus agent-context` always reflects the
in-process values).

### Workflow 6 — deliver artefacts somewhere other than stdout

Every data-returning command takes `--deliver`:

```bash
# Atomic file write
kusyllabus search list --slot wed1 --limit 50 \
  --deliver=file:./out/wed1.json

# POST to a webhook (Content-Type: application/json)
kusyllabus syllabus get 63736 \
  --deliver=webhook:https://example.com/hook
```

Unknown schemes return a structured error naming the valid set, so you can
retry with the correct shape in one round-trip.

---

## Conventions the agent should rely on

* **`<noun> <verb>` everywhere**: `search list`, `syllabus get`, `all tree`,
  `profile save`, `jobs list`. No `info`, no `ls`, no `delete-no-confirm`.
* **`--json` toggles machine output** on every data command. Stdout is the
  payload; stderr is diagnostics; exit codes communicate failure class
  (`0` ok, `2` user-input error, `4` not found, `1` other).
* **`--force` for destructive ops** (`profile delete`, `jobs prune`,
  `syllabus fetch-all --force` to overwrite a file).
* **`--limit` to bound list responses**. Without it, a list command returns
  one upstream page (10 rows) — that is the bounded default.
* **`--profile NAME`** applies a saved bundle of search defaults. Precedence
  is flag > env > profile > built-in default.
* **`--lang ja|en`** chooses the UI language of the response (some fields,
  notably descriptions, switch translations entirely).

## Gotchas baked into the upstream

* **Pagination is 1-based and fixed at 10 rows per page.** `page=0` returns
  HTTP 500. The CLI rejects `page<=0` before sending.
* **There is no full-text search.** `--keyword` does a substring match in
  the upstream index, not a body search. If you need free-text matching
  against syllabus bodies, run `syllabus fetch-all` once and grep the JSONL.
* **No sort parameters work.** `sort`, `orderBy`, `order` are silently
  ignored upstream. If you need an order, sort client-side after fetching.
* **Search totals for non-liberal-arts departments are misleading.** For
  example `kusyllabus search count --department 16` (Engineering) reports
  ~600 results, but `search list` returns 0 rows — that pool's syllabi are
  available only via `kusyllabus syllabus get <lectureNo> --department 16`,
  with the `lectureNo` discovered via `kusyllabus all leaves --department 16`.
* **All content is CP932 (Shift_JIS).** The library handles encoding for
  you; you don't need to touch it. Strings emitted to stdout are UTF-8.

## When to fall back to the Python library directly

The CLI covers ~95% of common workflows. Drop into Python if you need:

* Streaming results out of a custom event loop instead of `--wait`.
* Custom retry behaviour or `httpx.AsyncClient` reuse (pass `http_client=`
  to `AsyncKuSyllabusClient(...)`).
* Programmatic profile or jobs-ledger manipulation beyond what
  `kusyllabus profile`/`jobs` exposes.

```python
import asyncio
from kusyllabus import AsyncKuSyllabusClient, SearchCondition, DayOfWeek

async def main():
    async with AsyncKuSyllabusClient() as ku:
        cond = SearchCondition(keyword="thermodynamics")
        cond.add_slot(DayOfWeek.WEDNESDAY, 1)
        result = await ku.search(cond, page=1)
        ...

asyncio.run(main())
```

## Reporting friction

If the CLI fails you in a way that wasted retries or token budget,
`kusyllabus feedback add "what was painful"` records the entry locally
(`state_dir/feedback.jsonl`). Setting `KUSYLLABUS_FEEDBACK_ENDPOINT=<url>`
also POSTs it upstream. Telling the maintainer is the single highest-signal
thing an agent can do after a friction event.

---

## Reference: command tree at a glance

```
kusyllabus
├── search
│   ├── list       --department, --language, --slot, --keyword, --limit, --profile, --deliver
│   └── count      lightweight count-only request
├── syllabus
│   ├── get        <lectureNo> [--department] [--lang]
│   └── fetch-all  --out <path> [--kind open|department|all] [--limit] [--concurrency] [--rps]
├── all
│   ├── tree       3-level Rich tree, optional --department / --kind filter
│   └── leaves     flat list of leaves
├── titles
│   └── list       --department
├── master
│   ├── list       names of every master enum
│   ├── departments / class-style / language / semester / level / day
│   └── bunka      [--value N]
├── profile
│   ├── save       <name> --department --keyword --slot-index ... [--force]
│   ├── list / show / delete --force
├── jobs
│   ├── list / get / prune --force
├── feedback
│   ├── add / list
└── agent-context  always-JSON machine description
```
