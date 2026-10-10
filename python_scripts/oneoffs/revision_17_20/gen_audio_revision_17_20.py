#!/usr/bin/env python3
"""Build Revision 17–20 audio, matching Lesson 20's TTS choices.

English headings, focus, prompts: Chatterbox with kore_audio_prompt.wav.
Vietnamese context: Gemini multilingual TTS (Kore).
Bo/Na conversation: preserve supplied human M4A recordings, convert to MP3.

Run from anywhere:
    uv run python oneoffs/revision_17_20/gen_audio_revision_17_20.py
    uv run python oneoffs/revision_17_20/gen_audio_revision_17_20.py --stage recordings
    uv run python oneoffs/revision_17_20/gen_audio_revision_17_20.py --stage recordings --recordings-zip "raw_lessons/REVISION-17-20/REVISION 17-20-20261010T090342Z-1-001.zip" --replace-recordings Na2 Na3 Na4 Na5 Na6

Outputs already present are left unchanged unless explicitly selected for replacement.
The latest ZIP is used by default. Failed generation returns nonzero.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON_DIR = SCRIPT_DIR.parents[1]
ROOT = PYTHON_DIR.parent
RAW_DIR = PYTHON_DIR / "raw_lessons" / "REVISION-17-20"
OUTPUT = ROOT / "frontend" / "static" / "audio" / "revision-17-20"
PROMPT_AUDIO = PYTHON_DIR / "kore_audio_prompt.wav"

# Verbatim text/translations from REVISION LESSONS 17–20.docx.md.
DIALOGUE = [
    ("Bo", "Na ơi, tớ có thể mua đồ dùng học tập ở đâu nhỉ?", "Na, where can I find school supplies?"),
    ("Na", "Tớ biết một chỗ khá ổn. Chỗ đó nhỏ nhưng tiện lắm.", "I know a good place. It’s small, but convenient."),
    ("Bo", "Ở đó có bán nhiều đồ không?", "Are there many things there?"),
    ("Na", "Có bút, vở với nhiều đồ dùng học tập khác nữa.", "There are pens, notebooks, and other school supplies."),
    ("Bo", "Wow, tuyệt cú mèo!", "Wow, that’s great!"),
    ("Na", "Cậu thử đến cửa hàng gần công viên xem.", "You can go to the store near the park."),
    ("Bo", "À mà, cửa hàng ở đâu vậy Na?", "Where’s the store?"),
    ("Na", "Có một cửa hàng trên đường Trường Sa, đối diện công viên.", "There’s one on Truong Sa Street, across from the park."),
    ("Bo", "Từ đây đi tới đó thế nào nhỉ?", "How do I get there from here?"),
    ("Na", "Cậu đi thẳng, rồi quẹo trái vào đường Trường Sa.", "Go straight, then take a left onto Truong Sa Street."),
    ("Bo", "Cậu nói quẹo trái đúng không?", "Did you say take a left?"),
    ("Na", "Ừ, đúng rồi. Cửa hàng ở bên phải của cậu.", "Yes, that’s right. The store is on your right."),
    ("Bo", "Tuyệt vời, cảm ơn Na nhé.", "Great. Thanks, Na."),
]

CONTEXT = (
    "Bo đang muốn tìm một chỗ để mua đồ dùng học tập và hỏi Na xem có chỗ nào phù hợp không. "
    "Na giới thiệu một cửa hàng gần công viên, nhưng Bo chưa biết cửa hàng nằm ở đâu và làm thế nào "
    "để đến đó. Hãy cùng lắng nghe xem Na sẽ chỉ đường cho Bo như thế nào nhé!"
)

ENGLISH_AUDIO = [
    ("Revision: Lessons 17 to 20", "title.mp3"),
    (
        "Lesson Focus. Lesson 17: What's Your Place Like? Asking about a place. Describing a place. "
        "Lesson 18: Where Can I Get a Lamp? Asking for suggestions. Giving suggestions. "
        "Lesson 19: Where's The Mall? Asking about locations. Describing locations. "
        "Lesson 20: Take A Left. Giving directions. Asking for clarification.",
        "focus/eng/audio.mp3",
    ),
    ("1. Think and speak", "titles/think_and_speak.mp3"),
    # Spell out the section number: Chatterbox misread "2." as "seven".
    ("Two. Application", "titles/application.mp3"),
    (
        "Choose one of the following topics. Work in pairs and create your own conversation. "
        "Take turns speaking and try to use the structures you have learned.",
        "application/instruction.mp3",
    ),
    ("Topic 1: Let's Go Shopping!", "application/topic_1.mp3"),
    (
        "Imagine you want to buy something. Take turns asking for suggestions, choosing a store, "
        "asking about its location, and giving directions. Ask for clarification when needed.",
        "application/topic_1_desc.mp3",
    ),
    ("Your conversation should include:", "application/includes.mp3"),
    ("Asking for suggestions and giving suggestions.", "application/topic_1_include_1.mp3"),
    ("Asking about and describing locations.", "application/topic_1_include_2.mp3"),
    ("Giving directions and asking for clarification.", "application/topic_1_include_3.mp3"),
    ("Example prompts:", "application/example_prompts.mp3"),
    ("Where can I find a lamp?", "application/topic_1_ex_1.mp3"),
    ("You can go to ...", "application/topic_1_ex_2.mp3"),
    ("Where's the store?", "application/topic_1_ex_3.mp3"),
    ("How do I get there?", "application/topic_1_ex_4.mp3"),
    ("Did you say turn left?", "application/topic_1_ex_5.mp3"),
    ("Topic 2: Let's Visit a Friend!", "application/topic_2.mp3"),
    (
        "Imagine you are inviting a friend to your home for the first time. Take turns asking "
        "about and describing your homes, talking about nearby places, and giving directions "
        "to help your partner find your home. Ask for clarification when needed.",
        "application/topic_2_desc.mp3",
    ),
    ("Asking about and describing a place.", "application/topic_2_include_1.mp3"),
    ("Asking about and describing locations.", "application/topic_2_include_2.mp3"),
    ("Giving directions and asking for clarification.", "application/topic_2_include_3.mp3"),
    ("What's your place like?", "application/topic_2_ex_1.mp3"),
    ("How many rooms are there?", "application/topic_2_ex_2.mp3"),
    ("Where's the nearest park?", "application/topic_2_ex_3.mp3"),
    ("How do I get to your house?", "application/topic_2_ex_4.mp3"),
    ("Did you say turn left?", "application/topic_2_ex_5.mp3"),
]


def has_audio(path: Path) -> bool:
    """Check that the file contains playable audio, not just an MP3 header."""
    if not path.is_file() or path.stat().st_size < 1000:
        return False
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True,
    )
    try:
        return result.returncode == 0 and float(result.stdout.strip()) > 0.25
    except ValueError:
        return False


def dialogue_json() -> None:
    counts = {"Bo": 0, "Na": 0}
    lines = []
    for speaker, text, translation in DIALOGUE:
        counts[speaker] += 1
        lines.append({
            "type": "dialogue", "speaker": speaker, "text": text,
            "en": translation, "audio": f"{speaker}{counts[speaker]}.mp3",
        })
    target = OUTPUT / "think-and-speak" / "conversation.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    # Deterministic regeneration: the transcript is always derived from the raw material.
    target.write_text(json.dumps(lines, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Transcript: {target} ({len(lines)} lines)", flush=True)


def ffmpeg_convert(input_path: str, output_path: Path) -> None:
    """Encode atomically. Never leave a partial output that will be mistaken as complete."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output_path.parent) as tmp:
        temp_out = Path(tmp) / "encoded.mp3"
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
        cmd += ["-i", input_path]
        cmd += ["-codec:a", "libmp3lame", "-q:a", "3", str(temp_out)]
        proc = subprocess.run(cmd, capture_output=True)
        if proc.returncode != 0 or not has_audio(temp_out):
            raise RuntimeError(f"FFmpeg failed for {output_path}: {proc.stderr.decode(errors='replace')[-1000:]}")
        temp_out.replace(output_path)


def convert_recordings(archive_path: Path | None = None, replace_names: set[str] | None = None) -> None:
    zips = sorted(RAW_DIR.glob("*.zip"))
    if not zips and archive_path is None:
        raise RuntimeError(f"No recordings ZIP found in {RAW_DIR}")
    archive_path = archive_path or zips[-1]
    if not archive_path.is_file():
        raise FileNotFoundError(archive_path)
    expected = {f"Bo{i}" for i in range(1, 8)} | {f"Na{i}" for i in range(1, 7)}
    replace_names = replace_names or set()
    if unexpected := replace_names - expected:
        raise ValueError(f"Unknown recording names: {sorted(unexpected)}")
    print(f"Recordings source: {archive_path}", flush=True)
    with zipfile.ZipFile(archive_path) as archive:
        matches = {}
        for info in archive.infolist():
            if info.is_dir() or not info.filename.lower().endswith(".m4a"):
                continue
            # Handles e.g. Na4_Hiệu ứng AI_1.m4a as Na4.
            match = re.match(r"^(Bo|Na)(\d+)(?:_|\.)", Path(info.filename).name)
            if not match:
                raise RuntimeError(f"Unrecognized recording filename: {info.filename}")
            key = f"{match.group(1)}{match.group(2)}"
            if key in matches:
                raise RuntimeError(f"Duplicate recording for {key}")
            matches[key] = info.filename
        if set(matches) != expected:
            raise RuntimeError(f"Recordings mismatch: missing={sorted(expected-set(matches))}, extra={sorted(set(matches)-expected)}")
        for name in sorted(expected):
            target = OUTPUT / "think-and-speak" / f"{name}.mp3"
            if has_audio(target) and name not in replace_names:
                print(f"Existing human recording: {target.name}", flush=True)
                continue
            print(f"Converting supplied human recording: {name}"
                  f"{' (replacing)' if name in replace_names else ''}", flush=True)
            # M4A/MP4 can require seeking to the moov atom; a pipe may yield an
            # empty MP3 even when FFmpeg exits successfully (observed for Na2).
            with tempfile.TemporaryDirectory() as tmp:
                original = Path(tmp) / "original.m4a"
                original.write_bytes(archive.read(matches[name]))
                ffmpeg_convert(str(original), target)


def split_speech(text: str, limit: int = 65) -> list[str]:
    """Keep TTS utterances short enough for constrained GPU VRAM.

    Preserve sentence boundaries where possible and split long passages at
    spaces (rather than cutting words). Each chunk uses the same voice prompt.
    """
    sentences = re.split(r"(?<=[.!?])\s+", " ".join(text.split()))
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        words = sentence.split()
        for word in words:
            if len(current) + len(word) + 1 > limit and current:
                chunks.append(current)
                current = ""
            current = f"{current} {word}".strip()
    if current:
        chunks.append(current)
    return chunks


def generate_english(device: str = "cuda", replace_paths: set[str] | None = None) -> None:
    import torch
    import torchaudio
    from chatterbox.tts import ChatterboxTTS

    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable; rerun with --device cpu to use the same Chatterbox voice on CPU")
    if not PROMPT_AUDIO.is_file():
        raise FileNotFoundError(PROMPT_AUDIO)
    replace_paths = replace_paths or set()
    known_paths = {path for _, path in ENGLISH_AUDIO}
    if unexpected := replace_paths - known_paths:
        raise ValueError(f"Unknown English audio paths: {sorted(unexpected)}")
    model = None
    for idx, (text, relative) in enumerate(ENGLISH_AUDIO, 1):
        target = OUTPUT / relative
        if has_audio(target) and relative not in replace_paths:
            print(f"[{idx}/{len(ENGLISH_AUDIO)}] Existing Chatterbox audio: {relative}", flush=True)
            continue
        if model is None:
            print(f"Loading Chatterbox on {device}", flush=True)
            model = ChatterboxTTS.from_pretrained(device=device)
            # Cache the reference voice: identical voice to Lesson 20, without
            # repeatedly embedding the same WAV for every short audio chunk.
            model.prepare_conditionals(str(PROMPT_AUDIO))
        parts = split_speech(text)
        print(f"[{idx}/{len(ENGLISH_AUDIO)}] Generating Chatterbox: {relative} ({len(parts)} chunks)", flush=True)
        with tempfile.TemporaryDirectory() as tmp:
            wav = Path(tmp) / "voice.wav"
            segments = []
            for chunk in parts:
                audio = model.generate(chunk)
                segments.append(audio.cpu())
                del audio
                if device == "cuda":
                    torch.cuda.empty_cache()
                if len(parts) > 1:
                    segments.append(torch.zeros((segments[-1].shape[0], int(0.14 * model.sr))))
            combined = torch.cat(segments, dim=1)
            torchaudio.save(str(wav), combined, model.sr)
            del combined, segments
            ffmpeg_convert(str(wav), target)
        print(f"Generated {relative}", flush=True)


def generate_context() -> None:
    target = OUTPUT / "think-and-speak" / "context.mp3"
    if has_audio(target):
        print("Existing Gemini context audio", flush=True)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(PYTHON_DIR / "tts" / "gemini_multi.py"), "--voice", "Kore", CONTEXT, str(target)]
    print("Generating Vietnamese context with Gemini Kore", flush=True)
    try:
        proc = subprocess.run(cmd, cwd=PYTHON_DIR, check=False)
        if proc.returncode != 0 or not has_audio(target):
            raise RuntimeError(f"Gemini context generation failed with exit code {proc.returncode}")
    except Exception:
        target.unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("all", "recordings", "english", "context"), default="all")
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda", help="Chatterbox device; use CPU if other applications occupy GPU VRAM")
    parser.add_argument("--recordings-zip", type=Path, help="Specific ZIP with Bo/Na recordings (default: latest ZIP by filename)")
    parser.add_argument("--replace-recordings", nargs="+", default=[], metavar="NAME", help="Replace only these existing MP3s, e.g. Na2 Na3 Na4")
    parser.add_argument("--replace-english", nargs="+", default=[], metavar="PATH", help="Regenerate selected English MP3s even if they already exist")
    args = parser.parse_args()
    failures = []
    if args.stage in ("all", "recordings"):
        try:
            dialogue_json()
            convert_recordings(args.recordings_zip, set(args.replace_recordings))
        except Exception as exc:
            failures.append(f"recordings: {exc}")
    if args.stage in ("all", "english"):
        try:
            generate_english(args.device, set(args.replace_english))
        except Exception as exc:
            failures.append(f"English TTS: {exc}")
    if args.stage in ("all", "context"):
        try:
            generate_context()
        except Exception as exc:
            failures.append(f"Vietnamese context: {exc}")
    for failure in failures:
        print(f"ERROR {failure}", file=sys.stderr, flush=True)
    print(f"Completed stage={args.stage}; failures={len(failures)}", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
