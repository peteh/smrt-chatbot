import io
import faster_whisper

from .transcript import TranscriptInterface, TranscriptResult

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

    def transcribe(self, audio_data) -> TranscriptResult:
        audio_reader = io.BytesIO(audio_data)
        # or run on GPU with INT8
        # model = WhisperModel(model_size, device="cuda", compute_type="int8_float16")
        # or run on CPU with INT8
        # model = WhisperModel(model_size, device="cpu", compute_type="int8")
        vad = True
        segments, info = self._model.transcribe(audio_reader, beam_size=self._beam_size, vad_filter=vad)
        supported_languages = ['en', 'de', 'es', 'fr']
        if info.language not in supported_languages:
            print(f"Warning: language detected as '{info.language}', therefore we redo as 'en'")
            audio_reader.seek(0)
            segments, info = self._model.transcribe(audio_reader, language='en', beam_size=5, vad_filter=vad)
        audio_reader.close()
        duration = 0.
        text = ""
        for segment in segments:
            #print("[%.2fs -> %.2fs] %s" % (segment.start, segment.end, segment.text))
            duration = segment.end
            text += segment.text.strip() + "\n"
        text = text.strip()
        language = info.language
        language_probability = info.language_probability

        return TranscriptResult(text, language, duration)


