import asyncio
from wyoming.client import AsyncClient
from wyoming.audio import AudioStart, AudioChunk, AudioStop
import langid
from .transcript import TranscriptInterface, TranscriptResult

class WyomingTranscript(TranscriptInterface):
    """Implementation based on a Wyoming STT server"""

    RATE = 16000
    CHANNELS = 1
    WIDTH = 2

    def __init__(self, uri="tcp://127.0.0.1:10300"):
        self._uri = uri

    def _get_event_loop(self):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError as e:
            if str(e).startswith('There is no current event loop in thread'):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            else:
                raise
        return loop

    async def _async_transcribe(self, audio_data: bytes) -> TranscriptResult:
        """Internal async method for ASR communication."""
        async with AsyncClient.from_uri(self._uri) as client:
            # start audio processing
            await client.write_event(AudioStart(rate=self.RATE, width=self.WIDTH, channels=self.CHANNELS).event())
            # send audio data
            chunk = AudioChunk(audio=audio_data, rate=self.RATE, width=self.WIDTH, channels=self.CHANNELS)
            await client.write_event(chunk.event())
            await client.write_event(AudioStop().event())
            # Wait for the transcription response
            while True:
                event = await client.read_event()
                if event.type == "transcript":
                    text = event.data.get("text", "")
                    lang, _ = langid.classify(text)
                    text = text.strip()
                    return TranscriptResult(text, lang)
                elif event.type == "error":
                    raise RuntimeError(f"ASR error: {event.data.get('message', 'unknown')}")

    def transcribe(self, audio_data: bytes):
        # Schedule the coroutine safely in the background loop
        result = self._get_event_loop().run_until_complete(self._async_transcribe(audio_data))
        return result
