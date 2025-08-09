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
from pathlib import Path
from google import genai
from google.genai import types


def wave_file(filename, pcm, channels=1, rate=24000, sample_width=2):
    """Save PCM data to a wave file."""
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)


def mp3_file(filename, pcm, channels=1, rate=24000, sample_width=2):
    """Save PCM data to an MP3 file by first creating WAV then converting."""
    # First save as WAV
    wav_filename = filename.replace('.mp3', '.wav')
    wave_file(wav_filename, pcm, channels, rate, sample_width)

    # Convert WAV to MP3 (requires ffmpeg)
    try:
        import subprocess
        result = subprocess.run(['ffmpeg', '-i', wav_filename, '-y', filename],
                              capture_output=True, text=True)
        if result.returncode == 0:
            # Remove temporary WAV file
            os.remove(wav_filename)
            return True
        else:
            print(f"Warning: Could not convert to MP3, keeping WAV file: {wav_filename}")
            return False
    except FileNotFoundError:
        print(f"Warning: ffmpeg not found, keeping WAV file: {wav_filename}")
        return False


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
    start_index = max(0, current_index - 3)

    for i in range(start_index, current_index):
        prev_item = conversation[i]
        context_lines.append(f"{prev_item['speaker']}: {prev_item['text']}")

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
        f"",
        f"TTS the following line of conversation of {current_speaker}:",
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


def generate_line_audio(prompt, speaker, voice_name, output_file):
    """Generate TTS audio for a single line."""
    print(prompt)

    print("-" * 50)
    return
    client = genai.Client()

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-tts",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=voice_name,
                        )
                    )
                )
            )
        )

        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            data = response.candidates[0].content.parts[0].inline_data.data

            # Try to save as MP3, fallback to WAV
            if output_file.endswith('.mp3'):
                success = mp3_file(output_file, data)
                if not success:
                    # Fallback to WAV
                    wav_file = output_file.replace('.mp3', '.wav')
                    wave_file(wav_file, data)
                    return wav_file
            else:
                wave_file(output_file, data)

            return output_file
        else:
            print(f"Error: No audio data received from API for {speaker}")
            return None

    except Exception as e:
        print(f"Error generating TTS for {speaker}: {e}")
        return None


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
        voice_name = get_voice_for_speaker(speaker, voice_mapping, default_voices, i)
        speaker_voices[speaker] = voice_name

    # Print voice assignments
    print("\nVoice assignments:")
    for speaker, voice in speaker_voices.items():
        print(f"  {speaker}: {voice}")

    # Generate audio for each line
    print(f"\nGenerating audio files...")
    successful_files = []
    failed_files = []

    # Count lines per speaker for numbering
    speaker_counts = {}

    for i, item in enumerate(conversation):
        speaker = item['speaker']

        # Update speaker line count
        if speaker not in speaker_counts:
            speaker_counts[speaker] = 0
        speaker_counts[speaker] += 1

        # Create context prompt
        prompt = create_context_prompt(conversation, i, speakers)

        # Generate filename
        line_number = speaker_counts[speaker]
        filename = f"{speaker} - {line_number}.{args.format}"
        output_file = output_dir / filename

        print(f"  Generating: {filename}")

        # Generate audio
        voice_name = speaker_voices[speaker]
        result_file = generate_line_audio(prompt, speaker, voice_name, str(output_file))

        if result_file:
            successful_files.append(result_file)
        else:
            failed_files.append(filename)

    # Summary
    print(f"\nGeneration complete!")
    print(f"Successful: {len(successful_files)} files")
    if failed_files:
        print(f"Failed: {len(failed_files)} files")
        print("Failed files:", ", ".join(failed_files))

    print(f"\nAudio files saved in: {output_dir}")


if __name__ == "__main__":
    main()
