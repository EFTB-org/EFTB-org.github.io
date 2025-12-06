#!/bin/bash

# Input a directory and convert all audio files to mp3 format and remove old files

# Check if a directory is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <directory>"
    exit 1
fi

TARGET_DIR="$1"

# Check if the provided argument is a directory
if [ ! -d "$TARGET_DIR" ]; then
    echo "Error: '$TARGET_DIR' is not a directory."
    exit 1
fi

# Check if ffmpeg is installed
if ! command -v ffmpeg &> /dev/null; then
    echo "Error: ffmpeg is not installed. Please install it first."
    exit 1
fi

echo "Scanning '$TARGET_DIR' for audio files to convert..."

# Find and process audio files (recursive)
# Supports: wav, m4a, flac, ogg, aiff, wma
find "$TARGET_DIR" -type f \( -iname "*.wav" -o -iname "*.m4a" -o -iname "*.flac" -o -iname "*.ogg" -o -iname "*.aiff" -o -iname "*.wma" \) -print0 | while IFS= read -r -d '' file; do
    echo "Processing: $file"
    
    # Construct output filename
    base_name="${file%.*}"
    output_file="${base_name}.mp3"
    
    # Convert using ffmpeg
    # -i: Input
    # -vn: No video
    # -ac 2: Stereo
    # -b:a 192k: 192kbps bitrate
    # -nostdin: Prevent reading from stdin (needed inside loop)
    # -y: Overwrite output if exists
    if ffmpeg -i "$file" -vn -ac 2 -b:a 192k -nostdin -y "$output_file" 2>/dev/null; then
        echo "  Converted -> $(basename "$output_file")"
        rm "$file"
        echo "  Removed original"
    else
        echo "  Error converting file!"
    fi
done

echo "Conversion complete."
