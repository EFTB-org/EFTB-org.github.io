#!/usr/bin/env python3
import argparse
from pydub import AudioSegment
import os


def increase_volume(input_file, output_file, volume_increase_db):
    """
    Increase the volume of an MP3 file by a specified amount in decibels.

    Parameters:
        input_file (str): Path to the input MP3 file
        output_file (str): Path to save the modified MP3 file
        volume_increase_db (float): Amount to increase volume in decibels (positive values)
    """
    try:
        # Check if input file exists
        if not os.path.exists(input_file):
            return f"Error: Input file '{input_file}' not found."

        # Load the audio file
        sound = AudioSegment.from_mp3(input_file)

        # Increase the volume
        louder_sound = sound + volume_increase_db

        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Export the result
        louder_sound.export(output_file, format="mp3")

        return f"Successfully increased volume by {volume_increase_db}dB and saved to '{output_file}'"

    except Exception as e:
        return f"Error processing the audio file: {e}"


def main():
    # Create argument parser
    parser = argparse.ArgumentParser(
        description="Increase the volume of an MP3 file",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Add arguments
    parser.add_argument("input_file", help="Path to the input MP3 file")
    parser.add_argument(
        "-o",
        "--output",
        dest="output_file",
        help="Path to save the modified MP3 file (default: adds '_louder' suffix)",
    )
    parser.add_argument(
        "-v",
        "--volume",
        dest="volume_increase",
        type=float,
        default=6.0,
        help="Amount to increase volume in decibels (positive values)",
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="Suppress output messages"
    )

    # Parse arguments
    args = parser.parse_args()

    # If output file not specified, create one based on input filename
    if not args.output_file:
        base, ext = os.path.splitext(args.input_file)
        args.output_file = f"{base}_louder{ext}"

    # Process the file
    result = increase_volume(args.input_file, args.output_file, args.volume_increase)

    # Print result unless quiet mode is on
    if not args.quiet:
        print(result)

    # Return success/failure for script exit code
    return 0 if "Successfully" in result else 1


if __name__ == "__main__":
    exit(main())
