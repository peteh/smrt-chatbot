import io
import logging
import torch
from qwen_asr import Qwen3ASRModel

from .transcript import TranscriptInterface, TranscriptResult

class Qwen35Transcript(TranscriptInterface):
    """Implementation based on qwen 3.5. """
    def __init__(self, model_name = "Qwen/Qwen3-ASR-1.7B"):
        """_summary_

        Args:
            model_name (str, optional): Qwen/Qwen3-ASR-1.7B or Qwen/Qwen3-ASR-0.6B
        """
        self._model_name = model_name
        # Load model on CPU
        self._model = Qwen3ASRModel.from_pretrained(
            self._model_name,
            device_map="cpu",               # CPU only
            dtype=torch.float32,        # use full precision on CPU
        )

    def transcribe(self, audio_data) -> TranscriptResult:
        audio_reader = io.BytesIO(audio_data)
        # Transcribe local audio file
        results = self._model.transcribe(
            audio=audio_reader,
            language=None,             # auto language detection
            return_time_stamps=False,  # set True if you want timestamps
        )

        # The results list contains objects with attributes `.text`, `.language`, etc.
        logging.debug(f"Transcript: {results[0].text}")
        logging.debug(f"Detected language: {results[0].language}")

        supported_languages = ['en', 'de', 'es', 'fr', 'zh']
        if results[0].language not in supported_languages:
            print(f"Warning: language detected as '{results[0].language}', therefore we redo as 'en'")
            audio_reader.seek(0)
            results = self._model.transcribe(
            audio=audio_reader,
            language="en",
            return_time_stamps=False,  # set True if you want timestamps
        )
        audio_reader.close()
        text = ""
        for segment in results:
            text += segment.text.strip() + "\n"
        text = text.strip()
        language = results[0].language

        return TranscriptResult(text, language)
