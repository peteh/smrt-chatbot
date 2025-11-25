#!/usr/bin/env python3
import os
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError


# ------------------------------------------------------------
# Common options shared by info, subtitle, and audio extraction
# ------------------------------------------------------------
COMMON_OPTS = {
    "http_headers": {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        )
    },
    "extractor_args": {
        "youtube": {
            "player_client": ["android"]  # Avoid SABR web clients
        }
    },
    "retries": 10,
    "fragment_retries": 10,
    "source_address": "0.0.0.0",     # Change to "::" to force IPv6 if needed
}


# ------------------------------------------------------------
# Extract video info only (no downloads)
# ------------------------------------------------------------
def extract_info_only(url: str):
    opts = {
        **COMMON_OPTS,
        "skip_download": True,
        "dump_single_json": True,
        "quiet": True,
    }

    with YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)


# ------------------------------------------------------------
# Try downloading subtitles (separate lightweight request)
# Returns: (success: bool, filepath: str|None)
# ------------------------------------------------------------
def try_download_subtitles(url: str, title_prefix: str):
    opts = {
        **COMMON_OPTS,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitlesformat": "vtt",
        "skip_download": True,
        "outtmpl": f"{title_prefix}.%(ext)s",
        "quiet": False,
    }

    before = set(os.listdir("."))

    try:
        with YoutubeDL(opts) as ydl:
            ydl.download([url])
    except DownloadError:
        return False, None

    after = set(os.listdir("."))
    new_files = after - before
    subs = [f for f in new_files if f.endswith(".vtt") or f.endswith(".srt")]

    if not subs:
        return False, None

    return True, subs[0]


# ------------------------------------------------------------
# Download audio → convert to Whisper-ready WAV (mono/16k/s16)
# ------------------------------------------------------------
def download_whisper_audio(url: str, title_prefix: str):
    opts = {
        **COMMON_OPTS,
        "format": "bestaudio/best",
        "outtmpl": f"{title_prefix}.wav",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
            },
            {
                "key": "FFmpegAudioConvertor",
                "preferredcodec": "wav",
            },
            {
                "key": "FFmpegPostProcessor",
                "postprocessor_args": [
                    "-ac", "1",            # mono
                    "-ar", "16000",        # 16 kHz
                    "-sample_fmt", "s16"   # 16-bit PCM
                ],
            },
        ],
    }

    with YoutubeDL(opts) as ydl:
        ydl.download([url])

    # Find the produced WAV file
    candidates = [f for f in os.listdir(".") if f.endswith(".wav")]
    if not candidates:
        raise RuntimeError("Whisper WAV file not created")
    return max(candidates, key=os.path.getmtime)


# ------------------------------------------------------------
# Main pipeline
# ------------------------------------------------------------
def process(url: str):
    print("Extracting info...")
    info = extract_info_only(url)

    title = info.get("title") or "output"
    title_prefix = title.replace("/", "_")

    # Detect subtitles
    subs_available = bool(info.get("subtitles")) or bool(info.get("automatic_captions"))
    if subs_available:
        print("Subtitles detected. Attempting download...")
        ok, subfile = try_download_subtitles(url, title_prefix)
        if ok:
            print(f"Subtitles downloaded: {subfile}")
            return {"type": "subtitles", "file": subfile}
        else:
            print("Subtitle download failed due to rate limit or missing formats.")

    # No subs or download failed → fallback to Whisper audio
    print("Falling back to Whisper WAV extraction...")
    wavfile = download_whisper_audio(url, title_prefix)
    print(f"Whisper-ready audio written: {wavfile}")

    return {"type": "audio", "file": wavfile}


# Example usage:
result = process("https://www.youtube.com/shorts/MPV7M4t73yo")
print(result)