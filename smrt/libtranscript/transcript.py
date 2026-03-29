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

class OpenAIApiTranscript(TranscriptInterface):
    """Implementation based on OpenAI's web services. """
    def __init__(self, 
                 api_url: str = "https://api.openai.com/v1/audio/transcribe", 
                 api_key: str|None = None):
        self._api_key = api_key
        self._api_url = api_url


    def transcribe(self, audio_data) -> TranscriptResult:
        headers = {
            "Content-Type": "audio/wav",
        }
        if self._api_key is not None:
            headers["Authorization"] = f"Bearer {self._api_key}"


        files = {
            "audio": ("file.wav", io.BytesIO(audio_data), "audio/wav")
        }

        response = requests.post(self._api_url, headers=headers, files=files)

        if response.status_code == 200:
            transcript = response.json()
            text = transcript.get("text")
            language = transcript.get("language")
            return TranscriptResult(text=text, language=language)
        else:
            print(f"Error: {response.status_code}, {response.text}")
            return TranscriptResult(text=None, language=None)
