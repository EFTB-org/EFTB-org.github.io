#!/usr/bin/env python3
"""
Text-to-Speech Generator using Google Gemini API
Converts conversation JSON files to individual audio files per speaker line.
"""

import argparse
import json
import sys
import wave
import os
import time
import re
import struct
import mimetypes
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables from .env file
load_dotenv()

class KeyManager:
    """Manages multiple API keys for load balancing."""
    def __init__(self):
        self.keys = []
        self._load_keys()
        self.current_index = 0

    def _load_keys(self):
        # Try loading from GEMINI_API_KEYS (comma separated)
        keys_str = os.environ.get("GEMINI_API_KEYS")
        if keys_str:
            self.keys = [k.strip() for k in keys_str.split(",") if k.strip()]
        
        # Fallback/Add GEMINI_API_KEY
        single_key = os.environ.get("GEMINI_API_KEY")
        if single_key and single_key not in self.keys:
            self.keys.append(single_key)
        
        if not self.keys:
            print("Warning: No Gemini API keys found in environment variables.")

    def get_next_key(self):
        """Get the next API key in rotation."""
        if not self.keys:
            return None
        
        key = self.keys[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.keys)
        return key

# Initialize global key manager
key_manager = KeyManager()

def save_binary_file(file_name, data):
    """Save binary data to file."""
    with open(file_name, "wb") as f:
        f.write(data)
    print(f"File saved to: {file_name}")


def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """Generates a WAV file header for the given audio data and parameters.

    Args:
        audio_data: The raw audio data as a bytes object.
        mime_type: Mime type of the audio data.

    Returns:
        A bytes object representing the WAV file header.
    """
    parameters = parse_audio_mime_type(mime_type)
    bits_per_sample = parameters["bits_per_sample"]
    sample_rate = parameters["rate"]
    num_channels = 1
    data_size = len(audio_data)
    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = sample_rate * block_align
    chunk_size = 36 + data_size  # 36 bytes for header fields before data chunk size

    # http://soundfile.sapp.org/doc/WaveFormat/
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",          # ChunkID
        chunk_size,       # ChunkSize (total file size - 8 bytes)
        b"WAVE",          # Format
        b"fmt ",          # Subchunk1ID
        16,               # Subchunk1Size (16 for PCM)
        1,                # AudioFormat (1 for PCM)
        num_channels,     # NumChannels
        sample_rate,      # SampleRate
        byte_rate,        # ByteRate
        block_align,      # BlockAlign
        bits_per_sample,  # BitsPerSample
        b"data",          # Subchunk2ID
        data_size         # Subchunk2Size (size of audio data)
    )
    return header + audio_data


def parse_audio_mime_type(mime_type: str) -> dict[str, int]:
    """Parses bits per sample and rate from an audio MIME type string.

    Assumes bits per sample is encoded like "L16" and rate as "rate=xxxxx".

    Args:
        mime_type: The audio MIME type string (e.g., "audio/L16;rate=24000").

    Returns:
        A dictionary with "bits_per_sample" and "rate" keys.
    """
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


def load_conversation_from_json(json_path):
   """Load conversation from JSON file."""
   try:
      with open(json_path, 'r', encoding='utf-8') as f:
            conversation = json.load(f)
   except FileNotFoundError:
      print(f"Error: File {json_path} not found.")
      sys.exit(1)
   except json.JSONDecodeError as e:
      print(f"Error: Invalid JSON in {json_path}: {e}")
      sys.exit(1)

   return conversation


def get_speakers(conversation):
   """Get unique speakers in order of appearance."""
   speakers = []
   seen_speakers = set()
   for item in conversation:
      speaker = item['speaker']
      if speaker not in seen_speakers:
            speakers.append(speaker)
            seen_speakers.add(speaker)
   return speakers


def create_context_prompt(conversation, current_index, speakers):
    """Create context prompt for current line."""
    current_item = conversation[current_index]
    current_speaker = current_item['speaker']
    current_text = current_item['text']

    # Build context from previous lines (up to 3 previous lines for context)
    context_lines = []
    start_index = 0

    for i in range(start_index, current_index):
        prev_item = conversation[i]
        context_lines.append(f"{prev_item['speaker']} | {prev_item['text']}")

    # Create the prompt
    speakers_list = ' and '.join(speakers)
    prompt_parts = [
        f"This is the context of the conversation between {speakers_list}:"
    ]

    if context_lines:
        prompt_parts.extend(["<previous conversation>"])
        prompt_parts.extend(context_lines)
        prompt_parts.extend(["</previous conversation>"])
    else:
        prompt_parts.append("(Beginning of conversation)")

    prompt_parts.extend([
        "",
        f"TTS the following line of conversation above of {current_speaker}:",
        f"{current_speaker}: {current_text}"
    ])

    return "\n".join(prompt_parts)


def parse_voice_mapping(voice_mapping_str):
   """Parse voice mapping string in format 'speaker1:voice1,speaker2:voice2'."""
   if not voice_mapping_str:
      return {}

   voice_mapping = {}
   try:
      for mapping in voice_mapping_str.split(','):
            speaker, voice = mapping.strip().split(':')
            voice_mapping[speaker.strip()] = voice.strip()
   except ValueError:
      print("Error: Voice mapping should be in format 'speaker1:voice1,speaker2:voice2'")
      sys.exit(1)

   return voice_mapping


def get_voice_for_speaker(speaker, voice_mapping, default_voices, speaker_index):
   """Get voice name for a specific speaker."""
   if voice_mapping and speaker in voice_mapping:
      return voice_mapping[speaker]
   else:
      return default_voices[speaker_index % len(default_voices)]


def extract_retry_delay(error_message):
   """Extract retry delay from error message."""
   # Look for retryDelay in the error message
   match = re.search(r"'retryDelay': '(\d+)s'", str(error_message))
   if match:
      return int(match.group(1))
   return None


def is_rate_limit_error(error):
   """Check if the error is a rate limit error."""
   error_str = str(error)
   return ("429" in error_str and "RESOURCE_EXHAUSTED" in error_str) or \
         ("quota" in error_str.lower()) or \
         ("rate limit" in error_str.lower())


def generate_line_audio_with_retry(prompt, speaker, voice_name, output_file, log_prompts=False, max_retries=3):
   """Generate TTS audio for a single line with retry logic for rate limiting."""

   for attempt in range(max_retries + 1):
      # Get a key for this attempt (rotates on each call)
      api_key = key_manager.get_next_key()
      
      try:
            return generate_line_audio(prompt, speaker, voice_name, output_file, log_prompts, api_key)

      except Exception as e:
            if is_rate_limit_error(e) and attempt < max_retries:
               # Extract retry delay from error message
               retry_delay = extract_retry_delay(str(e))

               if retry_delay:
                  wait_time = retry_delay
               else:
                  # Exponential backoff: 1s, 2s, 4s, 8s, etc.
                  wait_time = 2 ** attempt

               print(f"Rate limit hit for {speaker} using key ...{api_key[-4:] if api_key else 'None'}.")
               
               # If we have multiple keys, try the next one immediately (with short delay)
               if len(key_manager.keys) > 1:
                     print(f"Switching to next API key (attempt {attempt + 1}/{max_retries})...")
                     time.sleep(1) # Short delay to prevent tight loop
               else:
                     print(f"Waiting {wait_time} seconds before retry {attempt + 1}/{max_retries}...")
                     time.sleep(wait_time)
               
               continue
            else:
               # Not a rate limit error or max retries exceeded
               print(f"Error generating TTS for {speaker}: {e}")
               return None

   return None


def generate_line_audio(prompt, speaker, voice_name, output_file, log_prompts=True, api_key=None):
    """Generate TTS audio for a single line using streaming API."""
    client = genai.Client(
        api_key=api_key,
    )

    # Log the prompt if requested
    if log_prompts:
        print(f"\n{'='*60}")
        print(f"PROMPT FOR: {speaker} -> {Path(output_file).name}")
        print(f"VOICE: {voice_name}")
        print(f"KEY: ...{api_key[-4:] if api_key else 'None'}")
        print(f"{'='*60}")
        print(prompt)
        print(f"{'='*60}\n")

    model = "gemini-2.5-flash-preview-tts"
    # return

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

    # try:
    audio_chunks = []
    for chunk in client.models.generate_content_stream(
        model=model,
        contents=prompt,
        config=generate_content_config,
    ):
        if not _has_audio_data(chunk):
            continue

        inline_data = chunk.candidates[0].content.parts[0].inline_data
        if inline_data.data and inline_data.mime_type:
            data_buffer = _process_audio_data(inline_data)
            audio_chunks.append(data_buffer)

    if audio_chunks:
        return _save_audio_file(audio_chunks, output_file)
    else:
        print(f"Error: No audio data received from API for {speaker}")
        return None

    # except Exception as e:
    #     print(f"Error generating TTS for {speaker}: {e}")
    #     return None


def _has_audio_data(chunk):
    """Check if chunk contains audio data."""
    return (chunk.candidates and
            chunk.candidates[0].content and
            chunk.candidates[0].content.parts and
            chunk.candidates[0].content.parts[0].inline_data and
            chunk.candidates[0].content.parts[0].inline_data.data)


def _process_audio_data(inline_data):
    """Process audio data and convert to WAV if needed."""
    data_buffer = inline_data.data
    mime_type = inline_data.mime_type or "audio/wav"

    file_extension = mimetypes.guess_extension(mime_type)
    if file_extension is None:
        data_buffer = convert_to_wav(data_buffer, mime_type)

    return data_buffer


def _save_audio_file(audio_chunks, output_file):
    """Save combined audio chunks to file."""
    combined_audio = b''.join(audio_chunks)

    if output_file.endswith('.mp3'):
        return _save_as_mp3(combined_audio, output_file)
    else:
        save_binary_file(output_file, combined_audio)
        return output_file


def _save_as_mp3(audio_data, output_file):
    """Save audio data as MP3, with WAV fallback."""
    wav_file = output_file.replace('.mp3', '.wav')
    save_binary_file(wav_file, audio_data)

    try:
        import subprocess
        result = subprocess.run(['ffmpeg', '-i', wav_file, '-y', output_file],
                              capture_output=True, text=True)
        if result.returncode == 0:
            os.remove(wav_file)
            return output_file
        else:
            print(f"Warning: Could not convert to MP3, keeping WAV: {wav_file}")
            return wav_file
    except FileNotFoundError:
        print(f"Warning: ffmpeg not found, keeping WAV: {wav_file}")
        return wav_file


def main():
   """Main CLI function."""
   parser = argparse.ArgumentParser(
      description="Convert conversation JSON to individual audio files per speaker line",
      formatter_class=argparse.RawDescriptionHelpFormatter,
      epilog="""
Examples:
%(prog)s conversation.json
%(prog)s conversation.json -o audio_output
%(prog)s conversation.json -v "Ty:Kore,Na:Puck"
%(prog)s conversation.json -v "Ty:Kore,Na:Puck" -o lesson6_audio

Available voices: Kore, Puck, Sage, Reed

Output files will be named: "<speaker> - <line_number>.mp3"
      """
   )

   parser.add_argument(
      'input_file',
      help='Path to the conversation JSON file'
   )

   parser.add_argument(
      '-o', '--output-dir',
      default='audio_output',
      help='Output directory for audio files (default: audio_output)'
   )

   parser.add_argument(
      '-v', '--voice-mapping',
      help='Voice mapping in format "speaker1:voice1,speaker2:voice2"'
   )

   parser.add_argument(
      '--format',
      choices=['mp3', 'wav'],
      default='mp3',
      help='Output audio format (default: mp3, requires ffmpeg)'
   )

   parser.add_argument(
      '--log-prompts',
      action='store_true',
      help='Log the TTS prompts to console for debugging'
   )

   parser.add_argument(
      '--max-retries',
      type=int,
      default=3,
      help='Maximum number of retries for rate-limited requests (default: 3)'
   )

   args = parser.parse_args()

   # Validate input file
   input_path = Path(args.input_file)
   if not input_path.exists():
      print(f"Error: Input file {args.input_file} does not exist.")
      sys.exit(1)

   # Create output directory
   output_dir = Path(args.output_dir)
   output_dir.mkdir(exist_ok=True)
   print(f"Output directory: {output_dir}")

   # Load conversation
   print(f"Loading conversation from {args.input_file}...")
   conversation = load_conversation_from_json(args.input_file)
   speakers = get_speakers(conversation)
   print(f"Found speakers: {', '.join(speakers)}")
   print(f"Total lines: {len(conversation)}")

   # Parse voice mapping
   voice_mapping = parse_voice_mapping(args.voice_mapping)
   if voice_mapping:
      print(f"Voice mapping: {voice_mapping}")

   # Default available voices
   default_voices = ['Kore', 'Puck', 'Sage', 'Reed']

   # Create speaker to voice mapping
   speaker_voices = {}
   for i, speaker in enumerate(speakers):
      voice_name = get_voice_for_speaker(
            speaker, voice_mapping, default_voices, i)
      speaker_voices[speaker] = voice_name

   # Print voice assignments
   print("\nVoice assignments:")
   for speaker, voice in speaker_voices.items():
      print(f"  {speaker}: {voice}")

   # Generate audio for each line
   print("\nGenerating audio files...")
   successful_files = []
   failed_files = []

   for i, item in enumerate(conversation):
      # if i < 5: continue
      speaker = item['speaker']

      # Create context prompt
      prompt = create_context_prompt(conversation, i, speakers)

      # Generate filename from JSON audio field
      json_filename = item['audio']

      # Handle format conversion if needed
      if args.format == 'wav' and json_filename.endswith('.mp3'):
            filename = json_filename.replace('.mp3', '.wav')
      elif args.format == 'mp3' and json_filename.endswith('.wav'):
            filename = json_filename.replace('.wav', '.mp3')
      else:
            filename = json_filename

      output_file = output_dir / filename

      # Check if file already exists
      if output_file.exists():
            print(f"  Skipping: {filename} (already exists)")
            successful_files.append(str(output_file))
            continue

      print(f"  Generating: {filename}")

      # Generate audio
      voice_name = speaker_voices[speaker]
      result_file = generate_line_audio_with_retry(
            prompt, speaker, voice_name, str(output_file), args.log_prompts, args.max_retries)

      if result_file:
            successful_files.append(result_file)
      else:
            failed_files.append(filename)

   # Summary
   print("\nGeneration complete!")
   print(f"Successful: {len(successful_files)} files")
   if failed_files:
      print(f"Failed: {len(failed_files)} files")
      print("Failed files:", ", ".join(failed_files))

   print(f"\nAudio files saved in: {output_dir}")


if __name__ == "__main__":
   main()
