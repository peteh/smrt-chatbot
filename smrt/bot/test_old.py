import time
import json
from transcript import WhisperTranscript, OpenAIWhisperTranscript, FasterWhisperTranscript
from messenger import Whatsapp
from decouple import config



def testSendMessage():
    recipient = '4917691403039'
    text = "Test Message"

    wa = Whatsapp(config('WPPCONNECT_APIKEY'))
    wa._send_message(recipient, text)

def testLocalWhisperTranscript():
    whisper = WhisperTranscript()
    f = open("out-cici.ogg", 'rb')
    data = f.read()
    f.close()
    print(whisper.transcribe(data))

def testLocalFasterWhisperTranscript():
    whisper = FasterWhisperTranscript()
    f = open("out-cici.ogg", 'rb')
    data = f.read()
    f.close()
    print(whisper.transcribe(data))

def testOpenAIWhisperTranscript():
    whisper = OpenAIWhisperTranscript(config('OPENAI_APIKEY'))
    f = open("out-cici.ogg", 'rb')
    data = f.read()
    f.close()
    print(whisper.transcribe(data))

def _testFasterWhisperPerformanceSingle(beamSize, threads, fileName):
    whisper = FasterWhisperTranscript(model = "medium", beam_size = beamSize, threads=threads)
    f = open(fileName, 'rb')
    data = f.read()
    f.close()
    return whisper.transcribe(data)
    
def testFasterWhisperPerformance():
    beamSize = 5
    for threads in range(2, 17, 2):
        start = time.time()
        data = _testFasterWhisperPerformanceSingle(beamSize, threads, "samples/newyear.ogg")
        end = time.time()
        duration = end - start
        print("Threads: %d, Duration: %f" % (threads, duration))
        print(data)


