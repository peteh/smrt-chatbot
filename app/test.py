import time
import json
from summary import OpenAIChatGPTSummary, ChatGPTSummary, BingGPTSummary
from transcript import WhisperTranscript, OpenAIWhisperTranscript, FasterWhisperTranscript
from whatsapp import Whatsapp
from decouple import config



def testSendMessage():
    recipient = '4917691403039'
    text = "Test Message"

    wa = Whatsapp(config('WPPCONNECT_APIKEY'))
    wa.sendMessage(recipient, text)

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


start = time.time()
testBingGPTSummary()
end = time.time()
print(end - start)
