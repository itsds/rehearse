# Rehearse
### by Durga Shanker  
*Mirror yourself. Rehearse until it shows.*

A voice-first AI mock interviewer for Senior/Staff Data Engineering interviews — practice out loud, get scored feedback with follow-up questions, watch yourself on camera, and track your progress rehearsal by rehearsal. (A Staff-level Hire/No-Hire verdict is on the roadmap.)

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-yellow.svg)](https://opensource.org/licenses/Apache-2.0)
[![Version](https://img.shields.io/badge/version-2026.8.9-blue.svg)](CHANGELOG.md)

Open-source AI technical interview trainer. Practice **theory Q&A**, **live coding**, or **both in one session** from curated YAML banks — with structured scoring, follow-ups, optional voice, and a local results history. Bring your own LLM (cloud or local).

[Why Rehearse](#why-rehearse-not-just-chatgpt) · [Quick start](#quick-start) · [Changelog](CHANGELOG.md) · [Architecture](ARCHITECTURE.md)

## Why Rehearse (not just ChatGPT)

A general chat assistant is flexible, but it does not run an **interview** for you.

| What you need | ChatGPT-style chat | Rehearse |
|---------------|-------------------|----------|
| Curated technical questions | You prompt each time | Built-in **tracks** (Python, Kafka, System Design, …), **levels**, and **topics** |
| Interview flow | Free-form thread | Fixed session: theory Q&A and/or coding tasks, up to **2 AI follow-ups** per item, **1–5 scoring**, session summary |
| Live coding practice | Paste code in chat | **Monaco editor**, **Run** against public tests, **Submit** for hidden tests + AI review (needs Judge0) |
| Practice history | Scattered chats | **Dashboard** with past sessions; open **results** and per-section **review** pages after completion |
| Progress over time | None | **Progress trend** on the dashboard and a per-topic **Progress** page (average first-answer score per rehearsal) |
| How you come across | Text only | **Camera self-view** while answering; opt-in **recording** with per-answer replay on the review page |
| Second opinion | Copy/paste by hand | **Export transcript** — questions and your answers as Markdown, scores left out, ready for a blind grade by another AI |
| Skip what you already know | You repeat the same prompts | **Known questions** — mark bank items during practice; optionally exclude them when starting a new session |
| Time pressure | None | Optional **per-round timer** on theory and coding (expired round → 0, move on) |
| Voice practice | Depends on product | Offline **Whisper** dictation; optional **Piper** question audio; **audio answers** when your model supports it |
| Where data lives | Vendor cloud | **Self-hosted**: SQLite + `data/` on your machine; use **Ollama**, vLLM, or any OpenAI-compatible API |

**Structured practice** — You pick tracks, difficulty, and topics; Rehearse builds a question plan and keeps score across the whole session, not a single ad-hoc prompt.

**Privacy and control** — Run via Docker on your laptop or server. API keys and interview history stay under `./data` (gitignored). No account or subscription required beyond your LLM provider (if you use a cloud model).

## Screenshots & demo

**Demo video** — full flow from setup to scored feedback

Soon

**Dashboard**
<img width="1920" height="1200" alt="Снимок экрана от 2026-08-09 17-17-15" src="https://github.com/user-attachments/assets/c70f2f39-34a2-49dd-8719-d570685663a2" />


**Setup**
<img width="1920" height="1200" alt="Снимок экрана от 2026-08-09 17-06-56" src="https://github.com/user-attachments/assets/1781833c-fce8-4878-b191-f565e2b44eb4" />


**Theory**
<img width="1920" height="1200" alt="Снимок экрана от 2026-08-09 17-13-49" src="https://github.com/user-attachments/assets/be536299-aa80-4d6d-aff5-df25a330e281" />


**Coding**
<img width="1920" height="1200" alt="Снимок экрана от 2026-08-09 17-14-44" src="https://github.com/user-attachments/assets/7954a520-bcf1-45ee-acf1-615e6d797b4f" />


**Evaluation**
<img width="1920" height="1200" alt="Снимок экрана от 2026-08-09 17-14-52" src="https://github.com/user-attachments/assets/8b19a34c-9865-49ef-928d-dbe2a7a6d62a" />


## Features

### Session modes

Pick one mode on **New interview** (`/setup`):

| Mode | What you practice |
|------|-------------------|
| **Theory only** | Technical Q&A from `data/questions/` — type, dictate, or record answers |
| **Coding only** | Programming tasks from `data/coding/` — edit, Run, Submit |
| **Theory then coding** | Q&A first, then coding panel when theory finishes |
| **Coding then theory** | Coding first, then theory |

Coding modes need a running [Judge0](https://github.com/judge0/judge0) instance (see **Coding sessions** below).

### Practice tools

- **Theory** — WebSocket Q&A, AI scoring 1–5, up to 2 follow-ups per question
- **Coding** — Monaco editor, Run (`POST /coding/run`) on public tests, Submit (`WS /coding/ws`) with hidden tests and AI feedback
- **Question banks** — Python, Database/SQL, System Design, Kafka, RabbitMQ, Docker, Kubernetes, Observability, Airflow, and more (junior / middle / senior where applicable)
- **Timer** — optional per-round limit on theory and coding; expired rounds score 0 and the session moves on
- **Voice** — offline Whisper dictation; optional Piper TTS to read theory questions aloud
- **Audio answers** — record a WAV theory answer when your model supports audio input and Whisper is ready
- **Results hub** — after you finish, `/interview/{id}/results` shows overall evaluation and links to **theory** and **coding** review pages with full chat/code history
- **Known questions** — mark theory or coding bank items as **I know this** during an interview or on review pages; optionally exclude them on **New interview** setup; manage the list at `/known-questions/manage`
- **Dashboard** — recent sessions on the home page (completed sessions link to results)
- **Setup** — model catalog on `/config`, interview locale, Whisper/Piper downloads from the UI
- **Theme** — light theme by default with a **dark mode toggle** (sun/moon) in the navbar; your choice is remembered and follows your system preference on first visit
- **Deployment** — Docker Compose on port 8000 with `./data` volume for config, DB, and models

### Progress and review

- **Progress trend** — a dashboard card plots your **average first-answer score** (0–5) for each of your last 20 completed rehearsals. Only the first answer to each question counts (follow-ups are counted, not averaged in); a timed-out first answer counts as 0. Hover for details, click a point to open that rehearsal's results.
- **Progress by topic** (`/progress`, in the top nav) — one chart per track (levels merged, so Kafka junior and senior both count as Kafka) plus a per-category table, weakest first. In a mixed session each question counts toward the overall trend **and** toward its own track. Computed from your existing history — nothing extra is stored.
- **Export transcript** — on a completed session's theory review page, **Export transcript** downloads `rehearsal-<id>-theory.md`: the questions, follow-ups and your answers. Rehearse's scores, feedback and rubric points are deliberately left out so another AI can grade it **blind**.

### Camera: self-view and recording

- **Self-view** — a **Self-view** panel on the theory and coding interview pages shows your camera while you answer. Untick **Mirror view** to see the un-mirrored image an interviewer gets. The preview never leaves your browser.
- **Preview size** — **Minimize** (preview hidden, camera and recording keep running), **Normal** (docked in the sidebar), **Maximize** (larger floating preview in the top-right corner; it can cover part of the chat) or **Pop out** (a browser picture-in-picture window you can move and resize, e.g. onto a second monitor; always un-mirrored).
- **Per session** — camera on/off, recording and size are remembered for each rehearsal: a **new rehearsal starts with the camera off**; refreshing or coming back to the same rehearsal (including the theory → coding switch) restores what you had.
- **Record this rehearsal** (theory page, opt-in, off for a new rehearsal) — records camera + voice **one clip per answer round**, from the moment the question appears until you submit. The first time you tick it in a rehearsal, a 10-second **calibration** asks you to look at the camera lens, then at the centre of the screen (used by external gaze analysis). After a refresh, recording resumes without recalibrating; the clip of the answer you were in the middle of restarts.
- **Recorded size** — videos are always recorded at the camera's full 1280×720, un-mirrored (what an interviewer sees), no matter how big or small the preview is.
- **Replay** — each recorded answer gets a video player on the theory review page, next to your answer. **Delete recordings** removes all of a session's videos.
- **Where recordings live** — only on your machine, under `data/recordings/<interview_id>/`: `q01-r0.webm` (question 1, main round), `q01-r1.webm` (its first follow-up), `calibration.webm`, and a `manifest.json` (questions, your answer text, clip timings, calibration segments — **no scores or feedback**) that other local tools can read. Expect roughly 5–10 MB per minute of video.
- **Browser requirement** — browsers allow the camera only on `localhost` or HTTPS, so open Rehearse at `http://localhost:8000`.

## Quick start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/)
- API key for a cloud provider, **or** a local OpenAI-compatible server (Ollama, vLLM, …)

### Run with Docker

```bash
git clone https://github.com/itsds/rehearse.git
cd rehearse
docker compose up --build
```

Open [http://localhost:8000](http://localhost:8000).

Optional **question voice** (Piper TTS, same `app` container):

1. Run `docker compose up` (or `uv run uvicorn app.main:app` for development).
2. Open `/config`, enable **Read questions aloud**, save.
3. On the Configuration page, use **Download question voice** when prompted (~60 MB per locale voice from Hugging Face).
4. Start an interview — questions can play aloud; WAV cache lives under `data/tts-cache/v2/{locale}/`.

`./data` on the host holds SQLite, `config.json`, `llm_models.json`, Whisper/Piper models, TTS cache, and your interview recordings (`data/recordings/`, only if you record). Question banks, templates, and static files ship in the image.

If bind-mounted `data/` is not writable (Linux UID mismatch):

```bash
PUID=$(id -u) PGID=$(id -g) docker compose up --build
```

**Coding sessions** (Monaco + code execution) require [Judge0 CE](https://github.com/judge0/judge0). Start the optional `coding` profile:

```bash
docker compose --profile coding up --build
```

Judge0 listens on port `2358` inside the Compose network (`JUDGE0_URL=http://judge0-server:2358` for the `app` service). For local development without Docker, run Judge0 separately and point `JUDGE0_URL` at `http://localhost:2358`.

On some Linux hosts Judge0 needs **cgroup v1** (`systemd.unified_cgroup_hierarchy=0` in GRUB). Set `CODING_ENABLED=false` to hide coding modes when Judge0 is unavailable.

### First-time flow

1. **Configuration** (`/config`) — add one or more OpenAI-compatible models to the catalog, select an interview model, set interview locale; test connection, then save. Download Whisper (and optionally a Piper voice) from the same page if you want voice features.
2. **New interview** (`/setup`) — pick a **session mode** (theory only, coding only, or combined). Choose tracks, levels, topics, how many questions/tasks, optional per-round timers, and whether to **exclude known questions**. Coding modes require Judge0 (see **Coding sessions** above).
3. **Practice** (`/interview/{id}`) — answer theory questions in the chat (type, dictate, or record audio). Optionally switch on **Camera on** to watch yourself, and tick **Record this rehearsal** to save a video of each answer. On coding phases, use the editor: **Run** to check public tests, **Submit** when ready. Combined sessions switch panels automatically when a section ends (or use **Continue to Coding**). End the interview from the sidebar at any time.
4. **Review** (`/interview/{id}/results`) — after completion, read the overall evaluation, then open **Theory** or **Coding** review for full conversation history, scores, and feedback. On the theory review, replay recorded answers and use **Export transcript** for a blind second opinion.
5. **Track progress** — the dashboard's **Progress trend** card and the **Progress** page show how your first-answer scores move over time, overall and per topic.

Without saved provider config, `/setup` redirects to `/config`.

### Local development

For contributors: see [CONTRIBUTING.md](CONTRIBUTING.md). Quick run:

```bash
uv sync --extra dev
uv run uvicorn app.main:app --reload
```

Same first-time flow at [http://127.0.0.1:8000](http://127.0.0.1:8000).

## Configuration (essentials)

Any **OpenAI-compatible** HTTP API works:

| Provider | Example base URL |
|----------|------------------|
| OpenAI | `https://api.openai.com/v1` |
| Ollama | `http://localhost:11434/v1` |
| vLLM / others | your endpoint + `/v1` |

On `/config`:

- **Add model to catalog** — display name, base URL, model name, optional API key (a stable catalog id is generated automatically from the display name); enable **Accepts audio input** only if the model supports multimodal audio (and download Whisper for transcription).
- **Interview model** — pick from the catalog, **Test Connection**, save.
- **Locale** — language for AI feedback and speech (stored in `data/config.json`, gitignored).
- **Whisper** — choose size (`small`, `medium`, `large`), download from the UI for dictation and audio answers.
- **Read questions aloud** — enable Piper, download a voice (~60 MB).

Do not commit `data/config.json`, `data/llm_models.json`, or API keys.

Optional environment variables (full list in [ARCHITECTURE.md](ARCHITECTURE.md#persistence--configuration)):

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | SQLAlchemy URL (default: SQLite under `data/db/`) |
| `HF_TOKEN` | Hugging Face token for faster Whisper/Piper downloads |
| `WHISPER_DEVICE` | `cpu` or `cuda` |
| `WHISPER_COMPUTE_TYPE` | `int8` or `float16` |
| `CODING_ENABLED` | Enable coding session modes (default `true`; requires healthy Judge0) |
| `JUDGE0_URL` | Judge0 API base URL (default `http://localhost:2358`) |
| `JUDGE0_AUTH_TOKEN` | Optional Judge0 `X-Auth-Token` header |
| `CODING_MAX_RUNS_PER_TASK` | Max Run attempts per coding task (default `20`) |

## Roadmap

The full backlog lives in [TODO.md](TODO.md). Highlights:

**Next**

- Separate local **video-review app** (its own repo) that reads `data/recordings/`: eye contact and look-aways (MediaPipe, with the calibration clip), framing and lighting, rough body-language numbers, and a timeline of moments to watch — runs on CPU, no LLM needed
- **Delivery metrics** from Whisper word timestamps: time to first word, long pauses, speaking pace, filler words — kept separate from the technical score
- Data Engineering question banks (PySpark, Snowflake, pipeline design, data modelling, AWS) and Staff+ leadership banks
- Staff-level rubric with a **Hire / No-Hire** verdict

**Later**

- "Answer again" loop, PySpark and SQL coding tasks, realtime streaming voice
- Session-wide time limit, custom question banks, PWA / standalone frontend

## For developers

| Document | Contents |
|----------|----------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Feature modules, routes, data flows, persistence, test layout |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Dev setup, quality checks, question/coding YAML guidelines |
| [CHANGELOG.md](CHANGELOG.md) | Release history |

## Security

Report vulnerabilities as described in [SECURITY.md](SECURITY.md). Do not open public issues for security problems.

## License

[Apache License 2.0](LICENSE) (see also [NOTICE](NOTICE))

> Based on [GrillKit](https://github.com/GrillKit/grillkit), licensed under Apache 2.0.
