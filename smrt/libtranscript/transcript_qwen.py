import io
import logging
import torch
import tempfile
from pathlib import Path
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

        with tempfile.TemporaryDirectory() as tmpdir:
            wav_path = Path(tmpdir) / "output.wav"
        
            with open(wav_path, "wb") as f:
                f.write(audio_data)
            audio_file = wav_path.as_posix()  # Convert Path to string for the model

            # Transcribe local audio file
            results = self._model.transcribe(
                audio=audio_file,  # local file path
                language=None,             # auto language detection
                return_time_stamps=False,  # set True if you want timestamps
            )

            # The results list contains objects with attributes `.text`, `.language`, etc.
            logging.debug(f"Transcript: {results[0].text}")
            logging.debug(f"Detected language: {results[0].language}")

        text = ""
        for segment in results:
            text += segment.text.strip() + "\n"
        text = text.strip()
        language = results[0].language

        return TranscriptResult(text, language)
