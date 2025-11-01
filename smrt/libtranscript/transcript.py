"""Transcript implementations to turn audio into text"""
import io
from abc import ABC, abstractmethod

import requests

class TranscriptResult():
    def __init__(self, text: str, language: str):
        self._text = text
        self._language = language

    def _get_text(self) -> str:
        return self._text

    def _get_language(self) -> str:
        return self._language

    def _get_num_words(self) -> int:
        return len(self._text.split(" "))

    text = property(
        fget=_get_text,
        fset=None,
        fdel=None,
        doc="The transcribed text."
    )

    language = property(
        fget=_get_language,
        fset=None,
        fdel=None,
        doc="The detected language code, e.g. 'de' or 'en'."
    )

    num_words = property(
        fget=_get_num_words,
        fset=None,
        fdel=None,
        doc="The duration in seconds"
    )

class TranscriptInterface(ABC):
    """Provides an interface for transcribing audio messages"""

    @abstractmethod
    def transcribe(self, audio_data) -> TranscriptResult:
        """Creates a transcript for the given audio data"""

class OpenAIWhisperTranscript(TranscriptInterface):
    """Implementation based on OpenAI's web services. """
    def __init__(self, api_key):
        self._api_key = api_key
        self._api_url = "https://api.openai.com/v1/audio/transcribe"


    def transcribe(self, audio_data) -> dict:
        headers = {
            "Content-Type": "audio/mp3",
            "Authorization": f"Bearer {self._api_key}"
        }

        files = {
            "audio": ("file.mp3", io.BytesIO(audio_data), "audio/mp3")
        }

        response = requests.post(self._api_url, headers=headers, files=files)

        if response.status_code == 200:
            transcript = response.json()
            # TODO: map data
            return transcript
        else:
            print(f"Error: {response.status_code}, {response.text}")
            return {}
