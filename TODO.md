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
- [ ] "Answer again" loop: re-attempt the same question after reading feedback
- [ ] Progress trend chart across rehearsals on the dashboard

## Coding mode

- [ ] PySpark coding tasks, AI-review only (skip Judge0 for this language; allow coding mode when Judge0 is down)
- [ ] SQL coding tasks with real execution via Judge0 (SQLite): add `sql` language, SQL test harness, SQL editor highlighting, `data/coding/sql/` banks
- [ ] Get Judge0 working under WSL (needs cgroup v1) — prerequisite for SQL execution

## Voice

- [ ] Realtime natural voice (streaming speech-to-text / text-to-speech pipeline)
- [ ] Optional: switch to Whisper large on the GPU for better accuracy

## Models

- [ ] Optional: Ollama as an offline backup interviewer model (7–8B fits alongside Whisper in 8 GB VRAM)

## Branding leftovers

- [ ] Favicon for Rehearse (browser currently gets a 404)
- [ ] README header and description for Rehearse
- [ ] Rename the database file from `grillkit.db` (needs a careful migration of existing data)

## From upstream GrillKit's roadmap

- [ ] Session-wide time limit (total interview duration)
- [ ] More question banks and categories
- [ ] Custom question banks; PWA / standalone frontend

## Done

- [x] Fix Docker startup so database migrations run
- [x] Enable NVIDIA GPU for Whisper (CUDA libraries in the image, GPU reservation in compose)
- [x] Rebrand UI to "Rehearse — By DS"
