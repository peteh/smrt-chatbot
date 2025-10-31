"""Transcript implementations to turn audio into text"""
import io
from abc import ABC, abstractmethod

import requests

class TranscriptResult():
    def __init__(self, text: str, language: str, duration: float):
        self._text = text
        self._language = language
        self._duration = duration

    def _get_text(self) -> str:
        return self._text

    def _get_language(self) -> str:
        return self._language

    def _get_duration(self) -> float:
        return self._duration
    
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

    duration = property(
        fget=_get_duration,
        fset=None,
        fdel=None,
        doc="The duration in seconds"
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



 

class WhisperTranscript(TranscriptInterface):
    """Implementation based on whisper asr webservice. """

    def transcribe(self, audio_data):
        url = 'http://localhost:9001/asr?task=transcribe&language=en&output=json'
        files = {'audio_file': audio_data}
        payload={}
        payload = {'task': 'transcribe',
                'output': 'json'}

        response = requests.post(url, files=files,
                                 json=payload,
                                 headers={'accept': 'application/json'},
                                 verify=False,
                                 timeout=1200).json()
        text = response['text']
        duration = 0
        for segment in response['segments']:
            duration = segment['end']
        language = response['language']
        print(response)
        words = len(text.split(' '))
        return {
            'text': text, 
            'words': words,
            'language': language,
            'duration': duration,
            'cost': 0
        }


