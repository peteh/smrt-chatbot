from flask import Flask, request, Response
import summary
import transcript
from messenger import MessengerInterface, Whatsapp
from decouple import config
import base64
import time
import json
import db

import pipeline
import texttoimage

import questionbot
app = Flask(__name__)

transcriber = transcript.FasterWhisperTranscript()
#summarizer = summary.OpenAIChatGPTSummary(config('OPENAI_APIKEY'))

whatsapp = Whatsapp(config("WPPCONNECT_SERVER"), "smrt", config('WPPCONNECT_APIKEY'))
CONFIG_MIN_WORDS_FOR_SUMMARY=int(config("MIN_WORDS_FOR_SUMMARY"))
#TODO: prepare for docker
database = db.Database("data.sqlite")
bots = [
        questionbot.QuestionBotRevChatGPT(config("CHATGPT_COOKIE")),
        questionbot.QuestionBotBingGPT(),
        questionbot.QuestionBotOpenAIAPI(config("OPENAI_APIKEY"))
        ]

questionBot = questionbot.FallbackQuestionbot(bots)

summarizer = summary.QuestionBotSummary(questionBot)
voicePipeline = pipeline.VoiceMessagePipeline(transcriber, summarizer, CONFIG_MIN_WORDS_FOR_SUMMARY)
groupMessagePipeline = pipeline.GroupMessageQuestionPipeline(database, summarizer, questionBot)
articleSummaryPipeline = pipeline.ArticleSummaryPipeline(summarizer)

processors = [texttoimage.StableDiffusionAIOrg(), 
              texttoimage.StableHordeTextToImage(config("STABLEHORDE_APIKEY"))]
imageAPI = texttoimage.FallbackTextToImageProcessor(processors)

imagePipeline = pipeline.ImagePromptPipeline(imageAPI)
ttsPipeline = pipeline.TextToSpeechPipeline()

@app.route('/incoming', methods=['POST'])
def return_response():
    message = request.json
    print(json.dumps(message, indent=4))
    
    if 'event' in message:
        if message['event'] == "onmessage":
            pipelines = [voicePipeline, groupMessagePipeline, articleSummaryPipeline, imagePipeline, ttsPipeline]
            for pipeline in pipelines:
                if pipeline.matches(whatsapp, message):
                    pipeline.process(whatsapp, message) 
            # delete message from phone after processing
            #whatsapp.deleteMessage(message)

    return Response(status=200)

whatsapp._startSession()
app.run(host="0.0.0.0", port=9000)