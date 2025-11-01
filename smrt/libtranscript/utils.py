import logging
import subprocess
import os
from pathlib import Path

class TranscriptUtils():

    @staticmethod
    def to_pcm(in_file_path: Path|str, out_file_path: Path|str) -> bool: 
        """Recode any audio file to 16 kHz, mono, 16-bit PCM using ffmpeg.
        Output format: WAV (PCM s16le)

        Args:
            in_file_path (Path | str): Path of the file to convert
            out_file_path (Path | str): Path of the output file

        Raises:
            FileNotFoundError: If input file was not found

        Returns:
            bool: If the process ran through
        """
        # make sure we really have path
        in_file_path = Path(in_file_path)
        out_file_path = Path(out_file_path)

        if not in_file_path.is_file():
            raise FileNotFoundError(f"Input file not found: {in_file_path}")

        # Ensure output directory exists
        os.makedirs(os.path.dirname(out_file_path) or ".", exist_ok=True)

        # FFmpeg command
        cmd = [
            "ffmpeg",
            "-y",              # overwrite output file if it exists
            "-i", in_file_path,  # input file
            "-ar", "16000",    # set sample rate
            "-ac", "1",        # set channels (mono)
            "-acodec", "pcm_s16le",  # 16-bit PCM codec
            out_file_path        # output file
        ]

        # Execute the command
        subprocess.run(cmd, check=True)
        logging.debug(f"Re-encoded to: {out_file_path}")
        return True