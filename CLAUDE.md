# CLAUDE.md — Rehearse

Guidance for Claude (and any AI coding agent) working in this repository. Read this first, then
[ARCHITECTURE.md](ARCHITECTURE.md) before touching application code.

---

## 1. What this project is

**Rehearse (by DS)** — a voice-first AI mock interviewer for **Senior/Staff Data Engineering**
interviews. The interviewer asks questions aloud, the candidate answers by speaking, the LLM scores
each answer (1–5), asks up to 2 follow-ups, and produces section + session feedback. Each mock
session is a "Rehearsal".

- **Fork of [GrillKit](https://github.com/GrillKit/grillkit)** (Apache-2.0). Upstream is watched and
  relevant changes are **ported by hand**. → Keep every change small, focused and localized so
  upstream diffs stay easy to merge. Do not do sweeping refactors, mass renames or reformatting of
  untouched files.
- **Naming:** the product is "Rehearse" in all user-facing text (UI, README, new docs). Internal
  identifiers that still say `grillkit` (package name in `pyproject.toml`, `grillkit.db`, `.idea`
  module, copyright headers, ARCHITECTURE.md title) are **intentionally left alone** for now —
  renaming them is a tracked backlog item that needs a data migration. Do not rename them ad hoc.
- **Backlog:** [TODO.md](TODO.md) is the source of truth for planned work. Tick items off there
  when they land and move them to **Done**.
- Repo: `github.com/itsds/rehearse` · default branch `main` · work happens on feature branches
  (e.g. `update-files`, `add-questions`) merged via PR.

## 2. Tech stack

| Concern | Choice |
|---|---|
| Language | Python **3.12** (`requires-python >=3.12`) |
| Package manager | **uv** (`uv.lock` committed; use `uv sync`, `uv run`, `uv add`) — never pip-install into the project |
| Web | **FastAPI** (HTTP + WebSocket), **Uvicorn** |
| Templates / UI | Server-rendered **Jinja2** (`templates/`) + vanilla JS (`static/js/`) + one stylesheet (`static/css/styles.css`); Monaco editor for coding |
| Persistence | **SQLAlchemy 2.0** on **SQLite** (WAL mode), **Alembic** migrations run on startup |
| Validation / DTOs | **Pydantic v2** |
| LLM | Any **OpenAI-compatible** API via the `openai` SDK (`app/ai/openai_compatible.py`) — only one adapter type exists |
| Speech-to-text | **faster-whisper** (offline; CUDA in Docker) |
| Text-to-speech | **piper-tts** (offline, CPU ONNX) for reading questions aloud |
| Code execution | **Judge0 CE** (optional `coding` compose profile) |
| Quality | **ruff** (lint + format), **mypy --strict**, **pytest** + pytest-asyncio (`asyncio_mode = "auto"`) |

## 3. Local environment (owner's machine)

- Windows laptop; Docker Engine runs **inside WSL2 Ubuntu 22.04** (not Docker Desktop), used from a
  zsh / PyCharm terminal. Repo on disk: `D:\repos\rehearse`.
- GPU: **NVIDIA RTX 4070 Laptop, 8 GB VRAM**. NVIDIA Container Toolkit is installed in WSL; the
  image ships cuBLAS/cuDNN wheels and `LD_LIBRARY_PATH` points at them; compose reserves the GPU.
- Whisper **medium** runs on the GPU (`WHISPER_DEVICE=cuda`, `WHISPER_COMPUTE_TYPE=float16`).
- Interviewer model: **Groq `openai/gpt-oss-120b`** (free tier) configured on `/config`.
  `llama-3.3-70b-versatile` is not available on this key. Respect free-tier rate limits — avoid
  designs that fan out many LLM calls per answer.
- Piper voice installed: `en_US-lessac-medium`.
- **Judge0 is not running** (images kept, containers stopped). It needs cgroup v1 under WSL, which
  is not set up. Treat coding mode as optional/disabled unless a task is explicitly about it.
- VRAM budget matters: Whisper medium + any future local model (e.g. Ollama 7–8B) must fit in 8 GB.

## 4. Commands

### Run

```bash
# Normal way (production-like, GPU Whisper)
docker compose up --build              # http://localhost:8000
docker compose up -d --build app       # detached, app only
docker compose logs -f app

# With Judge0 for coding mode (needs cgroup v1 on the host)
docker compose --profile coding up --build

# Local dev without Docker (CPU Whisper unless CUDA libs present)
uv sync --extra dev
uv run uvicorn app.main:app --reload
```

If bind-mounted `./data` is not writable (UID mismatch): `PUID=$(id -u) PGID=$(id -g) docker compose up --build`.

### Quality gates (same as CI — `.github/workflows/ci.yml`)

```bash
uv run ruff check --fix .
uv run ruff format .
uv run mypy .
uv run pytest
uv run pytest tests/theory/use_cases/ -q        # one package
uv run pytest -k "known_questions" -q            # by keyword
```

All four must pass before a change is considered done. CI runs `uv sync --frozen --extra dev`, so if
you add a dependency, update `uv.lock` with `uv add <pkg>` (or `uv add --optional dev <pkg>`).

### Database / migrations

```bash
uv run alembic revision -m "short_description"   # new revision in alembic/versions/
uv run alembic upgrade head                      # also runs automatically on startup
```

- Migrations run at startup via `run_migrations()` (`app/shared/infrastructure/database.py`) — both
  from the FastAPI `lifespan` and from `docker-entrypoint.sh`.
- Revision filenames follow `YYYYMMDD_NNNN_snake_description.py` (next number after the latest in
  `alembic/versions/`, currently `0011`). Write both `upgrade()` and `downgrade()`.
- **Never delete or reset `data/db/grillkit.db` on the owner's machine** — it holds real rehearsal
  history. Use an isolated DB (tests already do) for experiments.

## 5. Repository layout

```
app/
  main.py               create_app(), router registration, lifespan (migrations + speech runtime)
  templating.py         shared Jinja2Templates + static_version() cache-busting
  ai/                   provider adapters: AIProvider protocol, OpenAI-compatible client,
                        ProviderFactory, LLM catalog types, faster-whisper transcriber
  interview/            SESSION ORCHESTRATOR: setup, dashboard, Interview shell aggregate,
                        phase order, completion, results hub, known questions
  theory/               THEORY SECTION: question planning, WS/audio answer submit, timer,
                        TheoryEvaluator (scoring + follow-ups), review page
  coding/               CODING SECTION: YAML tasks, Monaco UI, Judge0 runs, WS submit, evaluator
  speech/               Whisper model status/download, dictation WebSocket
  question_voice/       Piper TTS status/download, question audio generation
  platform/             /config page: AppConfig + ConfigService (data/config.json),
                        LLM catalog (data/llm_models.json), SpeechRuntimeCoordinator
  shared/               cross-cutting: paths, YAML loaders (questions.py, coding.py), locales,
                        structured LLM JSON parsing, evaluation DTOs, timers,
                        infrastructure/ (db, ORM models, UoW, gateways: judge0, whisper, piper, tts cache)
alembic/                schema + data migrations
data/                   runtime data (see §8) — mounted into the container
templates/              Jinja2 pages and HTMX-style fragments
static/js, static/css   front-end behaviour per page (dictation.js, interview_voice.js, …)
tests/                  mirrors app/ one-to-one; helpers/ seeds, fakes.py, conftest.py
deploy/judge0.conf      Judge0 config for the coding profile
```

Every feature package uses the same internal layering:

```
<feature>/
  api/            FastAPI routes, WebSocket session + protocol mapping, deps.py, errors.py
  use_cases/      workflow classes (constructed with a UnitOfWork) — the write path
  queries/        read-only page/view-model builders and loaders
  domain/         aggregates, value objects, exceptions, evaluators, prompts; domain/rules/ = pure helpers
  repositories/   ORM access + mappers (ORM ↔ domain ↔ read DTO)
  schemas/        Pydantic read models and WebSocket wire messages
  support/        small helpers, event mappers, background prefetch, etc.
```

> ARCHITECTURE.md has some drift: it lists `platform/support/llm_catalog.py`, `speech_runtime.py`
> etc., but they actually live in `app/platform/domain/`. Trust the filesystem; fix the doc when you
> touch that area.

## 6. Architecture rules (must follow)

1. **Layer direction:** `api/` → `use_cases/` / `queries/` → `domain/` + `repositories/` → `shared/infrastructure/`.
   Domain code does no I/O. `domain/rules/` is pure functions only.
2. **No ORM objects on the wire.** API handlers and templates receive Pydantic read models
   (`InterviewRead`, `TheoryTaskRead`, `CodingTaskRead`, …). Mapping lives in `repositories/mappers.py`.
3. **One Unit of Work.** Transactions go through the app-wide `InterviewUnitOfWork`
   (`app/interview/repositories/uow.py`; repos: `uow.interviews`, `uow.theory_sections`,
   `uow.coding_sections`, `uow.code_run_attempts`, `uow.known_questions`). Use cases receive the UoW in
   their constructor; routes obtain it via `Depends` in `*/api/deps.py`.
4. **Aggregates are immutable-style:** load with `get_aggregate`, derive a new state with
   `with_…()` methods, persist with `save_aggregate`.
5. **SQLite concurrency:** never hold a write transaction open across an LLM call or other slow I/O.
   Commit first, then call the model, then open a fresh UoW to persist the result. Don't nest a new
   `InterviewUnitOfWork` inside an active one (→ `database is locked`); pass the caller's UoW instead.
   Background work (feedback prefetch, last follow-up scoring) opens its own UoW after the foreground commit.
6. **Interview shell vs sections:** `interview/` owns the session (mode, phase order, completion,
   results). `theory/` and `coding/` own their tasks. The shell does not store section tasks; read
   models compose them at read time.
7. **LLM output is structured.** Evaluators send a JSON schema derived from a Pydantic model
   (`theory/domain/evaluator_models.py`: `AnswerEvaluation`, `FollowUpEvaluation`) and parse with
   helpers in `shared/structured_evaluation.py` / `shared/json_parser.py`. New LLM features
   (e.g. the Staff-level rubric / Hire–No-Hire "Reflector") should follow this exact pattern: Pydantic
   model → schema in prompt → tolerant parse → validated DTO. Prompts live next to the evaluator in
   `domain/*_prompts.py` and must be **locale-aware** via `language_instruction()`.
8. **Answers are often spoken.** Prompts must keep the `EVALUATION_SUBSTANCE_NOTE` behaviour: don't
   penalise speech-to-text typos, misheard terms or grammar — judge substance. Delivery metrics
   (pace, fillers, pauses) are a separate, planned concern and must not leak into the technical score.
9. **Config lives in files, not env:** user settings in `data/config.json` (`AppConfig` /
   `ConfigService`), model catalog in `data/llm_models.json` (`LLMCatalogService`). Env vars are only
   for infrastructure (`DATABASE_URL`, `HF_TOKEN`, `WHISPER_*`, `CODING_ENABLED`, `JUDGE0_*`,
   `CODING_MAX_RUNS_PER_TASK`). Paths come from `app/shared/paths.py` — never hard-code them.
10. **Coding mode must degrade gracefully** when Judge0 is down (`coding/support/coding_availability.py`,
    `CODING_ENABLED`). Theory-only flows must never depend on Judge0.

## 7. Code conventions

- **Every new Python file** starts with:
  ```python
  # Copyright 2026 GrillKit Contributors
  # SPDX-License-Identifier: Apache-2.0
  """One-line module docstring."""
  ```
  (Apache-2.0 attribution to the upstream project is required — keep it. Modified files keep their header.)
- Full type hints; `mypy --strict` passes (tests are exempt). Prefer `collections.abc` types,
  `X | None`, `Final`, `Protocol` for ports (see `AIProvider`, `SpeechTranscriber`, `TtsEngine`).
- ruff: line length 88, double quotes, isort with `force-sort-within-sections` and `app` as first-party.
- Async for I/O paths (LLM, Whisper, WebSockets); keep domain logic sync and pure.
- Domain errors are typed exceptions in `domain/exceptions.py`, mapped to payloads in `api/errors.py`.
- Owner comes from a Java background and is learning Python idioms — when introducing a non-obvious
  Python pattern, a short comment explaining *why* is welcome. Don't over-comment the obvious.
- Commits: **Conventional Commits** (`feat(theory): …`, `fix(speech): …`, `docs: …`, `test(...)`).
- User-visible changes go under `## [Unreleased]` in [CHANGELOG.md](CHANGELOG.md)
  (`### Added / Changed / Fixed / Removed`). Versions are date-based `YYYY.M.d`.
- Update README / ARCHITECTURE / TODO when behaviour, layout or backlog status changes.

## 8. Data directory and question banks

```
data/
  questions/{track}/{level}/{category}.yaml   theory banks  (ship in image AND visible via ./data mount)
  coding/{track}/{level}/{category}.yaml      coding tasks  (via ./data mount)
  questions_map.yaml                          metadata only — loader discovers banks from the filesystem
  config.json, llm_models.json                user config (gitignored — never commit, contain API keys)
  db/grillkit.db (+ -wal/-shm)                SQLite (gitignored)
  whisper-models/, piper-voices/, tts-cache/, .cache/   downloaded models + caches (gitignored)
```

Terminology: **track** = bank slug (`kafka`, `system-design`), **level** = `junior|middle|senior`,
**category** = YAML file within a track/level. Existing tracks: python, database, system-design,
kafka, rabbitmq, docker, kubernetes, observability, airflow.

### Theory bank schema

```yaml
category: "PySpark Performance"
track: "pyspark"
level: "senior"
description: "Shuffles, skew, AQE, partitioning, memory"
questions:
  - id: "pysp-perf-s-001"        # unique, stable — known_questions + history reference it
    type: "knowledge"
    difficulty: 4                # 1–5 within the level
    tags: ["skew", "salting", "aqe"]
    question:
      text:
        en: "A join stage has one task running 40x longer than the rest. Walk me through diagnosis and fixes."
      code: null                 # optional snippet, never localized, never read aloud
    expected_points:             # optional but recommended: rubric checklist passed to TheoryEvaluator
      - "Identify skew via Spark UI task-duration / shuffle-read distribution"
      - "AQE skew join handling and its limits"
      - "Salting the hot key; broadcast when one side is small"
```

**Minimal valid question** — only `id`, `type`, `difficulty` and `question.text` are required;
`text` may be a plain string (treated as `en`); `tags`, `code`, `expected_points` are optional:

```yaml
category: PySpark Performance
track: pyspark
level: senior
questions:
  - id: pysp-001
    type: knowledge
    difficulty: 3
    question:
      text: Explain data skew in Spark and how you would fix it.
```

Rules for banks:
- A new track appears in the UI just by creating `data/questions/<track>/<level>/<category>.yaml`
  and restarting the app. Display labels come from `_TRACK_LABELS` in
  `app/interview/domain/rules/bank_selection.py` (fallback: slug title-cased, so add entries such as
  `"pyspark": "PySpark"`, `"aws": "AWS"` for proper casing).
- File name = category slug (`pyspark-performance.yaml`); `track`/`level` must match the directory.
- **IDs are permanent.** Never renumber or reuse an ID — past rehearsals and "known questions" point to them.
- `en` text is required; other locales optional (`en`, `ru`, `fr`, `es`, `de` supported).
- Write questions the way a Staff-level interviewer would **say** them — they are read aloud by Piper,
  so avoid tables, long code, or markdown in `text`; put code in `question.code`.
- Follow-ups are generated by the AI; static `follow_ups` keys are ignored by the loader.
- `expected_points` **is** loaded (`app/shared/questions.py`) and fed to the evaluator as a scoring
  checklist — CONTRIBUTING.md wrongly calls it a legacy/ignored key. Write 3–6 crisp points per DE question,
  phrased as **reasoning** ("explains that salting spreads a hot key across N partitions at the cost of
  replicating the other side") rather than bare keywords ("salting"), so the evaluator rewards
  understanding, not name-dropping. Without points the evaluator gets `(none)` and judges generically
  (tends to be lenient and less consistent).
- Validate YAML after editing:
  `uv run python -c "import yaml,glob;[yaml.safe_load(open(f,encoding='utf-8')) for f in glob.glob('data/**/*.yaml',recursive=True)]"`
  and run `uv run pytest tests/shared/test_questions.py tests/shared/test_coding.py`.
- Bank text indexes are `lru_cache`d per process — **restart the app container** after editing banks.
- Planned DE tracks (see TODO.md): PySpark, Snowflake, pipeline design, data modelling, AWS,
  plus behavioural and Staff+ leadership banks. Adding a new track is content-only — no code change.

### Coding task schema

Lives under `data/coding/`; uses `tasks:` (not `questions:`) with a `coding:` block
(`language`, `evaluation_mode: ai|tests`, `starter_code`, `entrypoint`, `public_tests`,
`hidden_tests`, limits) and `expected_points`. Full example in [CONTRIBUTING.md](CONTRIBUTING.md).
Never put `type: coding` rows in `data/questions/`.

## 9. Key flows (where to look)

| Flow | Entry point |
|---|---|
| Configure model / locale / voice | `platform/api/config.py` → `platform/domain/config.py`, `llm_catalog.py` |
| Create a rehearsal | `POST /setup` → `interview/use_cases/create_session.py` → `theory/use_cases/create_section.py` (+ coding) |
| Theory answer (typed) | `WS /interview/{id}/theory/ws` → `theory/api/ws_session.py` → `theory/use_cases/submit_answer.py` → `TheoryEvaluator` |
| Theory answer (spoken WAV) | `POST /interview/{id}/theory/audio-answer` → `theory/api/audio_answer.py` (NDJSON stream) |
| Dictation | `WS /interview/{id}/dictation` → `speech/use_cases/dictation.py` → faster-whisper (single final transcript) |
| Question read aloud | `GET /interview/{id}/question-audio` → `question_voice/` → Piper + `tts_cache.py`; UI `static/js/interview_voice.js` |
| Phase switch theory ↔ coding | `interview/use_cases/advance_phase.py` (`SessionPhaseOrchestrator`) |
| Completion + overall feedback | `interview/use_cases/complete_session.py`, `interview/domain/session_evaluation.py`, `evaluation_aggregator.py` |
| Results / review pages | `interview/api/results.py`, `*/queries/review_page.py`, `templates/session_results.html` |
| Dashboard | `GET /` → `interview/queries/dashboard.py`, `templates/dashboard.html` |
| Progress trend | `GET /` card + `GET /progress` → `interview/queries/progress.py`, `domain/rules/progress_trend.py`, `templates/_trend_chart.html` |
| Export transcript | `GET /interview/{id}/theory/export.md` → `theory/support/transcript_export.py` |

### How theory answers are scored today

1. Spoken answers are transcribed by Whisper (the Groq model has no audio input), then
   `TheoryEvaluator.evaluate_answer` sends the LLM: the question (+ optional code), the
   `expected_points` checklist (explicitly labelled "not candidate content"), and the answer.
2. Prompts live in `app/theory/domain/evaluator_prompts.py`. The 1–5 scale: 5 complete with examples
   and edge cases · 4 solid, minor gaps · 3 basic, lacks depth · 2 significant gaps · 1 wrong/empty/off-topic.
   `EVALUATION_SUBSTANCE_NOTE` tells it to ignore typos, misheard terms and grammar.
3. Score ≤ 3 → follow-up question; follow-ups scored on their own 1–5; another follow-up only if ≤ 2;
   max depth `TheoryEvaluator.MAX_FOLLOW_UP_DEPTH` (2).
4. Every round counts (each out of 5) in `score_breakdown` (keys `qid`, `qid:r1`, …); timer expiry = 0.
   Section/session narratives (strengths, topics to review) are written by the LLM at completion;
   the dashboard shows the sum of section scores. Scores are not shown live, only on results pages.
5. Known gaps (deferred, see TODO.md): no Staff-level bar, no Hire/No-Hire verdict, no delivery
   assessment, and the prompt doesn't state that correctness outranks checklist coverage.

## 10. Testing

- `tests/` mirrors `app/` — put a new test next to the matching package path.
- Fixtures (`tests/conftest.py`): `client` (TestClient with speech runtime mocked), `isolated_db`
  (in-memory SQLite, StaticPool), `fake_ai_provider`, `override_ws_ai_provider`.
- `tests/fakes.py` → `FakeProvider` + canned evaluation JSON. **Never call a real LLM, Whisper,
  Piper, Hugging Face or Judge0 in tests** — use fakes (`tests/helpers/fake_judge0.py`,
  `tests/helpers/transcription.py`).
- Seeds for complex states live flat in `tests/helpers/` (`interview_seed.py`,
  `completed_session_seed.py`, `theory_seed.py`, …). Reuse them rather than building rows by hand.
- New behaviour ⇒ new tests; bug fix ⇒ regression test.

## 11. Docker notes and gotchas

- `docker-entrypoint.sh` runs as root only to `chown` `/app/data`, then drops to `PUID:PGID` via
  `gosu` and runs migrations before `uvicorn`. Keep that order if you edit it.
- The image copies `app/`, `data/questions`, `templates/`, `static/`, `alembic/`. Python/template
  changes need `docker compose up --build`; YAML bank changes only need a container restart
  (they're read through the `./data` mount).
- `.dockerignore` excludes `tests`, `*.md` (except README), `data/db`, `data/config.json`.
- Healthcheck hits `http://127.0.0.1:8000/`.
- Speech models and download progress are **per process** — run a single uvicorn worker.
- Whisper on GPU needs the CUDA wheels in the image + compose `deploy.resources.reservations.devices`;
  don't remove either. On a machine without a GPU set `WHISPER_DEVICE=cpu WHISPER_COMPUTE_TYPE=int8`.
- Groq/OpenAI-compatible base URL is configured in the UI, not in `.env`.

## 12. Things not to do

- Don't commit `data/config.json`, `data/llm_models.json`, `.env`, DB files, or downloaded models.
- Don't reset/delete the real SQLite DB or drop tables outside an Alembic migration.
- Don't rename `grillkit` internals or the DB file outside the dedicated backlog task.
- Don't add a second LLM SDK — extend `AIProvider` / `ProviderFactory` instead.
- Don't introduce a JS framework or build step for the front end; it is Jinja2 + vanilla JS by design
  (a standalone/PWA frontend is a separate future item).
- Don't make theory mode depend on Judge0, network downloads at request time, or a GPU.
- Don't strip the Apache-2.0 headers, LICENSE or NOTICE.
- Don't add GPL/AGPL dependencies or non-commercial models/voices without flagging it in TODO.md (§14).
- Don't fold InterviewMentor's scorecard/rubric into Rehearse or the second-opinion flow unless the
  owner asks — that was explicitly deferred.

## 13. Roadmap context (from TODO.md)

Priority themes, roughly in order: DE + leadership question banks → Staff-level rubric with
Hire/No-Hire verdict ("Reflector", Pydantic structured output) → delivery metrics from Whisper word
timestamps (pace, fillers, pauses) → "answer again" loop → PySpark (AI-review only) and SQL (Judge0/SQLite) coding tasks → realtime streaming voice → optional
Ollama fallback model → branding leftovers (favicon, DB rename).

**Next planned session:** design the owner's second-opinion Claude skill (see §14). The
"Export transcript" it builds on is done.

When implementing any of these, check TODO.md for the exact scope, keep the change self-contained
in the relevant feature package, add tests, update CHANGELOG `[Unreleased]`, and tick the item.

## 14. Decisions log

**2026-10-04 — interview prep system and evaluation**
- Prep uses three tools, kept separate:
  1. **Rehearse** — spoken, scored short Q&A with follow-ups and progress history.
  2. **Claude second opinion** — the Rehearse transcript is graded blind (no Rehearse scores shown)
     by Claude for a Staff-level comparison. For now via the owner's own prompt; later via the
     owner's own dedicated **second-opinion skill** in the Claude app.
  3. **InterviewMentor** (github.com/PrepLabsAI/InterviewMentor, MIT) — 44 interviewer skills for long
     design rounds; installed as a Claude Code plugin in WSL and selectively uploaded to the Claude app.
     Not integrated into Rehearse.
- Target workflow: **Export transcript** in Rehearse → run the second-opinion skill in the Claude app.
  Export = questions, follow-ups and answers as Markdown, **scores and feedback excluded** (avoid anchoring).
- InterviewMentor's Novice/Intermediate/Expert scorecard is **not** used for the second opinion;
  revisit only if it proves valuable in practice.
- Evaluator-prompt tightening (correctness over coverage, cap at 2 for a wrong core claim, Staff bar)
  is deferred to a future release — tracked in TODO.md.
- Later (Reflector): Claude could become an in-app judge via Anthropic's OpenAI-compatible endpoint
  (`https://api.anthropic.com/v1/`), which fits the existing `openai-compatible` adapter; needs a paid
  API key (separate from a Claude subscription).

**Licensing notes (relevant before going private / commercial)**
- Apache-2.0 (GrillKit) allows private use, modification and commercial sale without publishing source;
  obligations: keep `LICENSE`, `NOTICE`, copyright headers; mark modified files; don't use the GrillKit
  name as branding.
- `piper-tts` (current releases) is **GPL-3.0-or-later** — fine for personal use; distributing the app
  (downloads/images) would bring GPL obligations. Replace before commercial distribution.
- The installed Piper **Lessac** voice is trained on a research-only dataset (Blizzard licence) —
  not usable commercially.
- A GitHub fork cannot be made private; this repo's history suggests it is standalone — confirm before
  changing visibility. Not legal advice; get a full dependency licence review before selling.
