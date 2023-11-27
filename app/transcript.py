"""Transcript implementations to turn audio into text"""
import io
from abc import ABC, abstractmethod

import requests
from openai import OpenAI
import faster_whisper


# faster whisper
import torch
import torchaudio
import denoiser.pretrained
import denoiser.dsp

class TranscriptInterface(ABC):
    """Provides an interface for transcribing audio messages"""
    @abstractmethod
    def uses_denoise(self) -> bool:
        """Returns true if the transcriber denoises the input media"""

    @abstractmethod
    def transcribe(self, audio_data) -> dict:
        """Creates a transcript for the given audio data"""

class OpenAIWhisperTranscript(TranscriptInterface):
    """Implementation based on OpenAI's web services. """
    def __init__(self, api_key):
        self._api_key = api_key

    def uses_denoise(self):
        return False

    def transcribe(self, audio_data) -> dict:
        client = OpenAI(api_key=self._api_key)
        file_like = io.BytesIO(audio_data)
        file_like.name = "file.mp3"
        transcript = client.audio.transcribe("whisper-1", file_like)
        # TODO: map data
        return transcript

class WhisperTranscript(TranscriptInterface):
    """Implementation based on whisper asr webservice. """
    def uses_denoise(self):
        return False

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
    def __init__(self, model = "medium", beam_size = 5, threads = 4, denoise = False):
        self._beam_size = beam_size
        self._threads = threads
        self._model = model
        self._denoise = denoise

    def uses_denoise(self):
        return self._denoise

    def _denoise_audio(self, audio_data: bytes):
        model = denoiser.pretrained.dns64().cpu()
        file_like = io.BytesIO(audio_data)
        #file_like.name = "file.ogg"
        wav, sample_rate = torchaudio.load(file_like)
        wav = denoiser.dsp.convert_audio(wav.cpu(), sample_rate, model.sample_rate, model.chin)
        with torch.no_grad():
            denoised = model(wav[None])[0]
        buffer = io.BytesIO()
        torchaudio.save(buffer, denoised, model.sample_rate, format="vorbis", compression=-1)
        buffer.seek(0)
        return buffer.read()

    def transcribe(self, audio_data):
        model = faster_whisper.WhisperModel(self._model,
                                            device="cpu",
                                            compute_type="int8",
                                            cpu_threads = self._threads)
        if self._denoise:
            audio_data = self._denoise_audio(audio_data)

        audio_reader = io.BytesIO(audio_data)
        # or run on GPU with INT8
        # model = WhisperModel(model_size, device="cuda", compute_type="int8_float16")
        # or run on CPU with INT8
        # model = WhisperModel(model_size, device="cpu", compute_type="int8")

        segments, info = model.transcribe(audio_reader, beam_size=self._beam_size)
        supported_languages = ['en', 'de', 'es', 'fr']
        if info.language not in supported_languages:
            print(f"Warning: language detected as '{info.language}', therefore we redo as 'en'")
            audio_reader = io.BytesIO(audio_data)
            segments, info = model.transcribe(audio_reader, language='en', beam_size=5)

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
