import json
import os
import torch
import torchaudio as ta
from chatterbox.tts import ChatterboxTTS
from pathlib import Path
from pydub import AudioSegment
import argparse

def wav_to_mp3(wav_path, mp3_path):
    print(f"Converting {wav_path} to {mp3_path}")
    audio = AudioSegment.from_wav(wav_path)
    # Set frame rate to 44100 and channels to 2 for consistency
    audio = audio.set_frame_rate(44100).set_channels(2)
    audio.export(mp3_path, format="mp3", bitrate="192k")

def main():
    parser = argparse.ArgumentParser(description="Generate lesson audios from JSON using Chatterbox TTS.")
    parser.add_argument("json_file", help="Path to the JSON configuration file.")
    parser.add_argument("--section", help="Only generate audios for a specific section name.")
    parser.add_argument("--clean", action="store_true", help="Remove temporary WAV files after conversion.")
    
    args = parser.parse_args()
    
    with open(args.json_file, "r") as f:
        config = json.load(f)
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    model = ChatterboxTTS.from_pretrained(device=device)
    
    # Audio prompt
    script_dir = Path(__file__).parent.absolute()
    audio_prompt_path = str(script_dir / "kore_audio_prompt.wav")
    
    # Project root is one level up from the script's directory
    project_root = script_dir.parent
    
    for section in config["sections"]:
        if args.section and section["name"] != args.section:
            continue
            
        # If path is relative, make it relative to project root
        section_dir = Path(section["dir"])
        if not section_dir.is_absolute():
            out_dir = project_root / section_dir
        else:
            out_dir = section_dir
            
        out_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"Processing section: {section['name']} -> {out_dir}")
        
        for slug, text in section["items"].items():
            print(f"  Generating: {slug} -> '{text}'")
            wav = model.generate(text, audio_prompt_path=audio_prompt_path)
            
            wav_path = out_dir / f"{slug}.wav"
            mp3_path = out_dir / f"{slug}.mp3"
            
            ta.save(str(wav_path), wav, model.sr)
            
            # Convert to MP3
            wav_to_mp3(str(wav_path), str(mp3_path))
            
            if args.clean:
                wav_path.unlink()
                print(f"  Cleaned: {wav_path}")

if __name__ == "__main__":
    main()
