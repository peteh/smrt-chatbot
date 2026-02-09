import unittest
import tempfile
from pathlib import Path
from smrt.libtranscript import FasterWhisperTranscript, WyomingTranscript, TranscriptUtils, Qwen35Transcript

class TranscriptTests(unittest.TestCase):
    def _get_test_file_path(self, file_name) -> Path:

        current_dir = Path(__file__).resolve().parent
        return current_dir / file_name
    
    def test_qwen_transcript(self):
        # arrange
        transcript = Qwen35Transcript(model_name="Qwen/Qwen3-ASR-0.6B")
        test_file = self._get_test_file_path("sample_open_the_apartment_door.aac")
        
        
        with tempfile.TemporaryDirectory() as tmpdir:
            print("Temporary directory:", tmpdir)
            
            # You can create files inside it
            wav_path = Path(tmpdir) / "output.wav"
            TranscriptUtils.to_pcm(test_file, wav_path)
        
            with open(wav_path, "rb") as f:
                test_file_data = f.read()  # returns bytes
            # act
            result = transcript.transcribe(test_file_data)
        
        
        #assert
        self.assertEqual(result.text, "Open the apartment door.")
        self.assertEqual(result.language, "English")

    def test_whisper_transcript(self):
        # arrange
        transcript = FasterWhisperTranscript()
        test_file = self._get_test_file_path("sample_open_the_apartment_door.aac")
        
        
        with tempfile.TemporaryDirectory() as tmpdir:
            print("Temporary directory:", tmpdir)
            
            # You can create files inside it
            wav_path = Path(tmpdir) / "output.wav"
            TranscriptUtils.to_pcm(test_file, wav_path)
        
            with open(wav_path, "rb") as f:
                test_file_data = f.read()  # returns bytes
            # act
            result = transcript.transcribe(test_file_data)
        
        
        #assert
        self.assertEqual(result.text, "Open the apartment door.")
        self.assertEqual(result.language, "en")
    
    def test_wyoming_transcript(self):
        # arrange
        transcript = WyomingTranscript("ha.homebrain.dev")
        test_file = self._get_test_file_path("sample_open_the_apartment_door.aac")
        
        
        with tempfile.TemporaryDirectory() as tmpdir:
            print("Temporary directory:", tmpdir)
            
            # You can create files inside it
            wav_path = Path(tmpdir) / "output.wav"
            TranscriptUtils.to_pcm(test_file, wav_path)
        
            with open(wav_path, "rb") as f:
                test_file_data = f.read()  # returns bytes
            # act
            result = transcript.transcribe(test_file_data)
        
        
        #assert
        self.assertEqual(result.text, "Open the apartment door.")
        self.assertEqual(result.language, "en")