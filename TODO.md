# Rehearse — Backlog

Future work for **Rehearse** (by DS), a voice-first AI mock interviewer for Senior/Staff Data Engineering interviews.
Based on [GrillKit](https://github.com/GrillKit/grillkit) (Apache 2.0).

Tick items off as they land. Keep each change small and focused so upstream GrillKit changes stay easy to bring in by hand.

## Question banks (content only — no code changes)

- [ ] DE theory banks in `data/questions/`: PySpark, Snowflake, pipeline design, data modelling, AWS
- [ ] Behavioural and leadership banks (Staff+ leadership question set)

## Evaluation and feedback

- [ ] Staff-level rubric with a Hire / No-Hire verdict (the "Reflector") — LLM-as-judge with Pydantic structured output
- [ ] Delivery metrics: speaking pace, filler words, long pauses (Whisper word timestamps)
- [ ] Tighten the evaluator prompt (`app/theory/domain/evaluator_prompts.py`): correctness and reasoning over checklist coverage; a wrong core claim caps the score at 2; naming a concept without explaining it earns no credit; checklist is guidance, a different valid approach can score 5; judge against a Staff-level bar when no checklist exists. Write `expected_points` as reasoning, not keywords
- [ ] "Answer again" loop: re-attempt the same question after reading feedback

## Coding mode

- [ ] PySpark coding tasks, AI-review only (skip Judge0 for this language; allow coding mode when Judge0 is down)
- [ ] SQL coding tasks with real execution via Judge0 (SQLite): add `sql` language, SQL test harness, SQL editor highlighting, `data/coding/sql/` banks
- [ ] Get Judge0 working under WSL (needs cgroup v1) — prerequisite for SQL execution

## Voice

- [ ] Realtime natural voice (streaming speech-to-text / text-to-speech pipeline)
- [ ] Optional: switch to Whisper large on the GPU for better accuracy

## Camera and video

Order agreed 2026-10-04: self-view → recording → separate review app → delivery metrics (see Evaluation and feedback).

- [ ] Recording on the coding page (Phase 2 covers theory rounds only)
- [ ] Add Whisper word timings to `manifest.json` once delivery metrics exist (new optional fields; manifest stays version 1)
- [ ] Separate local video-review app (own repo, not part of Rehearse): MediaPipe eye contact / look-aways, framing and lighting, rough body-language numbers, timeline of "moments to watch"; reads `data/recordings/` read-only, no LLM required

## Models

- [ ] Optional: Ollama as an offline backup interviewer model (7–8B fits alongside Whisper in 8 GB VRAM)

## Branding leftovers

- [ ] Favicon for Rehearse (browser currently gets a 404)
- [ ] README header and description for Rehearse
- [ ] Rename the database file from `grillkit.db` (needs a careful migration of existing data)

## Before going private / monetizing (later)

- [ ] Make the GitHub repo private (history suggests a standalone repo, not a GitHub fork — confirm there is no "forked from" label first; GitHub forks can't be made private)
- [ ] Licence clean-up: keep Apache-2.0 `LICENSE`/`NOTICE`/headers, mark modified files; replace `piper-tts` (GPL-3.0-or-later) and the Lessac voice (dataset licence is research-only) before any commercial use; review all dependency and voice/model licences

## From upstream GrillKit's roadmap

- [ ] Session-wide time limit (total interview duration)
- [ ] More question banks and categories
- [ ] Custom question banks; PWA / standalone frontend

## Done

- [x] Fix Docker startup so database migrations run
- [x] Enable NVIDIA GPU for Whisper (CUDA libraries in the image, GPU reservation in compose)
- [x] Rebrand UI to "Rehearse — By DS"
- [x] "Export transcript" button on the theory review page — downloads questions, follow-ups and my answers as Markdown, with Rehearse's scores and feedback left out, ready to paste into another AI for a blind second-opinion grade
- [x] Second-opinion skill for the Claude app (`rehearse-second-opinion`, created in Claude chat): grades an exported transcript blind at a Staff-level bar
- [x] Camera self-view on interview pages (Phase 1): local preview only, mirror toggle; on/off and size (minimize / normal / maximize / pop out) remembered per interview session
- [x] Record and replay theory answers (Phase 2): opt-in per visit, one clip per round, 10 s gaze calibration, `data/recordings/<interview_id>/` + `manifest.json` v1 (no scores/feedback), replay + delete on the theory review page
- [x] Progress trend chart across rehearsals on the dashboard, plus a per-topic `/progress` page (average first-answer score per rehearsal)
