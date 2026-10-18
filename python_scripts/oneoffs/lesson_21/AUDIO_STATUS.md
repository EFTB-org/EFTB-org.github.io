# Lesson 21 — audio production notes (2026-10-18)

The material comes from `raw_lessons/LESSON-21`. The conversation contains 12
supplied human recordings: Bo1–Bo6 and Na1–Na6, converted from M4A
to MP3 without altering the spoken content.
Their transcript is copied from the source lesson.

**Current status (2026-10-18): All 82 English clips have been regenerated
using Chatterbox and the `python_scripts/kore_audio_prompt.wav` reference,
matching Lesson 20, on the NVIDIA RTX 4060 GPU.** No temporary English
Gemini or gTTS fallback clips remain.

During the initial build, GPU access and the model cache were unavailable,
so Gemini Kore and gTTS were used as temporary fallbacks. After the GPU
returned and the Chatterbox model was downloaded, all English clips were
replaced.

All audio and the Hugo website pass mechanical validation. A human listening
review is recommended before publication, especially for prices, Vietnamese
loanwords, and the -teen/-ty pronunciation pairs.

To regenerate Chatterbox audio again if corrections are needed, run:

```bash
cd /mnt/data/code/EFTB-org.github.io
python_scripts/.venv/bin/python python_scripts/oneoffs/lesson_21/build_lesson21.py \
  --stage english --replace-english all
python_scripts/.venv/bin/python python_scripts/oneoffs/lesson_21/build_lesson21.py \
  --stage validate
cd frontend && pnpm build
```

The `--replace-english all` option overwrites **only** English Lesson 21
files. It does not overwrite Vietnamese recordings, context, or the source
transcripts. All default generation stages skip existing valid audio.
