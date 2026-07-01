import os
import asyncio
from pathlib import Path

async def convert_to_wav(input_filepath: str) -> str:
    """
    Asynchronously converts an audio file to a standard 16-bit, 44100Hz WAV 
    file suitable for aplay natively.
    """
    path = Path(input_filepath)
    
    # Skip conversion if already a wav
    if path.suffix.lower() == '.wav':
        return input_filepath 

    output_filepath = str(path.with_suffix('.wav'))

    # FFmpeg arguments to force format: 44.1kHz, stereo, 16-bit little-endian PCM
    command = [
        "ffmpeg",
        "-y",                   # Overwrite output files silently
        "-i", input_filepath,   # Input file
        "-ar", "44100",         # Sample rate
        "-ac", "2",             # Channels (Stereo)
        "-c:a", "pcm_s16le",    # Codec (16-bit little endian)
        output_filepath
    ]

    # Run FFmpeg asynchronously to avoid blocking the bot's event loop
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()

    if process.returncode == 0:
        # Optional: Remove the original file to save space on the Pi SD card
        # os.remove(input_filepath) 
        return output_filepath
    else:
        print(f"FFmpeg failed to convert {input_filepath}")
        if stderr:
            print(f"FFmpeg stderr: {stderr.decode().strip()[:500]}")
        return input_filepath # Fallback to original if it fails