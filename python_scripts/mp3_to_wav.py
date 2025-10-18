import os
import sys
from pydub import AudioSegment


def convert_mp3_to_wav(directory):
    # Check if the directory exists
    if not os.path.isdir(directory):
        print(f"The directory {directory} does not exist.")
        return

    # Iterate over all files in the directory
    for filename in os.listdir(directory):
        if filename.endswith(".mp3"):
            mp3_path = os.path.join(directory, filename)
            wav_filename = os.path.splitext(filename)[0] + ".wav"
            wav_path = os.path.join(directory, wav_filename)

            # Load the MP3 file
            audio = AudioSegment.from_mp3(mp3_path)
            audio = audio.set_frame_rate(24000)
            audio = audio.set_channels(1)

            # Export as WAV
            audio.export(wav_path, format="wav")
            print(f"Converted {mp3_path} to {wav_path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python convert_mp3_to_wav.py <directory>")
    else:
        directory = sys.argv[1]
        convert_mp3_to_wav(directory)
