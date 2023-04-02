from flask import Flask, request, Response
import summary
import transcript
from whatsapp import Whatsapp
from decouple import config
import base64
import time
import json
import db

app = Flask(__name__)

transcriber = transcript.FasterWhisperTranscript()
#summarizer = summary.OpenAIChatGPTSummary(config('OPENAI_APIKEY'))
summarizer = summary.BingGPTSummary()
whatsapp = Whatsapp(config("WPPCONNECT_SERVER"), "smrt", config('WPPCONNECT_APIKEY'))
CONFIG_MIN_WORDS_FOR_SUMMARY=int(config("MIN_WORDS_FOR_SUMMARY"))
#TODO: prepare for docker
db = db.Database("data.sqlite")
print(CONFIG_MIN_WORDS_FOR_SUMMARY)


@app.route('/incoming', methods=['POST'])
def return_response():
    message = request.json
    print(json.dumps(message, indent=4))
    
    if 'event' in message:
        if message['event'] == "onmessage":
            if message['isGroupMsg'] == True and message['type']=='chat':
                print("Group message received")
                pushName = message['sender']['pushname']
                messageText = message['content']
                # TODO: filter out own messages probably
                if messageText.startswith("#summary"):
                    whatsapp.reactHourglassFull(message['id'])
                    # TODO: put to configuration
                    messageCount = 20
                    command = messageText.split(" ")
                    if len(command) > 1:
                        messageCount = int(command[1])

                    chatText = ""
                    for row in db.getGroupMessages(message['chatId'], messageCount):
                        chatText += "%s: %s\n" % (row['sender'], row['message'])
                    summary = summarizer.summarize(chatText, 'de')

                    summaryText = "Summary (last %d messages)\n%s" % (messageCount, summary['text'])
                    whatsapp.sendGroupMessage(message['chatId'], summaryText)
                    whatsapp.reactDone(message['id'])
                else:
                    db.addGroupMessage(message['chatId'], pushName, messageText)

            if message['isGroupMsg'] == False:
                if 'mimetype' in message:
                    if message['mimetype'] == "audio/ogg; codecs=opus":
                        data = message['body']
                        debug = {}
                        #whatsapp.sendMessage(message['from'], "Processing...")
                        whatsapp.reactHourglassFull(message['id'])
                        
                        decoded = base64.b64decode(data)
                        with open('out.ogg', 'wb') as output_file:
                            output_file.write(decoded)

                        start = time.time()
                        transcript = transcriber.transcribe(decoded)
                        end = time.time()
                        debug['transcript_time'] = end - start
                        
                        transcriptText = transcript['text']
                        words = transcript['words']
                        language = transcript['language']
                        whatsapp.sendMessage(message['from'], "Transcribed: \n%s" % (transcriptText))
                        
                        debug['transcript_language'] = language
                        debug['transcript_language_probability'] = transcript['language_probability']
                        debug['transcript_words'] = transcript['words']
                        debug['transcript_cost'] = transcript['cost']
                        if words > CONFIG_MIN_WORDS_FOR_SUMMARY:
                            whatsapp.reactHourglassHalf(message['id'])
                            #whatsapp.sendMessage(message['from'], "Writing summary...")

                            start = time.time()
                            summary = summarizer.summarize(transcriptText, language)
                            end = time.time()
                            debug['summary_time'] = end - start

                            summaryText = summary['text']
                            debug['summary_cost'] = summary['cost']
                            whatsapp.sendMessage(message['from'], "Summary: \n%s" % (summaryText))
                        whatsapp.reactDone(message['id'])
                        debugText = "Debug: \n"
                        for debugKey, debugValue in debug.items():
                            debugText += debugKey + ": " + str(debugValue) + "\n"
                        debugText = debugText.strip()
                        whatsapp.sendMessage(message['from'], debugText)
            else:
                whatsapp.sendMessage(message['from'], "Please send a voice message")
    return Response(status=200)

whatsapp.startSession()
app.run(host="0.0.0.0", port=9000)