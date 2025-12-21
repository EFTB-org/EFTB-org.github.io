import torchaudio as ta
import torch
from chatterbox.tts import ChatterboxTTS

# from chatterbox.tts

# Load the Turbo model
model = ChatterboxTTS.from_pretrained(device="cuda")

# Generate with Paralinguistic Tags
text = "Hi there, Sarah here from MochaFone calling you back [chuckle], have you got one minute to chat about the billing issue?"

questions = {
    "Q1": "When is Christmas? A: The 25th of December. B: The 31st of December",
    "Q2": "What do people often do at Christmas? A: Celebrate with family and friends. B: Spend time alone",
    "Q3": "Who brings gifts to children at Christmas? A: Santa Claus. B: The Moon Boy",
    "Q4": "What color are Santa's clothes? A: Red and white. B: Black and blue",
    "Q5": "Is Santa kind or scary? A: Kind. B: Scary",
    "Q6": "What do people say at Christmas? A: Merry Christmas! B: Happy New Year!",
    "Q7": "What do children hang to get gifts? A: Stockings. B: Hats",
    "Q8": "What falls from the sky in the winter in many countries? A: Snow. B: Sun",
    "Q9": "Where do many people go on Christmas night? A: Church. B: Pagoda",
    "Q10": "What do people often give each other at Christmas? A: Gifts. B: Shoes",
}

out_dir = "../frontend/static/audio/christmas_2025/questions"

for q, text in questions.items():
    # Generate audio (requires a reference clip for voice cloning)
    wav = model.generate(text, audio_prompt_path="./kore_audio_prompt.wav")

    ta.save(f"{out_dir}/{q}.wav", wav, model.sr)