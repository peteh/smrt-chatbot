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

whatsapp = messenger.Whatsapp(config("WPPCONNECT_SERVER"), "smrt", config('WPPCONNECT_APIKEY'))
CONFIG_MIN_WORDS_FOR_SUMMARY=int(config("MIN_WORDS_FOR_SUMMARY"))
# TODO: prepare for docker
database = db.Database("data")

bots = [
        questionbot.QuestionBotBingGPT(),
        questionbot.QuestionBotRevChatGPT(config("CHATGPT_COOKIE")),
        questionbot.QuestionBotOpenAIAPI(config("OPENAI_APIKEY"))
        ]
question_bot = questionbot.FallbackQuestionbot(bots)

summarizer = summary.QuestionBotSummary(question_bot)

transcriber = transcript.FasterWhisperTranscript(denoise=False)
voice_pipeline = pipeline.VoiceMessagePipeline(transcriber,
                                               summarizer,
                                               CONFIG_MIN_WORDS_FOR_SUMMARY)
gpt_pipeline = pipeline.GptPipeline(question_bot)

group_message_pipeline = pipeline.GroupMessageQuestionPipeline(database, summarizer, question_bot)
article_summary_pipeline = pipeline.ArticleSummaryPipeline(summarizer)

processors = [texttoimage.BingImageProcessor(),
              texttoimage.StableDiffusionAIOrg(),
              texttoimage.StableHordeTextToImage(config("STABLEHORDE_APIKEY"))]
image_api = texttoimage.FallbackTextToImageProcessor(processors)
image_pipeline = pipeline.ImagePromptPipeline(image_api)

tts_pipeline = pipeline.TextToSpeechPipeline()
grammar_pipeline = pipeline.GrammarPipeline(question_bot)
tinder_pipeline = pipeline.TinderPipelinePipelineInterface(question_bot)

pipelines = [voice_pipeline,
            group_message_pipeline,
            article_summary_pipeline,
            image_pipeline,
            tts_pipeline,
            grammar_pipeline,
            tinder_pipeline,
            gpt_pipeline]

help_pipeline = pipeline.Helpipeline(pipelines)
pipelines.append(help_pipeline)

@app.route('/incoming', methods=['POST'])
def return_response():
    """Handles new incoming messages from wpp-server"""
    message = request.json
    print(json.dumps(message, indent=4))

    if 'event' in message:
        if message['event'] == "onmessage":
            for pipe in pipelines:
                if pipe.matches(whatsapp, message):
                    print(f"{type(pipe).__name__} matches, processing")
                    pipe.process(whatsapp, message)
            # delete message from phone after processing
            #whatsapp.deleteMessage(message)

    return Response(status=200)

whatsapp.start_session()
app.run(host="0.0.0.0", port=9000)
