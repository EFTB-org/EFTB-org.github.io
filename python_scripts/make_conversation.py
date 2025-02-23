import argparse
import os
import re

import numpy as np
import soundfile as sf
from nltk.tokenize import sent_tokenize
from rich.console import Console
from rich.progress import BarColumn, Progress, TextColumn

from make_audios import SpeechGenerator

console = Console()


def get_sound_effect(effect_name):
    """Get the path to a sound effect file"""
    effect_name = effect_name.lower().strip("()")
    data, sample_rate = sf.read(os.path.join("sound_effects", f"{effect_name}.wav"))
    return data


def extract_sound_effects(text):
    """Extract sound effects from text and return cleaned text and effects list"""
    effects = re.findall(r"\([A-Z]+\)", text)
    clean_text = text
    for effect in effects:
        clean_text = clean_text.replace(effect, "")

    return clean_text.strip(), effects


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Input file")
    parser.add_argument("--speed", help="Speed of the audio", default=1.0)
    parser.add_argument("--begin_duration", help="", default=1.0)
    parser.add_argument("--pause_between", help="", default=0.5)
    parser.add_argument("output", help="Output file")

    args = parser.parse_args()

    with open(args.input, "r") as f:
        inputs = f.read()
        # lines = f.readlines()
        # lines = [line.replace("\n", "").strip() for line in lines]

    voice_map_str = inputs.split("--")[0]
    script = inputs.split("--")[1]

    voice_map = {}
    for line in voice_map_str.split("\n"):
        line = line.strip()
        if len(line) == 0:
            continue
        speaker, voice = line.split("=")
        voice_map[speaker] = voice

    print(voice_map)

    conversation = []

    for line in script.split("\n"):
        line = line.strip()
        if len(line) == 0:
            continue
        speaker, text = line.split(": ")
        conversation.append((speaker, text))

    # print(conversation)

    speech_generator = SpeechGenerator()

    speechs = []
    progress = Progress(
        "[progress.description]{task.description}",
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TextColumn("[progress.remaining]{task.completed}/{task.total}"),
        console=console,
    )

    with progress:
        task = progress.add_task("[cyan]Generating audios...", total=len(conversation))

        for i, (speaker, text) in enumerate(conversation):
            sen_audios = []
            text, effects = extract_sound_effects(text)

            console.print(f"Text: {text}", f"Effects: {effects}")
            if speaker != "effect":
                voice = speech_generator.get_voice(voice_map[speaker])

                sentences = sent_tokenize(text)
                sentences = [text]

                for sentence in sentences:
                    sentence_audio = speech_generator.generate(
                        sentence, voice, speed=float(args.speed), begin_duration=0
                    )

                    sen_audios.append(sentence_audio)

            sen_audios += [get_sound_effect(effect) for effect in effects]
            line = np.zeros(1)

            for sen_audio in sen_audios:
                line = np.concatenate((line, sen_audio), axis=0)
                line = np.concatenate((line, np.zeros((int(0.2 * 24000)))), axis=0)

            speechs.append(line)
            progress.update(task, advance=1)

    final_audio = np.zeros((int(args.begin_duration * 24000)))
    for i, speech in enumerate(speechs):
        final_audio = np.concatenate((final_audio, speech), axis=0)
        final_audio = np.concatenate(
            (final_audio, np.zeros((int(args.pause_between * 24000)))), axis=0
        )

    sf.write(args.output, final_audio, 24000)


if __name__ == "__main__":
    main()
