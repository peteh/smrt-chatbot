"""Transcript implementations to turn audio into text"""

import io
import logging
import re
from abc import ABC, abstractmethod

import requests


class TranscriptResult:
    def __init__(self, text: str|None, language: str|None):
        self._text = text
        self._language = language

    def _get_text(self) -> str|None:
        return self._text

    def _get_language(self) -> str|None:
        return self._language

    def _get_num_words(self) -> int:
        if self._text is None:
            return 0
        return len(self._text.split(" "))

    text = property(fget=_get_text, fset=None, fdel=None, doc="The transcribed text.")

    language = property(
        fget=_get_language,
        fset=None,
        fdel=None,
        doc="The detected language code, e.g. 'de' or 'en'.",
    )

    num_words = property(
        fget=_get_num_words, fset=None, fdel=None, doc="The duration in seconds"
    )


class TranscriptInterface(ABC):
    """Provides an interface for transcribing audio messages"""

    @abstractmethod
    def transcribe(self, audio_data) -> TranscriptResult:
        """Creates a transcript for the given audio data"""


class OpenAIApiTranscript(TranscriptInterface):

    DEFAULT_API_URL = "https://api.openai.com/v1/audio/transcribe"
    DEFAULT_TIMEOUT = 600  # seconds

    """Implementation based on OpenAI's web services. """

    def __init__(
        self,
        api_url: str = DEFAULT_API_URL,
        model: str | None = None,
        api_key: str | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        self._api_key = api_key
        self._api_url = api_url
        self._model = model
        self._timeout = timeout

    def transcribe(self, audio_data) -> TranscriptResult:
        headers = {
        }
        if self._api_key is not None:
            headers["Authorization"] = f"Bearer {self._api_key}"

        data = {}

        if self._model is not None:
            data["model"] = self._model

        files = {"file": ("file.wav", io.BytesIO(audio_data), "audio/wav")}

        response = requests.post(
            self._api_url,
            headers=headers,
            data=data,
            files=files,
            timeout=self._timeout,
        )

        if response.status_code == 200:
            transcript = response.json()
            text = transcript.get("text")
            
            # TODO: workaround for bug in llamacpp that prefixes the text with crap. 
            match = re.match(r"language (\w+)<asr_text>(.*)", text, re.DOTALL)
            if match:
                language, transcript = match.group(1), match.group(2).strip()
            else:
                language, transcript = None, text.strip()
            # if the language is in the response we will use it from there
            language = transcript.get("language", language)
            return TranscriptResult(text=text, language=language)
        else:
            logging.error(f"Error: {response.status_code}, {response.text}")
            return TranscriptResult(text=None, language=None)
