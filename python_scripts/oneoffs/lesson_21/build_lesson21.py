#!/usr/bin/env python3
"""Build the Lesson 21 page and audio, using Lesson 20's voice pipeline.

English: Chatterbox with kore_audio_prompt.wav (preferred), Gemini Kore when
GPU/model unavailable, gTTS for any remaining clips when Gemini is exhausted.
Vietnamese vocabulary and translations: gTTS. Vietnamese scene context: Gemini Kore. Bo and Na's
Vietnamese conversation: the original M4A recordings supplied with the lesson.

Run from the repository root:
  python_scripts/.venv/bin/python python_scripts/oneoffs/lesson_21/build_lesson21.py --stage page
  HF_HUB_OFFLINE=1 python_scripts/.venv/bin/python python_scripts/oneoffs/lesson_21/build_lesson21.py --stage all
  # When GPU + Chatterbox weights return, regenerate original voice for all
  # English assets without affecting the supplied Vietnamese human recordings:
  python_scripts/.venv/bin/python python_scripts/oneoffs/lesson_21/build_lesson21.py --stage english --replace-english all

Existing valid MP3s are reused, and audio conversion is atomic.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import html
import json
import re
import subprocess
import sys
import tempfile
import zipfile
from collections import Counter
from pathlib import Path

THIS = Path(__file__).resolve()
PYTHON_DIR = THIS.parents[2]
ROOT = PYTHON_DIR.parent
RAW = PYTHON_DIR / "raw_lessons" / "LESSON-21"
AUDIO = ROOT / "frontend/static/audio/lesson-21"
PAGE = ROOT / "frontend/content/docs/topic_6/lesson-21.md"
TOPIC = PAGE.parent / "_index.md"
VOICE_PROMPT = PYTHON_DIR / "kore_audio_prompt.wav"

# Text and translations follow the supplied "LESSON 21 HOW MUCH IS COFFEE.docx.md".
VOCAB = [
    ("a haircut", "/ə ˈheəkʌt/", "Noun", "Việc cắt tóc"),
    ("museum admission fee", "/mjuːˈziːəm ədˈmɪʃn fiː/", "Noun phrase", "Phí vào cửa bảo tàng"),
    ("a cup of coffee", "/ə kʌp əv ˈkɒfi/", "Noun phrase", "Một ly cà phê"),
    ("a taxi ride across town", "/ə ˈtæksi raɪd əˈkrɒs taʊn/", "Noun phrase", "Một chuyến taxi băng qua thị trấn"),
    ("a movie ticket", "/ə ˈmuːvi ˈtɪkɪt/", "Noun phrase", "Một vé xem phim"),
    ("bus fare", "/ˈbʌs feə/", "Noun phrase", "Tiền vé xe buýt"),
    ("reasonable", "/ˈriːznəbl/", "Adjective", "Hợp lý, phải chăng (về giá cả)"),
    ("fare", "/feə/", "Noun", "Tiền vé, cước phí di chuyển"),
    ("convenience store", "/kənˈviːniəns stɔː/", "Noun phrase", "Cửa hàng tiện lợi"),
    ("It depends.", "/ɪt dɪˈpendz/", "Phrase", "Còn tùy, điều đó còn phụ thuộc"),
    ("hometown", "/ˈhəʊmtaʊn/", "Noun", "Quê hương, quê nhà"),
    ("excuse me", "/ɪkˈskjuːz miː/", "Phrase", "Xin lỗi (để mở lời hỏi hoặc thu hút sự chú ý)"),
    ("how much", "/ˌhaʊ ˈmʌtʃ/", "Phrase", "Bao nhiêu, bao nhiêu tiền"),
    ("bottled water", "/ˌbɒtld ˈwɔːtə/", "Noun", "Nước đóng chai"),
    ("dollar", "/ˈdɒlə/", "Noun", "Đô la"),
    ("expensive", "/ɪkˈspensɪv/", "Adjective", "Đắt, đắt tiền"),
    ("about", "/əˈbaʊt/", "Adverb", "Khoảng, xấp xỉ"),
    ("around", "/əˈraʊnd/", "Adverb", "Khoảng, xấp xỉ"),
    ("cost", "/kɒst/", "Verb", "Có giá, tốn (bao nhiêu tiền)"),
    ("be about/around + price", "—", "Structure", "Có giá khoảng…, giá vào khoảng…"),
]

# title, groups of (structure, [English/Vietnamese examples])
BOOSTERS = [
    ("Asking about prices", [
        ("How much + be + noun?", [
            ("How much is a cup of coffee?", "Một ly cà phê giá bao nhiêu tiền?"),
            ("How much are movie tickets?", "Vé xem phim giá bao nhiêu tiền?"),
        ]),
        ("How much do/does + noun + cost?", [
            ("How much does a cup of coffee cost?", "Một ly cà phê giá bao nhiêu tiền?"),
            ("How much do movie tickets cost?", "Vé xem phim giá bao nhiêu tiền?"),
        ]),
    ]),
    ("Giving prices", [
        ("Be + price", [
            ("A cup of coffee is six dollars.", "Một ly cà phê giá 6 đô la."),
            ("Movie tickets are thirteen dollars.", "Vé xem phim giá 13 đô la."),
        ]),
        ("Cost + price", [
            ("A cup of coffee costs six dollars.", "Một ly cà phê có giá 6 đô la."),
            ("Movie tickets cost thirteen dollars.", "Vé xem phim có giá 13 đô la."),
        ]),
    ]),
]

PRACTICE = ["a meal at a fast food restaurant", "a newspaper", "a bottle of water"]
CONTEXT = (
    "Bo và Na ghé vào cửa hàng tiện lợi. Khi biết giá trà sữa khá đắt, Bo vẫn thèm quá trời. "
    "Thấy vậy, Na hào phóng đề nghị mua cho bạn, khiến Bo vui vẻ nhờ Na mua thêm cả bánh mì."
)

DIALOGUE = [
    ("Bo", "Na ơi, một ly cà phê ở đây bao nhiêu tiền vậy?", "Na, how much does a cup of coffee cost here?"),
    ("Na", "30.000 đồng một ly á.", "It costs thirty thousand dong."),
    ("Bo", "Cũng được đó! Thế một chai nước suối bao nhiêu?", "That’s not bad! How much is a bottle of water?"),
    ("Na", "10.000 đồng một chai thôi.", "It’s only ten thousand dong a bottle."),
    ("Bo", "Còn trà sữa thì sao?", "What about milk tea?"),
    ("Na", "Một ly 50.000 đồng đó.", "It’s fifty thousand dong."),
    ("Bo", "Hả? Năm mươi nghìn á? Đắt quá!", "What? Fifty thousand dong? That’s expensive!"),
    ("Na", "Ừ, trà sữa thường đắt hơn nước suối mà.", "Yeah, milk tea is usually more expensive than bottled water."),
    ("Bo", "Chán ghê, tự nhiên tớ thèm trà sữa quá à.", "Oh, man! Now I want milk tea so bad!"),
    ("Na", "Xời, thèm thì để tớ mua cho. Tớ giàu mà!", "Oh, come on! If you want some, I’ll buy it for you. I’m rich, you know!"),
    ("Bo", "Yeah, vậy cậu mua cho tớ một ly trà sữa và một ổ bánh mì nha!", "Yay! Then, can you get me a cup of milk tea and a bánh mì, please?"),
    ("Na", "Okiee nè Bo, cậu thích là được nè.", "Okay, Bo! As long as you’re happy!"),
]

COMPREHENSION = [
    ("How much is a cup of coffee?", "It’s thirty thousand dong."),
    ("How much is a bottle of water?", "It’s ten thousand dong."),
    ("How much is a cup of milk tea?", "It’s fifty thousand dong."),
    ("What does Bo think about the price of milk tea?", "He thinks it’s expensive."),
    ("What does Bo ask Na to buy for him?", "A cup of milk tea and a bánh mì."),
]

PRONUNCIATION = [("thirteen", "thirty"), ("fourteen", "forty"), ("fifteen", "fifty")]
APPLICATION_INSTRUCTION = (
    "Pair work. Work in pairs and create your own conversation. "
    "Take turns speaking and try to use the structures you have learned."
)
APPLICATION_DESCRIPTION = (
    "Imagine you are planning a day out with a friend. Take turns asking about the prices "
    "of food, drinks, and transportation. Compare prices and agree on what to buy within your budget."
)
APPLICATION_INCLUDES = [
    "Asking about prices and giving prices.",
    "Comparing prices and expressing opinions about prices.",
    "Deciding what to buy and agreeing on what to spend.",
]
APPLICATION_EXAMPLES = [
    "How much is a cup of coffee?",
    "It’s thirty thousand dong.",
    "That’s expensive!",
    "Let’s get a sandwich and some water!",
]


def slug(text: str) -> str:
    import unicodedata
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def attr(text: str) -> str:
    return html.escape(text, quote=True)


def ap(relative: str) -> str:
    return f"audio/lesson-21/{relative}"


def audio_text(text: str, relative: str) -> str:
    return '{{< audio-text text="' + attr(text) + '" src="' + ap(relative) + '" >}}'


def audio_header(text: str, relative: str, level: int, anchor: str = "") -> str:
    suff = f' id="{anchor}"' if anchor else ""
    return '{{< header-audio text="' + attr(text) + '" src="' + ap(relative) + '" level="' + str(level) + '"' + suff + ' >}}'


def audio_controls(relative: str) -> str:
    return '{{< audio-with-controls src="' + ap(relative) + '" >}}'


def escape_cell(text: str) -> str:
    return html.escape(text)


def dialogue_rows() -> tuple[list[dict], list[dict]]:
    counters: Counter[str] = Counter()
    vi_rows, en_rows = [], []
    for speaker, vi, en in DIALOGUE:
        counters[speaker] += 1
        filename = f"{speaker}{counters[speaker]}.mp3"
        vi_rows.append({"type": "dialogue", "speaker": speaker, "text": vi, "en": en, "audio": filename})
        en_rows.append({"type": "dialogue", "speaker": speaker, "text": en, "audio": filename})
    return vi_rows, en_rows


def write_json() -> None:
    vi, en = dialogue_rows()
    for folder, rows in [("think-and-speak", vi), ("conversation", en)]:
        dest = AUDIO / folder / "conversation.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_page() -> None:
    TOPIC.parent.mkdir(parents=True, exist_ok=True)
    if not TOPIC.exists():
        TOPIC.write_text(
            '---\ntitle: "TOPIC 6"\ndescription: "English lessons beginning with asking about prices."\n'
            'lead: "English for The Blind - TOPIC 6"\ndraft: false\nweight: 120\n'
            'seo:\n  title: "EFTB - Topic 6"\n  description: "English lessons on prices and related topics."\n---\n',
            encoding="utf-8",
        )
    parts = [
        '---\ntitle: "Lesson 21: HOW MUCH IS COFFEE?"\n'
        'description: "Asking about prices and giving prices."\n'
        'lead: "English for The Blind - Lesson 21"\n'
        'draft: false\nweight: 910\nseo:\n'
        '  title: "EFTB - Lesson 21: HOW MUCH IS COFFEE?"\n'
        '  description: "Learn how to ask about and give prices in English."\n'
        'hide_title: true\n---\n',
        audio_header("Lesson 21: How Much Is Coffee?", "title.mp3", 1),
        audio_controls("focus/eng/audio.mp3"),
        "**Lesson Focus**",
        "- Asking about prices\n- Giving prices",
        "---",
        "## Section 1 {#section-1 .toc-only}",
        audio_header("Section 1", "common/unused.mp3", 2, "section-1").replace(ap("common/unused.mp3"), "audio/common/headers/section_1.mp3"),
        "### 1. Vocabulary {#vocabulary .toc-only}",
        audio_header("1. Vocabulary", "common/unused.mp3", 3, "vocabulary").replace(ap("common/unused.mp3"), "audio/common/headers/1_vocabulary.mp3"),
        '<table>\n<thead><tr><th>No</th><th>Word / Phrase</th><th>IPA</th>'
        '<th>Part of speech</th><th>Meaning</th></tr></thead>\n<tbody>',
    ]
    for idx, (en, ipa, pos, vi) in enumerate(VOCAB, 1):
        key = slug(en)
        parts.append(
            f"<tr><td>{idx}</td><td>{audio_text(en, f'vocabs/eng/{key}.mp3')}</td>"
            f"<td>{escape_cell(ipa)}</td><td>{escape_cell(pos)}</td>"
            f"<td>{audio_text(vi, f'vocabs/vie/{key}.mp3')}</td></tr>"
        )
    parts += ["</tbody></table>", "### 2. Language Booster {#language-booster .toc-only}",
              audio_header("2. Language Booster", "common/unused.mp3", 3, "language-booster").replace(
                  ap("common/unused.mp3"), "audio/common/headers/2_language_booster.mp3"),
              "<table><thead><tr><th>Structure</th><th>Example</th><th>Meaning</th></tr></thead><tbody>"]
    for group_idx, (title, blocks) in enumerate(BOOSTERS, 1):
        parts.append(
            f'<tr><th colspan="3">{audio_text(title, f"sentences/group_{group_idx}.mp3")}</th></tr>'
        )
        for pattern_idx, (pattern, examples) in enumerate(blocks, 1):
            pattern_key = f"sentences/pattern_{group_idx}_{pattern_idx}.mp3"
            for example_idx, (en, vi) in enumerate(examples, 1):
                key = f"{group_idx}_{pattern_idx}_{example_idx}"
                structure_cell = (
                    f'<td rowspan="{len(examples)}">'
                    f'{audio_text(pattern, pattern_key)}</td>'
                    if example_idx == 1 else ""
                )
                parts.append(
                    "<tr>" + structure_cell +
                    f'<td>{audio_text(en, f"sentences/en_{key}.mp3")}</td>'
                    f'<td>{audio_text(vi, f"sentences/vi_{key}.mp3")}</td></tr>'
                )
    parts += [
        "</tbody></table>",
        "### 3. Let's Practice {#lets-practice .toc-only}",
        audio_header("3. Let's Practice", "common/unused.mp3", 3, "lets-practice").replace(
            ap("common/unused.mp3"), "audio/common/headers/3_lets_practice.mp3"),
        audio_text("Take turns asking about and giving prices for the items below.",
                   "lets_practice/instructions.mp3"),
        "<table><thead><tr><th>Item 1</th><th>Item 2</th><th>Item 3</th></tr></thead><tbody><tr>" +
        "".join(
            f'<td>{audio_text(phrase, f"lets_practice/item_{i}.mp3")}</td>'
            for i, phrase in enumerate(PRACTICE, 1)
        ) + "</tr></tbody></table>",
        "### 4. Think and Speak {#think-and-speak .toc-only}",
        audio_header("4. Think and Speak", "common/unused.mp3", 3, "think-and-speak").replace(
            ap("common/unused.mp3"), "audio/common/headers/4_think_and_speak.mp3"),
        "**Ngữ cảnh:**",
        audio_controls("context/vie/context.mp3"),
        CONTEXT,
        '{{< audio_script_table json="/audio/lesson-21/think-and-speak/conversation.json" '
        'audiopath="/audio/lesson-21/think-and-speak/" headerSpeaker="Character" '
        'headerText="Vietnamese" headerMeaning="English" meaningField="en" >}}',
        "---",
        "## Section 2 {#section-2 .toc-only}",
        audio_header("Section 2", "common/unused.mp3", 2, "section-2").replace(
            ap("common/unused.mp3"), "audio/common/headers/section_2.mp3"),
        "### 1. Conversation {#conversation .toc-only}",
        audio_header("1. Conversation", "common/unused.mp3", 3, "conversation").replace(
            ap("common/unused.mp3"), "audio/common/headers/1_conversation.mp3"),
        '{{< audio_script_table json="/audio/lesson-21/conversation/conversation.json" '
        'audiopath="/audio/lesson-21/conversation/" headerSpeaker="Character" '
        'headerText="English" meaningField="" >}}',
        "#### Listening Comprehension {#listening-comprehension .toc-only}",
        audio_header("Listening Comprehension", "common/unused.mp3", 4).replace(
            ap("common/unused.mp3"), "audio/common/headers/listening_comprehension.mp3"),
        audio_header("Listen carefully and answer the questions:", "common/unused.mp3", 5).replace(
            ap("common/unused.mp3"), "audio/common/headers/listen_carefully_and_answer_the_questions.mp3"),
        '<table><thead><tr><th>Question</th><th>Answer</th></tr></thead><tbody>',
    ]
    for i, (q, a) in enumerate(COMPREHENSION, 1):
        parts.append(
            f'<tr><td>{audio_text(f"{i}. {q}", f"comprehension/q{i}.mp3")}</td>'
            f'<td>{audio_text(a, f"comprehension/a{i}.mp3")}</td></tr>'
        )
    parts += [
        "</tbody></table>",
        "#### Listening and Speaking {#listening-and-speaking .toc-only}",
        audio_header("Listening and Speaking", "common/unused.mp3", 4).replace(
            ap("common/unused.mp3"), "audio/common/headers/listening_and_speaking.mp3"),
        "**Pronunciation Note: -teen vs. -ty**",
        '<table><thead><tr><th>-teen</th><th>-ty</th></tr></thead><tbody>',
    ]
    for i, (teen, ty) in enumerate(PRONUNCIATION, 1):
        parts.append(
            f'<tr><td>{audio_text(teen, f"pronunciation/teen_{i}.mp3")}</td>'
            f'<td>{audio_text(ty, f"pronunciation/ty_{i}.mp3")}</td></tr>'
        )
    parts += [
        "</tbody></table>",
        audio_controls("pronunciation/instructions.mp3"),
        "Listen to the audio and imitate the speaker's pronunciation, rhythm, and intonation.",
        "### 2. Application {#application .toc-only}",
        audio_header("2. Application", "application/title.mp3", 3, "application"),
        audio_controls("application/instructions.mp3"),
        "**PAIR WORK:** Work in pairs and create your own conversation. "
        "Take turns speaking and try to use the structures you have learned.",
        audio_header("Topic: Let's Plan a Day Out!", "application/topic.mp3", 4, "day-out"),
        audio_controls("application/description.mp3"),
        APPLICATION_DESCRIPTION,
        audio_text("Your conversation should include:", "application/includes.mp3"),
    ]
    for i, item in enumerate(APPLICATION_INCLUDES, 1):
        parts.append(f"- {audio_text(item, f'application/include_{i}.mp3')}")
    parts.append(audio_text("Example prompts:", "application/prompts.mp3"))
    for i, item in enumerate(APPLICATION_EXAMPLES, 1):
        parts.append(f"- {audio_text(item, f'application/example_{i}.mp3')}")
    PAGE.write_text("\n\n".join(parts) + "\n", encoding="utf-8")
    write_json()
    print(f"Wrote Lesson 21 page: {PAGE} and two conversation transcripts", flush=True)


def has_audio(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size < 1000:
        return False
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
         str(path)], text=True, capture_output=True,
    )
    try:
        return proc.returncode == 0 and float(proc.stdout.strip()) > 0.25
    except ValueError:
        return False


def encode_mp3(source: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=dest.parent) as tmp:
        target = Path(tmp) / "audio.mp3"
        proc = subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i",
             str(source), "-codec:a", "libmp3lame", "-q:a", "3", str(target)],
            capture_output=True, text=True,
        )
        if proc.returncode or not has_audio(target):
            raise RuntimeError(f"FFmpeg failure for {dest}: {proc.stderr[-1000:]}")
        target.replace(dest)


def convert_human_recordings() -> None:
    zips = list(RAW.glob("*.zip"))
    if len(zips) != 1:
        raise RuntimeError(f"Expected one recordings ZIP in {RAW}, found {len(zips)}")
    expected = {f"Bo{i}" for i in range(1, 7)} | {f"Na{i}" for i in range(1, 7)}
    with zipfile.ZipFile(zips[0]) as archive:
        matches = {}
        for info in archive.infolist():
            if info.is_dir() or not info.filename.lower().endswith(".m4a"):
                continue
            match = re.match(r"^(Bo|Na)(\d+)(?:[_.])", Path(info.filename).name)
            if not match:
                raise RuntimeError(f"Unexpected recording name: {info.filename}")
            key = "".join(match.groups())
            if key in matches:
                raise RuntimeError(f"Duplicate recording {key}")
            matches[key] = info.filename
        if set(matches) != expected:
            raise RuntimeError(f"Recordings missing: {expected - set(matches)}; extra: {set(matches) - expected}")
        for name in sorted(expected):
            target = AUDIO / "think-and-speak" / f"{name}.mp3"
            if has_audio(target):
                print(f"Existing human recording: {name}", flush=True)
                continue
            with tempfile.TemporaryDirectory() as tmp:
                m4a = Path(tmp) / "input.m4a"
                m4a.write_bytes(archive.read(matches[name]))
                encode_mp3(m4a, target)
                print(f"Converted human recording: {name}", flush=True)


def audio_jobs() -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    english = [
        ("Lesson twenty one. How much is coffee?", "title.mp3"),
        ("Lesson focus. Asking about prices. Giving prices.", "focus/eng/audio.mp3"),
        ("Two. Application", "application/title.mp3"),
        ("Take turns asking about and giving prices for the items below.", "lets_practice/instructions.mp3"),
        ("Listen to the audio and imitate the speaker's pronunciation, rhythm, and intonation.",
         "pronunciation/instructions.mp3"),
        (APPLICATION_INSTRUCTION, "application/instructions.mp3"),
        ("Topic: Let's Plan a Day Out!", "application/topic.mp3"),
        (APPLICATION_DESCRIPTION, "application/description.mp3"),
        ("Your conversation should include:", "application/includes.mp3"),
        ("Example prompts:", "application/prompts.mp3"),
    ]
    vietnamese = []
    for en, _ipa, _pos, vi in VOCAB:
        key = slug(en)
        english.append((en.replace(" + ", " plus ").replace("/", " or "), f"vocabs/eng/{key}.mp3"))
        vietnamese.append((vi, f"vocabs/vie/{key}.mp3"))
    for group_idx, (title, blocks) in enumerate(BOOSTERS, 1):
        english.append((title, f"sentences/group_{group_idx}.mp3"))
        for pat_idx, (pattern, examples) in enumerate(blocks, 1):
            speak_pattern = pattern.replace("+", "plus").replace("/", " or ")
            english.append((speak_pattern, f"sentences/pattern_{group_idx}_{pat_idx}.mp3"))
            for ex_idx, (en, vi) in enumerate(examples, 1):
                key = f"{group_idx}_{pat_idx}_{ex_idx}"
                english.append((en, f"sentences/en_{key}.mp3"))
                vietnamese.append((vi, f"sentences/vi_{key}.mp3"))
    for idx, phrase in enumerate(PRACTICE, 1):
        english.append((phrase, f"lets_practice/item_{idx}.mp3"))
    counters: Counter[str] = Counter()
    for speaker, _vi, en in DIALOGUE:
        counters[speaker] += 1
        english.append((en, f"conversation/{speaker}{counters[speaker]}.mp3"))
    for idx, (question, answer) in enumerate(COMPREHENSION, 1):
        english.append((question, f"comprehension/q{idx}.mp3"))
        english.append((answer, f"comprehension/a{idx}.mp3"))
    for idx, (teen, ty) in enumerate(PRONUNCIATION, 1):
        english += [(teen, f"pronunciation/teen_{idx}.mp3"), (ty, f"pronunciation/ty_{idx}.mp3")]
    for idx, text in enumerate(APPLICATION_INCLUDES, 1):
        english.append((text, f"application/include_{idx}.mp3"))
    for idx, text in enumerate(APPLICATION_EXAMPLES, 1):
        english.append((text, f"application/example_{idx}.mp3"))
    return english, vietnamese


def chunks(text: str, limit: int = 110) -> list[str]:
    """Bound Chatterbox utterances by words without cutting any words."""
    groups, section = [], ""
    for word in text.split():
        if len(section) + len(word) + 1 > limit and section:
            groups.append(section)
            section = ""
        section = f"{section} {word}".strip()
    if section:
        groups.append(section)
    return groups


def english_audio(device: str = "cuda", limit: int | None = None,
                  replace_paths: set[str] | None = None) -> None:
    import torch
    import torchaudio
    from chatterbox.tts import ChatterboxTTS
    jobs, _ = audio_jobs()
    if limit is not None:
        jobs = jobs[:limit]
    replace_paths = replace_paths or set()
    valid_paths = {rel for _, rel in jobs}
    if unknown := replace_paths - valid_paths - {"all"}:
        raise ValueError(f"Unknown English replacement paths: {sorted(unknown)}")
    pending = [
        (text, rel) for text, rel in jobs
        if not has_audio(AUDIO / rel) or "all" in replace_paths or rel in replace_paths
    ]
    if not pending:
        print(f"All {len(jobs)} requested English clips already exist", flush=True)
        return
    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available; rerun with --device cpu for the same Chatterbox voice.")
    if not VOICE_PROMPT.is_file():
        raise FileNotFoundError(VOICE_PROMPT)
    model = None
    for idx, (text, relative) in enumerate(pending, 1):
        dest = AUDIO / relative
        if model is None:
            print(f"Loading local Chatterbox model on {device} with Kore reference", flush=True)
            model = ChatterboxTTS.from_pretrained(device=device)
            model.prepare_conditionals(str(VOICE_PROMPT))
        print(f"English {idx}/{len(pending)}: {relative} — {text[:45]}", flush=True)
        with tempfile.TemporaryDirectory() as tmp:
            samples = []
            for piece in chunks(text):
                wave = model.generate(piece)
                samples.append(wave.cpu())
                del wave
                if device == "cuda":
                    torch.cuda.empty_cache()
            if len(samples) > 1:
                merged = []
                for n, sample in enumerate(samples):
                    if n:
                        merged.append(torch.zeros(sample.shape[0], int(model.sr * 0.14)))
                    merged.append(sample)
                samples = merged
            wav = Path(tmp) / "synth.wav"
            torchaudio.save(str(wav), torch.cat(samples, dim=1), model.sr)
            encode_mp3(wav, dest)
    print(f"English complete ({len(pending)} generated files)", flush=True)


def english_gemini(workers: int = 3, limit: int | None = None) -> None:
    """Fallback to the Lesson 20 Gemini/Kore voice if Chatterbox is unavailable.

    A failed API response never leaves a partial output masquerading as a valid
    MP3. Use a small pool to avoid submitting too many requests at once.
    """
    if workers < 1 or workers > 4:
        raise ValueError("Gemini workers must be between 1 and 4")
    jobs, _ = audio_jobs()
    if limit is not None:
        jobs = jobs[:limit]
    pending = [(text, rel) for text, rel in jobs if not has_audio(AUDIO / rel)]
    if not pending:
        print("All requested English clips already exist", flush=True)
        return

    def generate(job: tuple[str, str]) -> str:
        text, relative = job
        target = AUDIO / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=target.parent) as tmp:
            intermediate = Path(tmp) / "clip.mp3"
            args = [
                sys.executable, str(PYTHON_DIR / "tts/gemini_multi.py"),
                "--voice", "Kore", text, str(intermediate),
            ]
            result = subprocess.run(args, cwd=PYTHON_DIR, text=True,
                                    capture_output=True, timeout=150)
            if result.returncode or not has_audio(intermediate):
                raise RuntimeError(
                    f"{relative}: Gemini failed (exit {result.returncode}): "
                    f"{(result.stderr + result.stdout)[-650:]}"
                )
            intermediate.replace(target)
            return relative

    failures = []
    print(f"Gemini Kore English generation: {len(pending)} missing files, {workers} workers", flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(generate, job): job[1] for job in pending}
        for index, future in enumerate(concurrent.futures.as_completed(futures), 1):
            try:
                relative = future.result()
                print(f"English {index}/{len(pending)}: {relative}", flush=True)
            except Exception as exc:
                failures.append(str(exc))
                print(f"English FAILURE: {exc}", file=sys.stderr, flush=True)
    if failures:
        raise RuntimeError(f"{len(failures)} English clips failed; rerun the stage to resume.")


def english_gtts(uniform_dialogue: bool = False) -> None:
    """Last-resort English audio, keeping the complete English dialogue one voice.

    Existing audio is preserved by default. With --uniform-dialogue, rebuild
    all English dialogue in one gTTS voice if Gemini only generated some lines.
    Regenerate all English with Chatterbox when the local GPU is available.
    """
    from gtts import gTTS
    jobs, _ = audio_jobs()
    for idx, (text, rel) in enumerate(jobs, 1):
        target = AUDIO / rel
        if has_audio(target) and not (uniform_dialogue and rel.startswith("conversation/")):
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=target.parent) as tmp:
            temp = Path(tmp) / "clip.mp3"
            gTTS(text=text, lang="en", tld="com", slow=False).save(str(temp))
            if not has_audio(temp):
                raise RuntimeError(f"gTTS English produced invalid audio: {rel}")
            temp.replace(target)
            print(f"English gTTS fallback {idx}/{len(jobs)}: {rel}", flush=True)


def vietnamese_audio() -> None:
    sys.path.insert(0, str(PYTHON_DIR))
    from tts.gtts_vie import synthesize_to_file
    _, jobs = audio_jobs()
    for idx, (text, relative) in enumerate(jobs, 1):
        target = AUDIO / relative
        if has_audio(target):
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            synthesize_to_file(text, target, fmt="mp3", lang="vi")
            if not has_audio(target):
                raise RuntimeError(f"Invalid Vietnamese audio: {target}")
        except Exception:
            target.unlink(missing_ok=True)
            target.with_suffix(".mp3.part").unlink(missing_ok=True)
            raise
        print(f"Vietnamese {idx}/{len(jobs)}: {relative}", flush=True)


def context_audio() -> None:
    target = AUDIO / "context/vie/context.mp3"
    if has_audio(target):
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable, str(PYTHON_DIR / "tts/gemini_multi.py"),
        "--voice", "Kore", CONTEXT, str(target),
    ]
    try:
        subprocess.run(cmd, cwd=PYTHON_DIR, check=True)
        if not has_audio(target):
            raise RuntimeError("Gemini did not create a valid context MP3")
    except Exception:
        target.unlink(missing_ok=True)
        raise


def validate() -> None:
    if not PAGE.exists():
        raise RuntimeError("No lesson webpage. Run --stage page first.")
    text = PAGE.read_text(encoding="utf-8")
    refs = re.findall(r'(?:src|json|audiopath)="(/?audio/[^"]+)"', text)
    missing = []
    for ref in refs:
        # References to common heading audio resolve from the frontend static tree.
        p = ROOT / "frontend/static" / ref.lstrip("/")
        if not p.exists():
            missing.append(str(p))
    for folder in ["think-and-speak", "conversation"]:
        transcript = AUDIO / folder / "conversation.json"
        lines = json.loads(transcript.read_text(encoding="utf-8"))
        if len(lines) != 12:
            missing.append(f"{folder}: expected 12 conversation lines, found {len(lines)}")
        for line in lines:
            file = AUDIO / folder / line["audio"]
            if not has_audio(file):
                missing.append(str(file))
    english, vietnamese = audio_jobs()
    for _text, rel in english + vietnamese:
        if not has_audio(AUDIO / rel):
            missing.append(str(AUDIO / rel))
    if not has_audio(AUDIO / "context/vie/context.mp3"):
        missing.append("Missing context/vie/context.mp3")
    if missing:
        raise RuntimeError(f"Missing or invalid audio references ({len(missing)}):\n" + "\n".join(missing))
    print(f"All checks passed: {len(english)} English, {len(vietnamese)} Vietnamese, "
          "12 human recordings, context audio, transcripts and page references.", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("all", "page", "recordings", "english", "english-gemini", "english-gtts", "vietnamese",
                                            "context", "validate"), default="all")
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda",
                        help="Device for Chatterbox English TTS; CPU uses the same voice")
    parser.add_argument("--limit", type=int, help="For English audio, process only the first N jobs")
    parser.add_argument("--replace-english", nargs="+", default=[], metavar="PATH",
                        help="Regenerate specific English assets (or 'all') with Chatterbox")
    parser.add_argument("--workers", type=int, default=3,
                        help="Concurrent Gemini Kore TTS requests (1-4)")
    parser.add_argument("--uniform-dialogue", action="store_true",
                        help="With English gTTS, replace the entire dialogue with one voice")
    args = parser.parse_args()
    stage = args.stage
    try:
        if stage in ("all", "page"):
            build_page()
        if stage in ("all", "recordings"):
            convert_human_recordings()
        if stage in ("all", "vietnamese"):
            vietnamese_audio()
        if stage in ("all", "context"):
            context_audio()
        if stage in ("all", "english"):
            english_audio(device=args.device, limit=args.limit,
                          replace_paths=set(args.replace_english))
        if stage == "english-gemini":
            english_gemini(workers=args.workers, limit=args.limit)
        if stage == "english-gtts":
            english_gtts(uniform_dialogue=args.uniform_dialogue)
        if stage in ("all", "validate"):
            validate()
    except Exception as exc:
        print(f"ERROR in stage {stage}: {exc}", file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
