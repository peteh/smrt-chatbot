import logging
from pathlib import Path
import wave
import os
from piper import PiperVoice

from .texttospeech import TextToSpeechInterface


class PiperTTSModel(TextToSpeechInterface):
    def __init__(self, onnx_path: Path|str) -> None:
        self._onnx_path = Path(onnx_path)
        logging.debug(f"Creating piper model from {self._onnx_path}")
    
    def tts(self, text: str, output_wav_file : Path|str, language : str = None) -> bool:
        output_wav_file = Path(output_wav_file)
        voice = PiperVoice.load(self._onnx_path)
        with wave.open(os.fspath(output_wav_file), "wb") as wav_file:
            voice.synthesize_wav(text, wav_file)
        return True
