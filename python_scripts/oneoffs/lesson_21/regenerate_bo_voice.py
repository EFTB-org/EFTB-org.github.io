#!/usr/bin/env python3
"""Regenerate Lesson 21 Section 2 Bo lines by cloning Lesson 20 Bo's voice.

Uses existing Lesson 20 Bo speech as reference for local Chatterbox TTS.
Changes only the six lesson-21/conversation/Bo*.mp3 files, atomically.
"""
import json
import subprocess
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
AUDIO = ROOT / "frontend/static/audio"
FOLDER = AUDIO / "lesson-21/conversation"
PREVIOUS = AUDIO / "lesson-20/conversation"

def main():
    import torch
    import torchaudio
    from chatterbox.tts import ChatterboxTTS

    entries = json.loads((FOLDER / "conversation.json").read_text())
    bo = [entry for entry in entries if entry["speaker"] == "Bo"]
    if len(bo) != 6:
        raise RuntimeError(f"Expected six Bo lines, found {len(bo)}")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    with tempfile.TemporaryDirectory(dir=FOLDER) as tmp:
        tmp = Path(tmp)
        reference = tmp / "bo_reference.wav"
        sources = [PREVIOUS / f"bo{i}.mp3" for i in (2, 3, 5)]
        args = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
        for source in sources:
            args.extend(["-i", str(source)])
        args += ["-filter_complex", "[0:a][1:a][2:a]concat=n=3:v=0:a=1[out]",
                 "-map", "[out]", "-ac", "1", "-ar", "24000", str(reference)]
        subprocess.run(args, check=True)
        print(f"Loading Chatterbox on {device}, conditioning on Lesson 20 Bo", flush=True)
        model = ChatterboxTTS.from_pretrained(device=device)
        model.prepare_conditionals(str(reference))
        for i, entry in enumerate(bo, 1):
            output = tmp / "generated.wav"
            target = tmp / "generated.mp3"
            wave = model.generate(entry["text"])
            torchaudio.save(str(output), wave.cpu(), model.sr)
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                            "-i", str(output), "-codec:a", "libmp3lame", "-q:a",
                            "3", str(target)], check=True)
            duration = subprocess.check_output(["ffprobe", "-v", "error",
                "-show_entries", "format=duration", "-of", "csv=p=0", str(target)],
                text=True).strip()
            if float(duration) <= 0.25:
                raise RuntimeError(f"Bad generated duration: {entry['audio']}")
            target.replace(FOLDER / entry["audio"])
            output.unlink()
            print(f"Bo {i}/6: {entry['audio']} ({duration}s)", flush=True)
            del wave
            if device == "cuda":
                torch.cuda.empty_cache()

if __name__ == "__main__":
    main()
