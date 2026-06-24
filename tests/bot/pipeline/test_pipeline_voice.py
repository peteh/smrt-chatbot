import time
import threading
import unittest

from smrt.bot.pipeline.pipeline_voice import VoiceMessagePipeline, NUM_PARALLEL_TRANSCRIPTS
from smrt.libtranscript import TranscriptInterface, TranscriptResult

class DummyTranscriptResult(TranscriptResult):
    def __init__(self, text="ok", language="en"):
        self.text = text
        self.language = language
        self.num_words = len(text.split())


class ConcurrencyTranscriber(TranscriptInterface):
    def __init__(self, start_event: threading.Event, counter: list[int], lock: threading.Lock):
        self._start_event = start_event
        self._counter = counter
        self._lock = lock
        self.max_concurrent = 0

    def transcribe(self, audio_data):
        self._start_event.wait()
        with self._lock:
            self._counter[0] += 1
            self.max_concurrent = max(self.max_concurrent, self._counter[0])

        time.sleep(0.2)

        with self._lock:
            self._counter[0] -= 1

        return DummyTranscriptResult()


class VoicePipelineConcurrencyTests(unittest.TestCase):
    def test_transcribe_runs_at_most_num_parallel_transcripts(self):
        start_event = threading.Event()
        counter = [0]
        lock = threading.Lock()
        transcriber = ConcurrencyTranscriber(start_event, counter, lock)
        pipeline = VoiceMessagePipeline(transcriber, None, min_words_for_summary=0)

        threads = []
        for _ in range(NUM_PARALLEL_TRANSCRIPTS + 3):
            thread = threading.Thread(target=pipeline._transcribe_wav, args=(b"audio",))
            thread.start()
            threads.append(thread)

        time.sleep(0.05)
        start_event.set()

        for thread in threads:
            thread.join()

        self.assertLessEqual(transcriber.max_concurrent, NUM_PARALLEL_TRANSCRIPTS)


if __name__ == '__main__':
    unittest.main()
