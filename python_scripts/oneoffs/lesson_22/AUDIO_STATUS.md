# Lesson 22 — production notes (2026-11-01)

Source: `python_scripts/raw_lessons/LESSON-22/LESSON 22 WILL YOU TAKE $20_.docx.md`.

- Page: `frontend/content/docs/topic_6/lesson-22.md` (Topic 6: Shopping).
- 11 human Vietnamese dialogue recordings (Bo1–Bo5 and Na1–Na6) converted from the source ZIP with FFmpeg. The source uses names `N1_2.m4a`–`N6_2.m4a` for Na.
- 80 English TTS clips generated with local Chatterbox on CUDA. Bo's five English Section 2 conversation clips use the existing Lesson 20 Bo recordings as the voice reference. Other English clips, including Na's six lines, use `python_scripts/kore_audio_prompt.wav`.
- 30 Vietnamese vocabulary / translation clips generated with gTTS. The Vietnamese context also uses gTTS.
- 122 MP3 files total, plus two conversation JSON files and a generation jobs JSON.
- All generated page audio references exist. `pnpm build` succeeds.

A **human listening review remains necessary** before publication. Pay special attention to amounts such as $20, $30, 100,000 dong, 60,000 dong, 80,000 dong, and 70,000 dong, and verify that the voices sound natural and distinguishable.

Regeneration from the repository root:

```bash
python3 python_scripts/oneoffs/lesson_22/build_lesson22.py
python3 python_scripts/oneoffs/lesson_22/build_lesson22.py --recordings
HF_HUB_OFFLINE=1 python_scripts/.venv/bin/python python_scripts/oneoffs/lesson_22/generate_audio.py english
HF_HUB_OFFLINE=1 python_scripts/.venv/bin/python python_scripts/oneoffs/lesson_22/generate_audio.py bo
python_scripts/.venv/bin/python python_scripts/oneoffs/lesson_22/generate_audio.py vietnamese
cd frontend && pnpm build
```

Audio generation skips existing valid MP3s. Do not delete those files unless regeneration is intended.
