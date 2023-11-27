import unittest
import transcript
from decouple import config

class TranscriptTest(unittest.TestCase):


    def test_faster_whisper_noisy(self):
        # arrange
        file_name = "samples/noisy.ogg"
        whisper = transcript.FasterWhisperTranscript(model = "medium", denoise=True)
        f = open(file_name, 'rb')
        data = f.read()
        f.close()
        print(whisper.transcribe(data))
    
    def test_faster_whisper(self):
        # arrange
        file_name = "samples/noisy.ogg"
        whisper = transcript.FasterWhisperTranscript(model = "medium", denoise=False)
        f = open(file_name, 'rb')
        data = f.read()
        f.close()
        transcription = whisper.transcribe(data)
        self.assertEqual(transcription["text"], "So flach wie meine Kuh!")
        

if __name__ == '__main__':
    unittest.main()

