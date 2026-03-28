import argparse
import os
import re
import sys
from pathlib import Path
from typing import Optional, Literal

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

#!/usr/bin/env python3
"""
CLI: Generate English TTS audio using Groq and save it.

Backend:
- Groq Text-to-Speech API (requires GROQ_API_KEY env var or --api-key)

Usage:
        python generate_eng_audio.py <text> <output_path> [--voice VOICE] [--model MODEL] [--format FORMAT]

Notes:
- Default model: playai-tts
- Default voice: Fritz-PlayAI (US-style voice). Adjust with --voice if desired.
- Default output/format: wav. Use --format mp3 for mp3 output.
- The script prints the final saved audio file path to stdout on success.

Exit codes:
    0 = success
    2 = API/network or write error
    3 = invalid arguments (e.g., missing GROQ API key)
"""

DEFAULT_MODEL = "playai-tts"
DEFAULT_VOICE = "Fritz-PlayAI"
DEFAULT_FORMAT = "wav"  # "wav" or "mp3"


def slugify_filename(stem: str) -> str:
    s = stem.strip().lower()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9_\-]+", "", s)
    return s or "audio"


def ensure_output_path(output: str, text: str, default_ext: str = ".wav") -> Path:
    p = Path(output)
    if p.exists() and p.is_dir():
        return p / f"{slugify_filename(text)}{default_ext}"
    # If user indicates directory by trailing separator
    if str(output).endswith((os.sep, "/")):
        Path(output).mkdir(parents=True, exist_ok=True)
        return Path(output) / f"{slugify_filename(text)}{default_ext}"
    # If path has no extension, add default
    if p.suffix == "":
        p = p.with_suffix(default_ext)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

RespFormat = Literal["flac", "mp3", "mulaw", "ogg", "wav"]


def _ext_for_format(fmt: str) -> str:
    fmt = (fmt or "").lower()
    if fmt == "mp3":
        return ".mp3"
    # default to wav
    return ".wav"


def _normalize_response_format(fmt: str) -> RespFormat:
    f = (fmt or "").lower()
    if f in ("wav", "mp3", "ogg", "flac", "mulaw"):
        return f  # type: ignore[return-value]
    return "wav"


def synthesize_to_file(client: Groq, text: str, dest: Path, model: str, voice: str, fmt: str) -> Path:
    """Call Groq TTS and write the result to 'dest'. Returns the final path written."""
    response_format: RespFormat = _normalize_response_format(fmt)
    response = client.audio.speech.create(
        model=model,
        voice=voice,
        input=text,
        response_format=response_format,
    )

    # If user passed a path with a different extension, normalize to match response format
    desired_ext = _ext_for_format(response_format)
    if dest.suffix.lower() != desired_ext:
        dest = dest.with_suffix(desired_ext)

    tmp = dest.with_suffix(dest.suffix + ".part")
    response.write_to_file(str(tmp))
    tmp.replace(dest)
    return dest


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Generate English TTS audio using Groq and save it.")
    parser.add_argument("text", help="Text to synthesize (e.g., 'Hello world')")
    parser.add_argument("output_path", help="Output file or directory path for the saved audio")
    parser.add_argument("--voice", default=DEFAULT_VOICE, help="Voice name (default: %(default)s)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Groq TTS model (default: %(default)s)")
    parser.add_argument("--format", choices=["wav", "mp3"], default=DEFAULT_FORMAT, help="Output audio format (default: %(default)s)")
    parser.add_argument("--api-key", dest="api_key", default=None, help="Groq API key (overrides GROQ_API_KEY env var)")
    args = parser.parse_args(argv)

    api_key = args.api_key or os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("GROQ_API_KEY is not set. Provide via env or --api-key.", file=sys.stderr)
        return 3

    out_path = ensure_output_path(args.output_path, args.text, default_ext=_ext_for_format(args.format))

    try:
        client = Groq(api_key=api_key)
        final_path = synthesize_to_file(client, args.text, out_path, model=args.model, voice=args.voice, fmt=args.format)
    except Exception as e:
        print(f"Failed to generate audio: {e}", file=sys.stderr)
        return 2

    print(str(final_path.resolve()))
    return 0


if __name__ == "__main__":
    sys.exit(main())