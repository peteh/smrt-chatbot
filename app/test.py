import time
import json
from summary import OpenAIChatGPTSummary, ChatGPTSummary, BingGPTSummary, BardSummary
from transcript import WhisperTranscript, OpenAIWhisperTranscript, FasterWhisperTranscript
from messenger import Whatsapp
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

    #text = "Mein Tag war echt langweilig, ich habe gar nichts sinnvolles gemacht. Hey wir treffen uns heute 14:00 am Hauptbahnhof. "
    text = '''
Pete: Könntest quasi auch damit heizen
Pete: Man könnte dass dann auch irgendwo hin bauen wo Leute Abwärme brauchen
Pete: Keine Ahnung, hat der Praktikant oder chatgpt übersetzt :D
Pete: Bard von Google ist übrigens richtig schlecht
Pete: Sagt noch öfter als das free chatgpt dass er was nicht kann
Pete: Dann muss dir die Anlage aber gleich gehören
Pete: Mhm so richtig stimmt die Zuordnung noch nicht, aber ihm fehlen auch ein paar Nachrichten
Pete: Debug: 
summmary_input: Pete: Das löst das Problem aber nur in eine Richtung
Pete: Also man könnte damit Lastspitzen abfangen
Pete: Bzw müsste Wind Kraft Räder nicht abschalten
🤠: Aber nur wenn du den Strom in der Nähe der Windräder verbrauchst. Die Leitungen sind ja oft der Flaschenhals
Pete: Man könnte dass dann auch irgendwo hin bauen wo Leute Abwärme brauchen
Pete: Könntest quasi auch damit heizen
🤠: Ja, oder halt power to Gas und efuels, dann ist auch der schlechte Wirkungsgrad egal
Pete: Keine Ahnung, hat der Praktikant oder chatgpt übersetzt :D
Pete: Bard von Google ist übrigens richtig schlecht
Pete: Sagt noch öfter als das free chatgpt dass er was nicht kann
Marco Paul: Ja genau. Du baust Bitcoin Miner direkt an die Solar-/Windanlagen und drosselst die Leistung zu den Spitzenzeiten und speist ein und im Normalbetrieb machst du die meiste Kohle mit dem Mining
Marco Paul: Behind the meter Bitcoin Mining nennt sich das
Pete: Dann muss dir die Anlage aber gleich gehören
Marco Paul: Macht wahrscheinlich am meisten Sinn ja

summmary_maxMessages: 100
summmary_actualMessages: 14
summary_time: 22.9865779876709
summary_cost: 0
Pete: mal wieder am pumpen der gute?
Pete: Ich weiß jetzt warum Elon das Logo geändert hat
Pete: Damit in den News nix von dem Verfahren auftaucht
Pete: Sondern nur dass er Scheiss auf Twitter macht :D
Pete: Bzw wenn man nach Elon und Doge sucht nichts zum Verfahren kommt
Pete: Wollte er von den torries lernen :D
Pete: Klappt aber nur fast
Pete: Die ing hat jetzt wohl wieder 3 Prozent auf Tagesgeld
Pete: Dann performt mein Notgroschen besser als Aktien xD
Pete: Scheinbar
Pete: https://www.stern.de/wirtschaft/geld/tagesgeld--ing-lockt-jetzt-mit-3-prozent-zinsen-fuer-alle-33350076.html
Pete: Die Penner
Pete: Nur für Geld was man hin überweist
Pete: Das was da schon liegt zählt nicht
Andi: Abgeben und wieder überweisen? 😅
Pete: Der Terminator der Zusammenfassungen schreibt
Pete: XD
Pete: Der gleiche, das ist debug Info von meiner Entwicklung
Pete: Der schickt dir was er für die Zusammenfassung benutzt hat privat
Pete: Nur bei WhatsApp
Pete: Also im Moment speichert er die Gruppen ID + die Nachrichten + Username + Zeit
Pete: Und wenn du summary sagst fasst er das mit Bing gpt4 4 zusammen
Pete: Die Gruppen Nachrichten werde ich allerdings auf 100 beschränken, also er löscht dann alte Nachrichten
Pete: Das was du als debug Nachricht bekommst ist was er auswertet
Pete: Kannst ihm auch ne voice Nachricht schicken dann macht er Text und summary drauf
Pete: Draus
Pete: Geht aber noch nicht in Gruppen Nachrichten sondern nur in 1 to 1
Pete: Was hat das mit öffis zu tun?
Pete: die chinesen haben jetzt auch Grafikkarten
Pete: https://www.youtube.com/watch?v=DUnraazeGtk
Pete: Normal bin ich ja da :D
Pete: Aber dieses Jahr ist etwas anstrengend
Pete: Ist das nicht nur ne Berater Burnout Bude?
Andi: Bin normal auch da
Pete: Was ist der Virtual Scanner?
Pete: Da es scheinbar ne virtueller Scanner App ist, warum auch immer, sind das wahrscheinlich Test Files die der Entwickler aus Versehen mit eingecheckt hat
Pete: Du überschätzt random Entwickler ;)
🤠: Was mich aber besonders an dem Gesocks von den Grünen ärgert, ist das sie Steuerklasse 3 und 5 abschaffen wollen. Indirekte Steuererhöhung, kostet mich richtig Geld. 
Wer wählt diesen Dreck eigentlich?
Marco Paul: Gut aussehen tut sie ja schon ^^😂
Pete: #question um was geht es in den letzten 10 Nachrichten?
Pete: Lol
JP: Wie bitte?
Pete: Mhm vielleicht zu viele Nachrichten
🤠: Hat du es geändert? Bisher lief es doch immer super?
🤠: Es=was
Pete: Bisher konnte er noch keine random Fragen beantworten
Pete: Vielleicht mag er den Text nicht weil Bard darin schlecht weg kommt xD
Marco Paul: Oder er hat auch eine grüne Agenda 😂
Pete: Mag er auch nicht
Pete: Le sack
🤠: Safe😂'''
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
