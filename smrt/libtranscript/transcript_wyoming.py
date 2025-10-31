import io
import socket
import wave
from wyoming.audio import AudioChunk
from wyoming.event import Event
from wyoming.asr import Transcribe, Transcript
from .transcript import TranscriptInterface, TranscriptResult

class WyomingTranscript(TranscriptInterface):
    """Implementation based on a Wyoming STT server instead of faster_whisper."""

    def __init__(self, host="127.0.0.1", port=10300):
        self._host = host
        self._port = port

    def _send_event(self, sock, event: Event):
        sock.sendall(event.to_bytes())

    def _recv_event(self, sock):
        header = sock.recv(8)
        if not header:
            return None

        length = int.from_bytes(header[:4], "big")
        event_type = header[4:].decode("ascii").strip()
        payload = b""
        while len(payload) < length:
            chunk = sock.recv(length - len(payload))
            if not chunk:
                break
            payload += chunk

        return Event(event_type, payload)

    def transcribe(self, audio_data: bytes):
        """Send audio_data (bytes) to Wyoming STT and return transcript metadata."""

        # Write audio_data into a temporary in-memory WAV file for chunked reading
        audio_reader = io.BytesIO(audio_data)
        with wave.open(audio_reader, "rb") as wf:
            rate = wf.getframerate()
            width = wf.getsampwidth()
            channels = wf.getnchannels()

            # Connect to Wyoming server
            sock = socket.create_connection((self._host, self._port))

            # Send transcribe request
            self._send_event(sock, Transcribe().event())

            # Send audio chunks
            chunk_size = 1024
            audio_reader.seek(0)
            while True:
                chunk = wf.readframes(chunk_size)
                if not chunk:
                    break
                self._send_event(sock, AudioChunk(audio=chunk, rate=rate, width=width, channels=channels).event())

            # End-of-audio marker
            self._send_event(sock, AudioChunk(audio=b"").event())

            # Wait for transcript
            text = ""
            language = "unknown"
            language_probability = 1.0
            duration = 0.0

            while True:
                event = self._recv_event(sock)
                if event is None:
                    break
                if event.type == Transcript.type:
                    transcript = Transcript.from_event(event)
                    text = transcript.text.strip()
                    language = getattr(transcript, "language", "unknown")
                    language_probability = getattr(transcript, "language_probability", 1.0)
                    break

            sock.close()

        words = len(text.split())
        return TranscriptResult(text, language, duration)