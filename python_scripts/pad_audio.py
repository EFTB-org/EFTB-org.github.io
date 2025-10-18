import os
import argparse
from pydub import AudioSegment

def add_silence_padding(input_file, output_file, padding_ms=2000):
    """Add silence padding to the beginning of an audio file."""
    try:
        # Load the audio file
        audio = AudioSegment.from_file(input_file)
        # Create silence
        silence = AudioSegment.silent(duration=padding_ms)
        # Add silence to the beginning of the audio
        padded_audio = silence + audio
        # Export the result
        padded_audio.export(output_file, format="mp3")
        return True
    except Exception as e:
        print(f"Error processing {input_file}: {str(e)}")
        return False

def process_folder(input_folder, output_folder, padding_ms=1000):
    """Process all audio files in a folder, adding silence padding to each."""
    # Create output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Track processing statistics
    total_files = 0
    successful_files = 0

    # Supported audio formats
    supported_formats = ('.mp3', '.wav', '.ogg', '.flac')

    # Iterate through all files in the input folder
    for filename in os.listdir(input_folder):
        if filename.endswith(supported_formats):
            total_files += 1
            input_path = os.path.join(input_folder, filename)
            output_path = os.path.join(output_folder, filename)
            print(f"Processing: {filename}")

            if add_silence_padding(input_path, output_path, padding_ms):
                successful_files += 1
                print(f"✓ Created: {filename}")
            else:
                print(f"✗ Failed to process: {filename}")

    # Print summary
    print(f"\nProcessing complete!")
    print(f"Successfully processed {successful_files} out of {total_files} files")
    if successful_files < total_files:
        print(f"Failed to process {total_files - successful_files} files")

def main():
    parser = argparse.ArgumentParser(
        description="Add silence padding to audio files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Process a single file:
    python script.py -i input.mp3 -o output.mp3
  Process all files in a folder:
    python script.py -f input_folder -d output_folder
  Specify custom padding duration:
    python script.py -f input_folder -d output_folder -p 3000
        """
    )

    # Add arguments
    parser.add_argument('-i', '--input', help='Input audio file')
    parser.add_argument('-o', '--output', help='Output audio file')
    parser.add_argument('-f', '--folder', help='Input folder containing audio files')
    parser.add_argument('-d', '--destination', help='Output folder for processed files')
    parser.add_argument('-p', '--padding', type=int, default=2000,
                        help='Padding duration in milliseconds (default: 2000)')

    args = parser.parse_args()

    # Validate arguments
    if args.input and args.folder:
        parser.error("Please specify either a single file (-i) or a folder (-f), not both")

    if args.input:
        if not args.output:
            parser.error("When processing a single file, output file (-o) must be specified")
        if not os.path.exists(args.input):
            parser.error(f"Input file not found: {args.input}")
        print(f"Processing single file: {args.input}")
        if add_silence_padding(args.input, args.output, args.padding):
            print(f"✓ Successfully created: {args.output}")
        else:
            print(f"✗ Failed to process file")

    elif args.folder:
        if not args.destination:
            parser.error("When processing a folder, destination folder (-d) must be specified")
        if not os.path.exists(args.folder):
            parser.error(f"Input folder not found: {args.folder}")
        print(f"Processing folder: {args.folder}")
        print(f"Output folder: {args.destination}")
        print(f"Padding duration: {args.padding}ms")
        process_folder(args.folder, args.destination, args.padding)

    else:
        parser.error("Please specify either an input file (-i) or folder (-f)")

if __name__ == "__main__":
    main()
