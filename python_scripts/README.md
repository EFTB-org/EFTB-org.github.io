# Python Scripts for EFTB-org.github.io

This directory contains Python scripts used to process, generate, and manage audio content and related resources for the English For The Blind (EFTB) website.

## Scripts Overview

-
- `add_cleaned_row.py` — Adds cleaned data rows to lesson files.
- `hello.py` — Test script for basic Python functionality.
- `lession1.py`, `lession2.py` — Scripts for processing specific lessons.
- `louder.py` — Increases the volume of audio files.
- `make_audios.py` — Batch generates audio files for lessons.
- `make_conversation.py` — Creates conversation audio files.
- `mp3_to_wav.py` — Converts MP3 files to WAV format.
- `pad_audio.py` — Adds padding (silence) to audio files.
- `wav_to_mp3.py` — Converts WAV files to MP3 format.
- `generate_eng_audio.py` — Uses Groq TTS to synthesize English audio (WAV/MP3) from text.
- `generate_vie_audio.py` — Uses Google Translate (gTTS) to synthesize Vietnamese audio (MP3/WAV) from text.

Other folders:

- `processed_lessions/` — Output directory for processed lesson files.
- `raw_lessions/` — Input directory for raw lesson files.
- `sound_effects/` — Sound effects used in lessons.

## Requirements

- Python 3.12 or higher (see `pyproject.toml`)
- Recommended: Create a virtual environment
- Install dependencies using your chosen tool (e.g. `uv` or `pip`).

## Usage

Run scripts from this directory. For example:

```bash
python3 make_audios.py
```

Some scripts may require input/output directories or specific arguments. Check the script source for details.

### Generate English audio with Groq

Set your API key and run the script:

```bash
export GROQ_API_KEY=your_api_key_here
python3 generate_eng_audio.py "Hello, world" ./output/ --voice Fritz-PlayAI --model playai-tts --format wav
```

Notes:

- Defaults: model `playai-tts`, voice `Fritz-PlayAI`, format `wav`.
- Pass a file path or a directory path for `output_path`. When a directory is given, the file name is derived from the text.

### Generate Vietnamese audio with gTTS

Run with `uv` from this folder:

```bash
uv run generate_vie_audio.py "Xin chào, thế giới" ./output/ --format mp3
```

Notes:

- Defaults: language `vi`, format `mp3`. Use `--format wav` to export WAV (requires ffmpeg via pydub).
- Pass a file path or a directory path for `output_path`. When a directory is given, the file name is derived from the text.

## Notes

- Audio files are used by the main Hugo site for accessible English lessons.
- Some scripts may require additional Python packages (e.g., `pydub`, `ffmpeg`).
- See comments in each script for more information.

## Contributing

Contributions and improvements are welcome. Please document any new scripts you add.
