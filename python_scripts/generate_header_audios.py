#!/usr/bin/env python3
"""
Generate English TTS audio for each Markdown heading in a lesson file.

It scans a lesson markdown file, extracts headings (##, ###, ####), cleans the
heading text (stripping markdown formatting / trailing colons), and produces
an audio file per heading using the existing `generate_eng_audio.py` script.

Audio files are stored in:  <base_output_dir>/headers/<slug>.mp3 (default)
Typical usage for lesson-6:

    python generate_header_audios.py \
        --markdown ../content/docs/topic_2/lesson-6.md \
        --lesson lesson-6 \
        --out-root ../static/audio \
        --format mp3

Then reference in markdown via:
    {{<audio-with-controls src="audio/lesson-6/headers/<slug>.mp3">}}

Options:
  --dry-run : Only list the headings + target paths (no API calls)
  --force   : Re-generate even if file already exists

Requires GROQ_API_KEY env (forwarded to underlying generator) unless you pass
--api-key which is forwarded.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Tuple
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

THIS_DIR = Path(__file__).parent.resolve()
GEN_SCRIPT = THIS_DIR / "generate_eng_audio.py"

HEADING_RE = re.compile(r"^(#{2,4})\s+(.+?)\s*$")

# Default reusable phrases (shared headers) for lessons.
DEFAULT_SHARED_PHRASES = [
    "Section 1",
    "Section 2",
    "1. Vocabulary",
    "2. Language Booster",
    "3. Think and Speak",
    "1. Conversation",
    "Listening Comprehension",
    "Listening and Speaking",
    "2. Application",
    "Group activities",
    "Example",
    "Let's practice",
    "Structures",
]


def slugify(text: str) -> str:
    t = text.lower().strip()
    # remove markdown emphasis/backticks and html tags
    t = re.sub(r"[`*_]+", "", t)
    t = re.sub(r"<[^>]+>", "", t)
    # remove trailing punctuation like ':'
    t = re.sub(r"[:;,!?]+$", "", t)
    t = re.sub(r"\s+", " ", t)
    t = t.strip()
    t = t.replace(" ", "_")
    t = re.sub(r"[^a-z0-9_\-]", "", t)
    return t or "heading"


def extract_headings(markdown_path: Path) -> List[Tuple[str, str]]:
    headings: List[Tuple[str, str]] = []
    for line in markdown_path.read_text(encoding="utf-8").splitlines():
        m = HEADING_RE.match(line)
        if not m:
            continue
        hashes, raw = m.groups()
        cleaned = raw.strip()
        headings.append((hashes, cleaned))
    return headings


def build_audio_jobs(headings: Iterable[Tuple[str, str]], lesson: str, out_root: Path, fmt: str) -> List[Tuple[str, Path, str]]:
    jobs: List[Tuple[str, Path, str]] = []
    base = out_root / lesson / "headers"
    for _hashes, text in headings:
        slug = slugify(text)
        # Ensure extension matches format
        ext = ".mp3" if fmt == "mp3" else ".wav"
        dest = base / f"{slug}{ext}"
        jobs.append((text, dest, slug))
    return jobs


def ensure_gen_script() -> None:
    if not GEN_SCRIPT.exists():
        print(f"Cannot find generate_eng_audio.py at {GEN_SCRIPT}", file=sys.stderr)
        sys.exit(2)


def run_generation(text: str, dest: Path, fmt: str, api_key: str | None, voice: str | None, model: str | None, dry_run: bool, force: bool) -> None:
    if dest.exists() and not force:
        print(f"SKIP (exists): {dest}")
        return
    if dry_run:
        print(f"DRY  -> {dest} :: {text}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(GEN_SCRIPT), text, str(dest.parent), "--format", fmt]
    if voice:
        cmd += ["--voice", voice]
    if model:
        cmd += ["--model", model]
    if api_key:
        cmd += ["--api-key", api_key]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
        saved = out.strip().splitlines()[-1]
        print(f"OK   -> {saved}")
    except subprocess.CalledProcessError as e:
        print(f"ERR  -> {dest} :: {e.output}", file=sys.stderr)


def main(argv: List[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Generate header audios for a lesson markdown file or shared set.")
    p.add_argument("--markdown", help="Path to lesson markdown file (omit when using --phrases or --default-set)")
    p.add_argument("--lesson", required=True, help="Lesson folder or shared namespace (e.g., lesson-6 or common)")
    p.add_argument("--out-root", required=True, help="Root output dir holding lesson folders (e.g., ../static/audio)")
    p.add_argument("--format", choices=["mp3", "wav"], default="mp3", help="Audio format (default: mp3)")
    p.add_argument("--voice", help="Override voice name (forwarded)")
    p.add_argument("--model", help="Override model name (forwarded)")
    p.add_argument("--api-key", dest="api_key", help="Groq API key (overrides env)")
    p.add_argument("--dry-run", action="store_true", help="List actions without calling TTS")
    p.add_argument("--force", action="store_true", help="Re-generate even if file exists")
    p.add_argument("--phrases", nargs="+", help="Explicit phrases to generate instead of parsing markdown")
    p.add_argument("--phrases-file", help="File containing one phrase per line")
    p.add_argument("--default-set", action="store_true", help="Use built-in default shared phrase set")
    args = p.parse_args(argv)

    ensure_gen_script()

    phrases: List[str] = []
    if args.default_set:
        phrases.extend(DEFAULT_SHARED_PHRASES)
    if args.phrases:
        phrases.extend(args.phrases)
    if args.phrases_file:
        pf = Path(args.phrases_file)
        if not pf.exists():
            p.error(f"Phrases file not found: {pf}")
        phrases.extend([ln.strip() for ln in pf.read_text(encoding="utf-8").splitlines() if ln.strip()])

    headings: List[Tuple[str, str]]
    if phrases:
        # Fabricate heading tuples with dummy hash markers
        headings = [("##", ph) for ph in phrases]
    else:
        if not args.markdown:
            p.error("--markdown required when not providing phrases/default set")
        md_path = Path(args.markdown).resolve()
        if not md_path.exists():
            p.error(f"Markdown file not found: {md_path}")
        headings = extract_headings(md_path)
        if not headings:
            print("No headings found.")
            return 0

    jobs = build_audio_jobs(headings, args.lesson, Path(args.out_root).resolve(), args.format)

    api_key = args.api_key or os.environ.get("GROQ_API_KEY")
    if not api_key and not args.dry_run:
        print("GROQ_API_KEY missing (use env or --api-key); running dry-run instead.", file=sys.stderr)
        args.dry_run = True

    for text, dest, _slug in jobs:
        run_generation(text, dest, args.format, api_key, args.voice, args.model, args.dry_run, args.force)

    print("Done.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
