from flask import Flask, request, Response
import base64
import requests
import summary
import transcript
from whatsapp import Whatsapp
from decouple import config

app = Flask(__name__)

transcriber = transcript.FasterWhisperTranscript()
#summarizer = summary.OpenAIChatGPTSummary(config('OPENAI_APIKEY'))
summarizer = summary.BingGPTSummary()
whatsapp = Whatsapp(config('WPPCONNECT_APIKEY'))
CONFIG_MIN_WORDS_FOR_SUMMARY=int(config("MIN_WORDS_FOR_SUMMARY"))

print(CONFIG_MIN_WORDS_FOR_SUMMARY)


@app.route('/incoming', methods=['POST'])
def return_response():
    message = request.json
    if 'event' in message:
        if message['event'] == "onmessage":
            if 'mimetype' in message:
                if message['mimetype'] == "audio/ogg; codecs=opus":
                    data = message['body']
                    whatsapp.sendMessage(message['from'], "Processing...")
                    decoded = base64.b64decode(data)
                    with open('out.ogg', 'wb') as output_file:
                        output_file.write(decoded)
                    transcript = transcriber.transcribe(decoded)
                    transcriptText = transcript['text']
                    words = transcript['words']
                    language = transcript['language']
                    whatsapp.sendMessage(message['from'], "Transcribed: \n%s" % (transcriptText))
                    debug = {}
                    debug['transcript_language'] = language
                    debug['transcript_language_probability'] = transcript['language_probability']
                    debug['transcript_words'] = transcript['words']
                    debug['transcript_cost'] = transcript['cost']
                    if words > CONFIG_MIN_WORDS_FOR_SUMMARY:
                        whatsapp.sendMessage(message['from'], "Writing summary...")
                        summary = summarizer.summarize(transcriptText, language)
                        summaryText = summary['text']
                        debug['summary_cost'] = summary['cost']
                        whatsapp.sendMessage(message['from'], "Summary: \n%s" % (summaryText))
                    debugText = "Debug: \n"
                    for debugKey, debugValue in debug.items():
                        debugText += debugKey + ": " + str(debugValue) + "\n"
                    debugText = debugText.strip()
                    whatsapp.sendMessage(message['from'], debugText)
    return Response(status=200)


app.run(host="0.0.0.0", port=9000)