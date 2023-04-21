"""Main application"""
import json

from flask import Flask, request, Response
import summary
import transcript
import messenger
from decouple import config
import db
import pipeline
import texttoimage
import questionbot

app = Flask(__name__)

transcriber = transcript.FasterWhisperTranscript()

whatsapp = messenger.Whatsapp(config("WPPCONNECT_SERVER"), "smrt", config('WPPCONNECT_APIKEY'))
CONFIG_MIN_WORDS_FOR_SUMMARY=int(config("MIN_WORDS_FOR_SUMMARY"))
# TODO: prepare for docker
database = db.Database("data.sqlite")
bots = [
        questionbot.QuestionBotRevChatGPT(config("CHATGPT_COOKIE")),
        questionbot.QuestionBotBingGPT(),
        questionbot.QuestionBotOpenAIAPI(config("OPENAI_APIKEY"))
        ]

question_bot = questionbot.FallbackQuestionbot(bots)

summarizer = summary.QuestionBotSummary(question_bot)
voicePipeline = pipeline.VoiceMessagePipeline(transcriber, summarizer, CONFIG_MIN_WORDS_FOR_SUMMARY)
groupMessagePipeline = pipeline.GroupMessageQuestionPipeline(database, summarizer, question_bot)
articleSummaryPipeline = pipeline.ArticleSummaryPipeline(summarizer)

processors = [texttoimage.BingImageProcessor(),
              texttoimage.StableDiffusionAIOrg(),
              texttoimage.StableHordeTextToImage(config("STABLEHORDE_APIKEY"))]
image_api = texttoimage.FallbackTextToImageProcessor(processors)

imagePipeline = pipeline.ImagePromptPipeline(image_api)
ttsPipeline = pipeline.TextToSpeechPipeline()
grammarPipeline = pipeline.GrammarPipeline(question_bot)

@app.route('/incoming', methods=['POST'])
def return_response():
    """Handles new incoming messages from wpp-server"""
    message = request.json
    print(json.dumps(message, indent=4))

    if 'event' in message:
        if message['event'] == "onmessage":
            pipelines = [voicePipeline,
                         groupMessagePipeline,
                         articleSummaryPipeline,
                         imagePipeline,
                         ttsPipeline,
                         grammarPipeline]

            for pipe in pipelines:
                if pipe.matches(whatsapp, message):
                    pipe.process(whatsapp, message) 
            # delete message from phone after processing
            #whatsapp.deleteMessage(message)

    return Response(status=200)

whatsapp.start_session()
app.run(host="0.0.0.0", port=9000)
