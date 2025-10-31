import unittest
from smrt.libtranscript import transcript
from decouple import config

class TranscriptTests(unittest.TestCase):
   
    def test_faster_whisper(self):
        # arrange
        from pathlib import Path

        # Get the directory where the current Python file is located
        current_dir = Path(__file__).parent

        # Build the path to a file named "example.txt" next to this script
        file_path = current_dir / "sample.aac"

        whisper = transcript.FasterWhisperTranscript()
        f = open(file_path, 'rb')
        data = f.read()
        f.close()
        transcription = whisper.transcribe(data)
        self.assertEqual(transcription["text"], "Open the apartment door")
        

if __name__ == '__main__':
    unittest.main()

