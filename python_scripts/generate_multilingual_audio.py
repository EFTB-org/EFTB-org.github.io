#!/usr/bin/env python3
"""
Multilingual Text-to-Speech Generator using Google Gemini API
Useful for sentences containing mixed languages (e.g. English + Vietnamese names).
"""

import argparse
import os
import sys
import struct
import mimetypes
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables
load_dotenv()

def save_binary_file(file_name, data):
    """Save binary data to file."""
    with open(file_name, "wb") as f:
        f.write(data)
    print(f"File saved to: {file_name}")

def parse_audio_mime_type(mime_type: str) -> dict[str, int]:
    """Parses bits per sample and rate from an audio MIME type string."""
    bits_per_sample = 16
    rate = 24000

    # Extract rate from parameters
    parts = mime_type.split(";")
    for param in parts:
        param = param.strip()
        if param.lower().startswith("rate="):
            try:
                rate_str = param.split("=", 1)[1]
                rate = int(rate_str)
            except (ValueError, IndexError):
                pass  # Keep rate as default
        elif param.startswith("audio/L"):
            try:
                bits_per_sample = int(param.split("L", 1)[1])
            except (ValueError, IndexError):
                pass  # Keep bits_per_sample as default
    
    return {"bits_per_sample": bits_per_sample, "rate": rate}

def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """Generates a WAV file header for the given audio data."""
    parameters = parse_audio_mime_type(mime_type)
    bits_per_sample = parameters["bits_per_sample"]
    sample_rate = parameters["rate"]
    num_channels = 1
    
    data_size = len(audio_data)
    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = sample_rate * block_align
    chunk_size = 36 + data_size

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", chunk_size, b"WAVE", b"fmt ", 16, 1, num_channels, 
        sample_rate, byte_rate, block_align, bits_per_sample, b"data", data_size
    )
    return header + audio_data

def _save_as_mp3(audio_data, output_file):
    """Save audio data as MP3 using ffmpeg."""
    wav_file = output_file.replace('.mp3', '.wav')
    save_binary_file(wav_file, audio_data)

    try:
        import subprocess
        result = subprocess.run(['ffmpeg', '-i', wav_file, '-y', output_file],
                              capture_output=True, text=True)
        if result.returncode == 0:
            os.remove(wav_file)
            print(f"Converted to MP3: {output_file}")
            return output_file
        else:
            print(f"Warning: ffmpeg conversion failed. Keeping WAV: {wav_file}")
            return wav_file
    except FileNotFoundError:
        print(f"Warning: ffmpeg not found. Keeping WAV: {wav_file}")
        return wav_file

def generate_audio(text, output_file, voice_name="Puck"):
    """Generate TTS audio for a single text string."""
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

    print(f"Generating audio for: '{text}'")
    print(f"Voice: {voice_name}")

    model = "gemini-2.5-flash-preview-tts"

    generate_content_config = types.GenerateContentConfig(
        temperature=1,
        response_modalities=["audio"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name=voice_name
                )
            ),
        ),
    )

    prompt = f"Read this text naturally. If there are Vietnamese names or phrases, pronounce them correctly in Vietnamese context while keeping the English flow: {text}"

    max_retries = 3
    for attempt in range(max_retries + 1):
        try:
            audio_chunks = []
            for chunk in client.models.generate_content_stream(
                model=model,
                contents=prompt,
                config=generate_content_config,
            ):
                if chunk.candidates and chunk.candidates[0].content.parts:
                    inline_data = chunk.candidates[0].content.parts[0].inline_data
                    if inline_data and inline_data.data:
                        data = inline_data.data
                        # Handle MIME type if present to ensure correct format
                        mime_type = inline_data.mime_type or "audio/wav"
                        if mime_type and "audio/L16" in mime_type: # Raw PCM
                             data = convert_to_wav(data, mime_type)
                        
                        audio_chunks.append(data)

            if not audio_chunks:
                print("Error: No audio data received.")
                return

            combined_audio = b''.join(audio_chunks)
            
            # Check if it starts with RIFF (WAV header)
            if not combined_audio.startswith(b'RIFF'):
                 # If strictly raw PCM without mime type info, we might need to wrap it.
                 # But usually the previous check handles it. 
                 # Let's assume if it's not RIFF, it might be raw PCM default.
                 combined_audio = convert_to_wav(combined_audio, "audio/wav")

            if output_file.endswith('.mp3'):
                _save_as_mp3(combined_audio, output_file)
            else:
                save_binary_file(output_file, combined_audio)
            
            # If successful, break the retry loop
            break

        except Exception as e:
            error_str = str(e)
            if ("429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower()) and attempt < max_retries:
                wait_time = 2 ** attempt
                print(f"Rate limit hit. Waiting {wait_time} seconds before retry {attempt + 1}/{max_retries}...")
                import time
                time.sleep(wait_time)
                continue
            else:
                print(f"Error generating audio: {e}")
                sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Generate multilingual audio using Gemini TTS")
    parser.add_argument("text", help="Text to convert to speech")
    parser.add_argument("output_file", help="Path to save the audio file")
    parser.add_argument("--voice", default="Puck", help="Voice name (Puck, Kore, etc.)")
    
    args = parser.parse_args()
    
    # Ensure output directory exists
    output_path = Path(args.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    generate_audio(args.text, args.output_file, args.voice)

if __name__ == "__main__":
    main()
