import requests
import openai
from io import BytesIO
import faster_whisper
import os
from abc import ABC, abstractmethod

class TranscriptInterface(ABC):

    @abstractmethod
    def transcribe(self, audioData) -> dict:
        """Creates a transcript for the given audio data"""
        pass

class OpenAIWhisperTranscript(TranscriptInterface):
    def __init__(self, apiKey):
        self._apiKey = apiKey

    def transcribe(self, audioData) -> dict:
        openai.api_key = self._apiKey
        fileLike = BytesIO(audioData)
        fileLike.name = "file.mp3"
        transcript = openai.Audio.transcribe("whisper-1", fileLike)
        # TODO: map data
        return transcript

class WhisperTranscript(TranscriptInterface):
    def transcribe(self, audioData):
        url = 'http://localhost:9001/asr?task=transcribe&language=en&output=json'
        files = {'audio_file': audioData}
        payload={}
        payload = {'task': 'transcribe', 
                'output': 'json'}

        response = requests.post(url, files=files, json=payload, headers={'accept': 'application/json'}, verify=False).json()
        text = response['text']
        duration = 0
        for segment in response['segments']:
            duration = segment['end']
        language = response['language']
        print(response)
        words = len(text.split(' '))
        # TODO: add duration
        return {
            'text': text, 
            'words': words,
            'language': language,
            'duration': duration,
            'cost': 0
        }

class FasterWhisperTranscript(TranscriptInterface):

    def __init__(self, model = "medium", beamSize = 5, threads = 4):
        self._beamSize = beamSize
        self._threads = threads
        self._model = model

    def _getModelFolderName(self, model):
        return "../models/faster_whisper_%s" % (model)
    
    def _isModelCached(self, model):
        foldername = self._getModelFolderName(model)
        return os.path.isdir(foldername)
    
    def _download(self, model):
        from faster_whisper.utils import download_model
        foldername = self._getModelFolderName(model)

        if not self._isModelCached(model):
            os.mkdir(foldername)
            download_model(model, foldername)

    def transcribe(self, audioData):
        #if not self._isModelCached(model_size):
        #    self._download(model_size)

        #modelPath = self._getModelFolderName(model_size)

        # Run on GPU with FP16
        # TODO: experiment with thread
        model = faster_whisper.WhisperModel(self._model, device="cpu", compute_type="int8", cpu_threads = self._threads)
        audioReader = BytesIO(audioData)
        # or run on GPU with INT8
        # model = WhisperModel(model_size, device="cuda", compute_type="int8_float16")
        # or run on CPU with INT8
        # model = WhisperModel(model_size, device="cpu", compute_type="int8")

        segments, info = model.transcribe(audioReader, beam_size=self._beamSize)
        supportedLanguages = ['en', 'de', 'es', 'fr']
        if info.language not in supportedLanguages:
            print("Warning: language detected as '%s', therefore we redo as 'en'" % (info.language))
            audioReader = BytesIO(audioData)
            segments, info = model.transcribe(audioReader, language='en', beam_size=5)

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