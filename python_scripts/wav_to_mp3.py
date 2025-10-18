import os
import sys
from pydub import AudioSegment


def convert_wav_to_mp3(directory):
  # Check if the directory exists
  if not os.path.isdir(directory):
    print(f"The directory {directory} does not exist.")
    return

  # Iterate over all files in the directory
  for filename in os.listdir(directory):
    if filename.endswith(".wav"):
      wav_path = os.path.join(directory, filename)
      mp3_filename = os.path.splitext(filename)[0] + ".mp3"
      mp3_path = os.path.join(directory, mp3_filename)

      # Load the WAV file
      audio = AudioSegment.from_wav(wav_path)
      audio = audio.set_frame_rate(24000)
      audio = audio.set_channels(1)

      # Export as MP3
      audio.export(mp3_path, format="mp3")
      print(f"Converted {wav_path} to {mp3_path}")


if __name__ == "__main__":
  if len(sys.argv) != 2:
    print("Usage: python convert_wav_to_mp3.py <directory>")
  else:
    directory = sys.argv[1]
    convert_wav_to_mp3(directory)
