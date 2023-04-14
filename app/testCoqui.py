
from TTS.api import TTS
import tempfile
import os
import subprocess

# Running a multi-speaker and multi-lingual model

#tts_models/de/thorsten/tacotron2-DCA
#tts_models/de/thorsten/vits
#tts_models/de/thorsten/tacotron2-DDC
# List available 🐸TTS models and choose the first one
model_name = TTS.list_models()[0]
# Init TTS

tts = TTS("tts_models/de/thorsten/tacotron2-DDC")

def wavToOgg(text: str):
    with tempfile.TemporaryDirectory() as tmp:
        
        inputFile = os.path.join(tmp, 'input.wav')
        tts.tts_to_file(text=text, file_path=inputFile)
        outputFile = os.path.join(tmp, 'output.ogg')
        
        subprocess.run(["oggenc", "-o", outputFile, inputFile]) 
        file = open(outputFile,mode='rb')
        oggData = file.read()
        file.close()
    return oggData

ogg = wavToOgg("Hello ich bin Torsten motherfuckers")
f = open("test.ogg", "wb")
f.write(ogg)
f.close()