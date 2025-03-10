import argparse
import os
import random
import re
import unicodedata

import mdpd
import numpy as np
import soundfile as sf
import torch
from kokoro import KPipeline
from rich.console import Console
from rich.progress import BarColumn, Progress, TextColumn

console = Console()


def normalize_filename(text):
    """
    Normalize a text string to make it suitable for use as a filename.

    Parameters:
    text (str): The input text to normalize.

    Returns:
    str:The normalized filename.
    """
    # Normalize Unicode characters to their closest ASCII representation
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")

    # Replace spaces with underscores
    text = text.replace(" ", "_")

    # Remove or replace any characters that are not alphanumeric or underscores
    text = re.sub(r"[^a-zA-Z0-9_]", "", text)

    # Convert to lowercase (optional, depending on your preference)
    text = text.lower()

    return text


class SpeechGenerator:
    def __init__(self, voice_pack_path="voices-v1.0.bin"):
        self.pipeline = KPipeline(lang_code="a")

        self.voice_pack = np.load(voice_pack_path)

        self.available_voices = list(self.voice_pack.keys())

        self.device = "cuda" if torch.cuda.is_available() else "cpu"

    def mix_voice(self, voice_a, voice_b, ratio=0.5):
        voice_a = torch.from_numpy(self.voice_pack[voice_a]).to(self.device)
        voice_b = torch.from_numpy(self.voice_pack[voice_b]).to(self.device)

        return voice_a * (1 - ratio) + voice_b * ratio

    def get_voice(self, voice):
        return torch.from_numpy(self.voice_pack[voice]).to(self.device)

    def generate(
        self,
        text,
        voice,
        save_path=None,
        begin_duration=0.8,
        silent_duration=0.4,
        speed=1.0,
    ):
        self.pipeline.voices["mixed_voice"] = voice.squeeze(0)

        generator = self.pipeline(
            text, voice="mixed_voice", speed=speed, split_pattern="<br>"
        )

        final_audio = np.zeros((int(begin_duration * 24000)))
        # console.log(text.split("\n"))
        for i, (gs, ps, audio) in enumerate(generator):
            final_audio = np.concatenate((final_audio, audio), axis=0)
            final_audio = np.concatenate(
                (final_audio, np.zeros((int(silent_duration * 24000)))), axis=0
            )

        if save_path:
            sf.write(save_path, final_audio, 24000)
        else:
            return final_audio


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("unit", help="Unit name")
    parser.add_argument("type", help="vocabularies or sentences")
    parser.add_argument("input", help="Input file")
    parser.add_argument("--speed", help="Speed of the audio", default=1.0)
    # parser.add_argument("output", help="Output file")

    args = parser.parse_args()

    speech_generator = SpeechGenerator()

    # speech_generator.generate("Hello. This audio generated by kokoro!")
    # return

    with open(args.input, "r") as f:
        data = f.read()

    # df = pd.read_csv(StringIO(data.strip()), sep="|", skipinitialspace=True)
    df = mdpd.from_md(data)

    progress = Progress(
        "[progress.description]{task.description}",
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TextColumn("[progress.remaining]{task.completed}/{task.total}"),
        console=console,
    )

    voices = {
        # "af_nicole": speech_generator.get_voice("af_nicole"),
        "am_michael": speech_generator.get_voice("am_michael"),
        "am_puck": speech_generator.get_voice("am_puck"),
        # "am_onyx": speech_generator.get_voice("am_onyx"),
        # "am_adam": speech_generator.get_voice("am_adam"),
        "af_sarah": speech_generator.get_voice("af_sarah"),
        "af_bella": speech_generator.get_voice("af_bella"),
        "af_bella&am_michael": speech_generator.mix_voice(
            "af_bella", "am_michael", 0.5
        ),
    }

    os.makedirs(f"../static/audio/{args.unit}/{args.type}", exist_ok=True)

    map_voices = {
        0: "af_bella",
        1: "am_michael",
        3: "am_puck",
    }

    audio_buttons = []
    with progress:
        task = progress.add_task("[green]Making sounds ...", total=len(df))
        for i, row in df.iterrows():
            if i in list(map_voices.keys()):
                voice = map_voices[i]
            else:
                voice = random.choice(list(voices.keys()))
            text = f"{row['cleaned'].replace('**', '')}"
            print(i, voice, text)
            # console.log(f"Using voice: {voice} for text: {text}")
            path = f"audio/{args.unit}/{args.type}/{i:02}_{
                normalize_filename(row['cleaned'])
            }.wav"
            save_path = "../static/" + path
            voice = voices[voice]
            speech_generator.generate(
                text, voice, save_path=save_path, speed=float(args.speed)
            )
            audio_buttons.append("{{" + f'<audio-player src="{path}">' + "}}")
            progress.update(task, advance=1)

    # df["Audio"] = audio_buttons

    df.insert(0, "Audio", audio_buttons)

    df.drop(columns=["cleaned"], inplace=True)
    df.to_markdown(f"{args.input[:-3]}_audio.md", index=False)


if __name__ == "__main__":
    main()
