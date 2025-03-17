import marimo

__generated_with = "0.11.20"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo
    import os
    return mo, os


@app.cell
def _():
    # sentences = [
    #     "Nice to meet you.",
    #     "I’d like you to meet my classmate.",
    #     "It’s great to meet you.",
    # ]
    # path = '../static/audio/lession-1/pactice'
    # os.makedirs(path, exist_ok=True)

    # speed = 0.8

    # speech_generator = SpeechGenerator()

    # voice = speech_generator.get_voice("af_bella")

    # for sentence in sentences:
    #     save_path = f"{path}/{normalize_filename(sentence)}.wav"
    #     print(save_path)
    #     speech_generator.generate(
    #         sentence, voice, save_path=save_path, speed=speed
    #     )
    return


@app.cell
def _():
    import re
    import unicodedata

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
    return normalize_filename, re, unicodedata


@app.cell
def _():
    from make_conversation import get_sound_effect, extract_sound_effects
    import numpy as np
    import soundfile as sf
    return extract_sound_effects, get_sound_effect, np, sf


@app.cell
def _():
    [
      {"type": "dialogue", "speaker": "Alice", "text": "Hello, how are you?", "audio": "alice_hello.mp3"},
      {"type": "effect", "name": "door creak", "audio": "door_creak.mp3"},
      {"type": "dialogue", "speaker": "Bob", "text": "I'm good, thanks!", "audio": "bob_response.mp3"}
    ]
    return


@app.cell
def _(normalize_filename):
    import json

    conversation_scripts = [
        """effect: soft park ambiance|parkambience
    John: Good morning, Mr. Parker! How are you?
    Mr. Parker: I'm fine, thank you! And you?
    John: I'm good. I just moved to a new house.
    Mr. Parker: Oh! Where is your house?
    """,
        """effect: 🍃 Wind blowing sound|wind
    John: Near the park. I come here every day.
    Mr. Parker: That's nice! Do you see the boss?
    John: Yes, our boss is at work now.
    """,
        """effect: 🚶 Footsteps approaching|rushing
    Mr. Parker: Huh? Look! A stranger is in the park.
    John: No, that's our new colleague!
    """,
    ]

    def make_json_script(conversation_scripts, save_path):
        for i, script in enumerate(conversation_scripts):
            conversation = []
            output = f"{save_path}/conversation_{i}.json"
            conversation = []
            for line in script.split("\n"):
                line = line.strip()
                if len(line) == 0:
                    continue
                speaker, text = line.split(": ")
                c_line = {}
                if speaker == 'effect':
                    c_line['type'] = "effect"
                    c_line['name'], soundname = text.split('|')
                    c_line['audio'] = soundname + '.wav'
                else:
                    c_line['type'] = "dialogue"
                    c_line['speaker'] = speaker
                    c_line['text'] = text
                    c_line['audio'] = normalize_filename(text) + '.wav'

                conversation.append(c_line)

            print(conversation)
            json.dump(conversation, open(output, 'w'), indent=2)

    make_json_script(conversation_scripts, "../static/audio/lession-1/pactice/")
        
    return conversation_scripts, json, make_json_script


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
