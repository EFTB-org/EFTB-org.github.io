#!/usr/bin/env python3
"""
CLI: Generate Vietnamese TTS audio using Google Translate (gTTS).

Backend:
- gTTS (no API key required). Produces MP3 by default; WAV supported via conversion.

Usage:
        uv run generate_vie_audio.py <text> <output_path> [--format FORMAT] [--lang vi] [--slow]

Notes:
- Default language: vi (Vietnamese)
- Default output format: mp3. Use --format wav to export WAV (requires ffmpeg via pydub).
- The script prints the final saved audio file path to stdout on success.

Exit codes:
    0 = success
    2 = generation/conversion or write error
    3 = invalid arguments
"""

import argparse
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Optional, Literal

from gtts import gTTS

try:
    # pydub is optional, only needed for WAV conversion
    from pydub import AudioSegment  # type: ignore
except Exception:  # pragma: no cover - optional at runtime
    AudioSegment = None  # type: ignore


DEFAULT_LANG = "vi"
DEFAULT_FORMAT = "mp3"  # "mp3" or "wav"

RespFormat = Literal["mp3", "wav"]


def _latinize(text: str) -> str:
    """Convert Vietnamese text to ASCII: remove diacritics and map special letters.

    - Uses NFKD normalization to strip accents.
    - Maps Vietnamese 'đ'/'Đ' to 'd'/'D'.
    """
    if not text:
        return ""
    # Map Vietnamese-specific letters before stripping combining marks
    text = text.replace("đ", "d").replace("Đ", "D")
    # Decompose and remove combining diacritics
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    # Encode to ASCII ignoring remaining non-ascii, then decode back
    return stripped.encode("ascii", "ignore").decode("ascii")


def slugify_filename(stem: str) -> str:
    base = _latinize(stem).strip().lower()
    base = re.sub(r"\s+", "_", base)
    base = re.sub(r"[^a-z0-9_\-]+", "", base)
    return base or "audio"


def _ext_for_format(fmt: str) -> str:
    f = (fmt or "").lower()
    return ".wav" if f == "wav" else ".mp3"


def ensure_output_path(output: str, text: str, default_ext: str) -> Path:
    p = Path(output)
    if p.exists() and p.is_dir():
        return p / f"{slugify_filename(text)}{default_ext}"
    if str(output).endswith((os.sep, "/")):
        Path(output).mkdir(parents=True, exist_ok=True)
        return Path(output) / f"{slugify_filename(text)}{default_ext}"
    if p.suffix == "":
        p = p.with_suffix(default_ext)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _normalize_response_format(fmt: str) -> RespFormat:
    f = (fmt or "").lower()
    return "wav" if f == "wav" else "mp3"


def synthesize_to_file(text: str, dest: Path, fmt: str, lang: str = DEFAULT_LANG, slow: bool = False) -> Path:
    """Generate TTS into 'dest' using gTTS. Returns the final path written.

    If fmt == 'wav', converts the intermediate MP3 to WAV using pydub (requires ffmpeg).
    """
    response_format: RespFormat = _normalize_response_format(fmt)

    # Normalize destination extension based on requested format
    desired_ext = _ext_for_format(response_format)
    if dest.suffix.lower() != desired_ext:
        dest = dest.with_suffix(desired_ext)

    # Always synthesize to MP3 first
    tmp_mp3 = dest.with_suffix(".mp3.part")

    tts = gTTS(text=text, lang=lang, slow=slow)
    tts.save(str(tmp_mp3))

    if response_format == "mp3":
        final_mp3 = dest.with_suffix(".mp3")
        tmp_mp3.replace(final_mp3)
        return final_mp3

    # Convert to WAV using pydub (ffmpeg required)
    if AudioSegment is None:
        # Clean up tmp file before raising
        tmp_mp3.unlink(missing_ok=True)
        raise RuntimeError("WAV conversion requires pydub and ffmpeg to be installed and available in PATH.")

    audio = AudioSegment.from_file(str(tmp_mp3), format="mp3")
    final_wav = dest.with_suffix(".wav")
    audio.export(str(final_wav), format="wav")
    tmp_mp3.unlink(missing_ok=True)
    return final_wav


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Generate Vietnamese TTS audio using Google Translate (gTTS).")
    parser.add_argument("text", help="Text to synthesize (e.g., 'Xin chào thế giới')")
    parser.add_argument("output_path", help="Output file or directory path for the saved audio")
    parser.add_argument("--format", choices=["mp3", "wav"], default=DEFAULT_FORMAT, help="Output audio format (default: %(default)s)")
    parser.add_argument("--lang", default=DEFAULT_LANG, help="Language code (default: %(default)s)")
    parser.add_argument("--slow", action="store_true", help="Speak more slowly")
    args = parser.parse_args(argv)

    try:
        out_path = ensure_output_path(args.output_path, args.text, default_ext=_ext_for_format(args.format))
        final_path = synthesize_to_file(args.text, out_path, fmt=args.format, lang=args.lang, slow=args.slow)
    except Exception as e:
        print(f"Failed to generate audio: {e}", file=sys.stderr)
        return 2

    print(str(final_path.resolve()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
