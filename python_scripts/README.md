# Python Scripts for EFTB-org.github.io

This directory contains Python scripts used to process, generate, and manage audio content and related resources for the English For The Blind (EFTB) website.

## Scripts Overview

- `add_cleaned_row.py` — Adds cleaned data rows to lesson files.
- `hello.py` — Test script for basic Python functionality.
- `lession1.py`, `lession2.py` — Scripts for processing specific lessons.
- `louder.py` — Increases the volume of audio files.
- `make_audios.py` — Batch generates audio files for lessons.
- `make_conversation.py` — Creates conversation audio files.
- `mp3_to_wav.py` — Converts MP3 files to WAV format.
- `pad_audio.py` — Adds padding (silence) to audio files.
- `wav_to_mp3.py` — Converts WAV files to MP3 format.

Other folders:
- `processed_lessions/` — Output directory for processed lesson files.
- `raw_lessions/` — Input directory for raw lesson files.
- `sound_effects/` — Sound effects used in lessons.

## Requirements

- Python 3.8 or higher
- Recommended: Create a virtual environment
- Install dependencies (if any):

```
pip install -r requirements.txt
```

## Usage

Run scripts from this directory. For example:

```
python3 make_audios.py
```

Some scripts may require input/output directories or specific arguments. Check the script source for details.

## Notes
- Audio files are used by the main Hugo site for accessible English lessons.
- Some scripts may require additional Python packages (e.g., `pydub`, `ffmpeg`).
- See comments in each script for more information.

## Contributing
Contributions and improvements are welcome. Please document any new scripts you add.
