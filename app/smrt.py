from flask import Flask, request, Response
import summary
import transcript
from messenger import MessengerInterface, Whatsapp
from decouple import config
import base64
import time
import json
import db

from pipeline import VoiceMessagePipeline, GroupMessageQuestionPipeline
from questionbot import QuestionBotBingGPT, QuestionBotChatGPTOpenAI
app = Flask(__name__)

transcriber = transcript.FasterWhisperTranscript()
#summarizer = summary.OpenAIChatGPTSummary(config('OPENAI_APIKEY'))

whatsapp = Whatsapp(config("WPPCONNECT_SERVER"), "smrt", config('WPPCONNECT_APIKEY'))
CONFIG_MIN_WORDS_FOR_SUMMARY=int(config("MIN_WORDS_FOR_SUMMARY"))
#TODO: prepare for docker
database = db.Database("data.sqlite")
print(CONFIG_MIN_WORDS_FOR_SUMMARY)

questionBot = QuestionBotChatGPTOpenAI(config("CHATGPT_COOKIE"))
summarizer = summary.QuestionBotSummary(questionBot)
voicePipeline = VoiceMessagePipeline(transcriber, summarizer, CONFIG_MIN_WORDS_FOR_SUMMARY)


groupMessagePipeline = GroupMessageQuestionPipeline(database, summarizer, questionBot)

@app.route('/incoming', methods=['POST'])
def return_response():
    message = request.json
    print(json.dumps(message, indent=4))
    
    if 'event' in message:
        if message['event'] == "onmessage":
            pipelines = [voicePipeline, groupMessagePipeline]
            for pipeline in pipelines:
                if pipeline.matches(whatsapp, message):
                    pipeline.process(whatsapp, message) 

    return Response(status=200)

whatsapp._startSession()
app.run(host="0.0.0.0", port=9000)