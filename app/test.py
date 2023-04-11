import time
import json
from summary import OpenAIChatGPTSummary, ChatGPTSummary, BingGPTSummary, BardSummary
from transcript import WhisperTranscript, OpenAIWhisperTranscript, FasterWhisperTranscript
from whatsapp import Whatsapp
from decouple import config



def testSendMessage():
    recipient = '4917691403039'
    text = "Test Message"

    wa = Whatsapp(config('WPPCONNECT_APIKEY'))
    wa._sendMessage(recipient, text)

def testOpenAISummary():
    summary = OpenAIChatGPTSummary(config('OPENAI_APIKEY'))
    text = "Mein Tag war echt langweilig, ich habe gar nichts sinnvolles gemacht. Hey wir treffen uns heute halb drei am Hauptbahnhof. "

    print(json.dumps(summary.summarize(text, "de")))

def testChatGPTSummary():
    summary = ChatGPTSummary()

    text = "Mein Tag war echt langweilig, ich habe gar nichts sinnvolles gemacht. Hey wir treffen uns heute 14:00 am Hauptbahnhof. "

    print(json.dumps(summary.summarize(text, "de")))

def testBingGPTSummary():
    summary = BingGPTSummary()

    text = "Mein Tag war echt langweilig, ich habe gar nichts sinnvolles gemacht. Hey wir treffen uns heute 14:00 am Hauptbahnhof. "

    print(json.dumps(summary.summarize(text, "de")))

def testBardSummaryEnglish():
    summary = BardSummary(config("BARD_COOKIE"))

    text = """A "catastrophic" tornado has moved through the Little Rock, Arkansas area leaving one dead and at least 24 injured, according to the officials, and several tornadoes have been reported in Tennessee, Iowa, and Illinois.

The National Weather Service issued a Tornado Emergency for portions of the metro area of Little Rock on Friday afternoon, stating that a "damaging tornado" moved through the area. 

In Tennessee, the National Weather Service issued a Tornado Emergency for areas around Covington, which is just north of Memphis. The National Weather Service has also issued several Tornado Warnings for portions of Northwestern Illinois and Eastern Iowa.

The Little Rock Fire Department said in a Facebook post there was "heavy damage" in the West Little Rock area and encouraged residents to avoid traveling through the area, adding that it is conducting rescue operations.

Over 300,000 people were inside the tornado-warned storm, according to data from the National Weather Service."""

    print(json.dumps(summary.summarize(text, "en")))

def testBardSummaryGerman():
    summary = BardSummary(config("BARD_COOKIE"))

    text = "Mein Tag war echt langweilig, ich habe gar nichts sinnvolles gemacht. Hey wir treffen uns heute 14:00 am Hauptbahnhof. "

    print(json.dumps(summary.summarize(text, "de")))

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
    whisper = FasterWhisperTranscript(model = "medium", beamSize = beamSize, threads=threads)
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


#testFasterWhisperPerformance()
#testBardSummaryGerman()
testBingGPTSummary()