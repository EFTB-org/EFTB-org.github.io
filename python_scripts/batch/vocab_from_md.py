#!/usr/bin/env python3
"""Batch-generate vocabulary audios (English, Vietnamese, or both) from a lesson markdown file.

Primary use-case: Extract the first numbered vocabulary table (Word/Phrase + Meaning)
and produce per-term audio files for accessibility.

English:
    - Extracts the 2nd <td> (Word/Phrase) for rows with a numeric first column
    - Uses Groq TTS (helpers from generate_eng_audio.py)
    - Requires GROQ_API_KEY (env or --api-key) unless only Vietnamese is requested

Vietnamese:
    - Extracts the 4th <td> (Meaning) for those rows
    - Uses gTTS (helpers imported from generate_vie_audio.py)
    - No API key required

When --lang-target both is specified, outputs are placed in language subdirectories:
    <out-dir>/en/*.mp3  and  <out-dir>/vi/*.mp3 (or wav)

Usage (from within python_scripts directory, per project guidelines):
    uv run generate_vocab_audios.py ../content/docs/topic_2/lesson-9.md \
            --out-dir ../static/audio/topic_2/lesson-9/vocab --format mp3 --lang-target both

Key Flags:
    --lang-target   en|vi|both (default: en)
    --list-only     Show extracted phrases (per selected languages) and exit
    --skip-existing Skip audio files that already exist

Notes:
    - Parses only the FIRST vocabulary table (ends at </tbody>)
    - Ignores header / category rows (rows without leading number cell)
    - Vietnamese filenames are slugified via generate_vie_audio's slug logic
    - English filenames use generate_eng_audio's slug logic
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Iterable, List
from dotenv import load_dotenv

from groq import Groq

# Load environment variables from .env file
load_dotenv()

# Vietnamese (gTTS) helpers
try:  # pragma: no cover - import guard
    from generate_vie_audio import (
        slugify_filename as slugify_filename_vi,  # type: ignore
        synthesize_to_file as synthesize_vi,      # type: ignore
        _ext_for_format as _ext_for_format_vi,    # type: ignore
        DEFAULT_FORMAT as DEFAULT_VI_FORMAT,      # type: ignore
    )
except Exception:  # pragma: no cover - fallback wrappers
    slugify_filename_vi = None  # type: ignore
    synthesize_vi = None  # type: ignore
    _ext_for_format_vi = None  # type: ignore
    DEFAULT_VI_FORMAT = "mp3"  # type: ignore

# Import helpers from existing script (same directory).
try:
    from generate_eng_audio import (
        DEFAULT_MODEL,
        DEFAULT_VOICE,
        DEFAULT_FORMAT,
        slugify_filename,
        synthesize_to_file,
        _ext_for_format,  # type: ignore
    )
except Exception as e:  # pragma: no cover - defensive
    print(f"Failed to import generate_eng_audio helpers: {e}", file=sys.stderr)
    sys.exit(2)


ROW_REGEX_SIMPLE = re.compile(r"<tr><td>(?P<no>\d+)</td><td>(?P<phrase>.+?)</td><td>")

# Extended regex capturing English + IPA + Vietnamese meaning when present.
ROW_REGEX_FULL = re.compile(
    r"<tr><td>(?P<no>\d+)</td><td>(?P<eng>.+?)</td><td>(?P<ipa>.+?)</td><td>(?P<vie>.+?)</td></tr>"
)


def extract_vocab_rows(markdown_text: str) -> list[dict]:
    """Extract numbered vocabulary rows (English + Vietnamese) from first table.

    Returns list of dicts with keys: no (int), eng (str), vie (str|''), ipa (str|'').
    Falls back to simpler regex if full pattern not matched.
    """
    rows: list[dict] = []
    in_table = False
    for line in markdown_text.splitlines():
        if '<tbody>' in line:
            in_table = True
        if not in_table:
            continue
        full = ROW_REGEX_FULL.search(line)
        if full:
            eng = full.group('eng').strip()
            vie = full.group('vie').strip()
            ipa = full.group('ipa').strip()
            if eng and eng != '—':
                rows.append({
                    'no': int(full.group('no')),
                    'eng': html_unescape(strip_html_tags(eng)),
                    'vie': html_unescape(strip_html_tags(vie)) if vie and vie != '—' else '',
                    'ipa': html_unescape(strip_html_tags(ipa)) if ipa and ipa != '—' else '',
                })
        else:
            simple = ROW_REGEX_SIMPLE.search(line)
            if simple:
                phrase = simple.group('phrase').strip()
                if phrase and phrase != '—':
                    rows.append({
                        'no': int(simple.group('no')),
                        'eng': html_unescape(strip_html_tags(phrase)),
                        'vie': '',
                        'ipa': '',
                    })
        if in_table and '</tbody>' in line:
            break
    return rows


HTML_TAG_RE = re.compile(r"<.*?>")
HTML_ENTITIES = {
    '&amp;': '&',
    '&lt;': '<',
    '&gt;': '>',
    '&quot;': '"',
    '&#39;': "'",
    '&nbsp;': ' ',
}


def strip_html_tags(s: str) -> str:
    return HTML_TAG_RE.sub('', s)


def html_unescape(s: str) -> str:
    for ent, char in HTML_ENTITIES.items():
        s = s.replace(ent, char)
    return s


def generate_english_audios(
    phrases: Iterable[str],
    out_dir: Path,
    client: Groq,
    model: str,
    voice: str,
    fmt: str,
    skip_existing: bool = False,
) -> list[Path]:
    from tqdm import tqdm  # local import

    written: list[Path] = []
    out_dir.mkdir(parents=True, exist_ok=True)
    ext = _ext_for_format(fmt)
    for phrase in tqdm(list(phrases), desc="EN Synth", unit="item"):
        slug = slugify_filename(phrase)
        target = out_dir / f"{slug}{ext}"
        if skip_existing and target.exists():
            continue
        try:
            synthesize_to_file(client, phrase, target, model=model, voice=voice, fmt=fmt)
            written.append(target)
        except Exception as e:
            print(f"[WARN][EN] Failed: '{phrase}': {e}", file=sys.stderr)
    return written


def generate_vietnamese_audios(
    phrases: Iterable[str],
    out_dir: Path,
    fmt: str,
    skip_existing: bool = False,
    slow: bool = False,
) -> list[Path]:
    if synthesize_vi is None or slugify_filename_vi is None or _ext_for_format_vi is None:
        raise RuntimeError("Vietnamese generation helpers not available (generate_vie_audio import failed).")
    from tqdm import tqdm  # local import

    written: list[Path] = []
    out_dir.mkdir(parents=True, exist_ok=True)
    ext = _ext_for_format_vi(fmt)
    for phrase in tqdm(list(phrases), desc="VI Synth", unit="item"):
        slug = slugify_filename_vi(phrase)
        target = out_dir / f"{slug}{ext}"
        if skip_existing and target.exists():
            continue
        try:
            synthesize_vi(phrase, target, fmt=fmt, lang="vi", slow=slow)  # type: ignore[arg-type]
            written.append(target)
        except Exception as e:
            print(f"[WARN][VI] Failed: '{phrase}': {e}", file=sys.stderr)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Batch-generate vocabulary audios (English, Vietnamese, or both).")
    parser.add_argument("lesson_md", help="Path to lesson markdown file (e.g., ../content/docs/topic_2/lesson-9.md)")
    parser.add_argument("--out-dir", default="../static/audio/vocab_tmp", help="Output directory for generated audio files")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Groq TTS model (default: %(default)s)")
    parser.add_argument("--voice", default=DEFAULT_VOICE, help="Groq TTS voice (default: %(default)s)")
    parser.add_argument("--format", choices=["wav", "mp3"], default=DEFAULT_FORMAT, help="Audio format (default: %(default)s)")
    parser.add_argument("--lang-target", choices=["en", "vi", "both"], default="en", help="Which language(s) to generate (default: %(default)s)")
    parser.add_argument("--vi-slow", action="store_true", help="Generate Vietnamese audio in slow mode (gTTS slow flag)")
    parser.add_argument("--api-key", dest="api_key", default=None, help="Groq API key (overrides GROQ_API_KEY env var)")
    parser.add_argument("--skip-existing", action="store_true", help="Skip files that already exist")
    parser.add_argument("--list-only", action="store_true", help="Only list extracted phrases for selected language(s); do not synthesize")
    args = parser.parse_args(argv)

    lesson_path = Path(args.lesson_md)
    if not lesson_path.is_file():
        print(f"Lesson markdown not found: {lesson_path}", file=sys.stderr)
        return 1

    text = lesson_path.read_text(encoding="utf-8")
    rows = extract_vocab_rows(text)
    if not rows:
        print("No vocabulary rows found.", file=sys.stderr)
        return 1

    # Build phrase lists per language
    eng_phrases = [r['eng'] for r in rows if r['eng']]
    vie_phrases = [r['vie'] for r in rows if r.get('vie')]

    if args.list_only:
        if args.lang_target in ("en", "both"):
            print("# English phrases")
            for p in eng_phrases:
                print(p)
        if args.lang_target in ("vi", "both"):
            print("# Vietnamese meanings")
            for p in vie_phrases:
                print(p)
        return 0

    out_dir = Path(args.out_dir)
    total_generated = 0

    if args.lang_target in ("en", "both"):
        api_key = args.api_key or os.environ.get("GROQ_API_KEY")
        if not api_key:
            if args.lang_target == "en":
                print("GROQ_API_KEY is not set. Provide via env or --api-key.", file=sys.stderr)
                return 3
            else:
                print("[WARN] GROQ_API_KEY missing; skipping English generation.", file=sys.stderr)
        else:
            client = Groq(api_key=api_key)
            en_dir = out_dir if args.lang_target == "en" else out_dir / "en"
            generated_en = generate_english_audios(
                eng_phrases,
                out_dir=en_dir,
                client=client,
                model=args.model,
                voice=args.voice,
                fmt=args.format,
                skip_existing=args.skip_existing,
            )
            total_generated += len(generated_en)
            print(f"English: {len(generated_en)} files -> {en_dir.resolve()}")

    if args.lang_target in ("vi", "both"):
        if not vie_phrases:
            print("[WARN] No Vietnamese meanings extracted; skipping VI generation.", file=sys.stderr)
        else:
            try:
                vi_dir = out_dir if args.lang_target == "vi" else out_dir / "vi"
                generated_vi = generate_vietnamese_audios(
                    vie_phrases,
                    out_dir=vi_dir,
                    fmt=args.format,
                    skip_existing=args.skip_existing,
                    slow=args.vi_slow,
                )
                total_generated += len(generated_vi)
                print(f"Vietnamese: {len(generated_vi)} files -> {vi_dir.resolve()}")
            except Exception as e:
                print(f"[ERROR] Vietnamese generation failed: {e}", file=sys.stderr)

    print(f"Total generated: {total_generated} files")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
