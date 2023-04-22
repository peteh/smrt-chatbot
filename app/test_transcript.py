import unittest
import transcript
from decouple import config

class TranscriptTest(unittest.TestCase):


    def test_faster_whisper_noisy(self):
        # arrange
        file_name = "samples/noisy.ogg"
        whisper = transcript.FasterWhisperTranscript(model = "medium")
        f = open(file_name, 'rb')
        data = f.read()
        f.close()
        print(whisper.transcribe(data))
            

if __name__ == '__main__':
    unittest.main()

