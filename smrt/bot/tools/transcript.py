"""Transcript implementations to turn audio into text"""
import io
from abc import ABC, abstractmethod

import requests
import faster_whisper


class TranscriptInterface(ABC):
    """Provides an interface for transcribing audio messages"""

    @abstractmethod
    def transcribe(self, audio_data) -> dict:
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


class FasterWhisperTranscript(TranscriptInterface):
    """Implementation based on faster_whisper python. """
    def __init__(self, model_name = "large-v3-turbo", beam_size = 5, threads = 8):
        self._beam_size = beam_size
        self._threads = threads
        self._model_name = model_name
        self._model = faster_whisper.WhisperModel(self._model_name,
                                            device="cpu",
                                            compute_type="int8",
                                            cpu_threads = self._threads)

    def transcribe(self, audio_data):
        audio_reader = io.BytesIO(audio_data)
        # or run on GPU with INT8
        # model = WhisperModel(model_size, device="cuda", compute_type="int8_float16")
        # or run on CPU with INT8
        # model = WhisperModel(model_size, device="cpu", compute_type="int8")

        segments, info = self._model.transcribe(audio_reader, beam_size=self._beam_size)
        supported_languages = ['en', 'de', 'es', 'fr']
        if info.language not in supported_languages:
            print(f"Warning: language detected as '{info.language}', therefore we redo as 'en'")
            audio_reader.seek(0)
            segments, info = self._model.transcribe(audio_reader, language='en', beam_size=5)
        audio_reader.close()
        duration = 0.
        text = ""
        for segment in segments:
            #print("[%.2fs -> %.2fs] %s" % (segment.start, segment.end, segment.text))
            duration = segment.end
            text += segment.text.strip() + "\n"
        text = text.strip()

        words = len(text.split(' '))
        language = info.language
        language_probability = info.language_probability

        return {
            'text': text, 
            'words': words,
            'language': language,
            'language_probability': language_probability,
            'duration': duration, 
            'cost': '0'
        }
