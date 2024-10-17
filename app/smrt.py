"""Main application"""
import time
import logging
import messenger
from decouple import config
from main_pipeline import MainPipeline
from signalcli import SignalMessageQueue
from whatsappsocketio import WhatsappMessageQueue
from senate_stocks import SenateStockNotification
import pipeline
import questionbot
import transcript
import texttoimage
import pipeline_tts
import db
import summary
logging.basicConfig(level=logging.DEBUG)
root = logging.getLogger()
root.setLevel(logging.DEBUG)

#handler = logging.StreamHandler(sys.stdout)
#handler.setLevel(logging.DEBUG)
#formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#handler.setFormatter(formatter)
#root.addHandler(handler)

whatsapp = messenger.Whatsapp(config("WPPCONNECT_SERVER"), "smrt", config('WPPCONNECT_APIKEY'))
signalMessenger = messenger.SignalMessenger(config("SIGNAL_NUMBER"), config("SIGNAL_HOST"), int(config("SIGNAL_PORT")))

mainpipe = MainPipeline()

signal_queue = SignalMessageQueue(signalMessenger, mainpipe)
whatsapp_queue = WhatsappMessageQueue(whatsapp, mainpipe)

stock_notifier = SenateStockNotification(whatsapp)
CONFIG_MIN_WORDS_FOR_SUMMARY=int(config("MIN_WORDS_FOR_SUMMARY"))
database = db.Database("data")
questionbot_mistral_nemo = questionbot.QuestionBotMistralNemo()
questionbot_llama3_2 = questionbot.QuestionBotLlama3_2()
questionbot_image = questionbot.QuestionBotOllama("llava")
questionbot_openai = questionbot.QuestionBotOpenAIAPI(config("OPENAI_APIKEY"))
questionbot_bing = questionbot.QuestionBotBingGPT()
questionbot_bard = questionbot.QuestionBotBard()
bots = [
        questionbot_llama3_2,
        questionbot_mistral_nemo,
        questionbot_openai
        ]
question_bot = questionbot.FallbackQuestionbot(bots)

summarizer = summary.QuestionBotSummary(questionbot_llama3_2)

transcriber = transcript.FasterWhisperTranscript()
voice_pipeline = pipeline.VoiceMessagePipeline(transcriber,
                                            summarizer,
                                            CONFIG_MIN_WORDS_FOR_SUMMARY)


gpt_pipeline = pipeline.GptPipeline(question_bot, questionbot_openai, questionbot_bing, questionbot_bard)

group_message_pipeline = pipeline.GroupMessageQuestionPipeline(database, summarizer, question_bot)
article_summary_pipeline = pipeline.ArticleSummaryPipeline(summarizer)

processors = [texttoimage.BingImageProcessor(),
                texttoimage.FlowGPTImageProcessor(texttoimage.FlowGPTImageProcessor.MODEL_DALLE3),
                #texttoimage.DiffusersTextToImage(), 
                texttoimage.StableHordeTextToImage(config("STABLEHORDE_APIKEY"))]
imagegen_api = texttoimage.FallbackTextToImageProcessor(processors)
imagegen_pipeline = pipeline.ImageGenerationPipeline(imagegen_api)

image_prompt_pipeline = pipeline.ImagePromptPipeline(questionbot_image)


tts_pipeline = pipeline_tts.TextToSpeechPipeline()
grammar_pipeline = pipeline.GrammarPipeline(question_bot)
tinder_pipeline = pipeline.TinderPipelinePipelineInterface(question_bot)


mainpipe.add_pipeline(stock_notifier)
mainpipe.add_pipeline(voice_pipeline)
mainpipe.add_pipeline(group_message_pipeline)
mainpipe.add_pipeline(article_summary_pipeline)
mainpipe.add_pipeline(imagegen_pipeline)
mainpipe.add_pipeline(tts_pipeline)
mainpipe.add_pipeline(grammar_pipeline)
mainpipe.add_pipeline(tinder_pipeline)
mainpipe.add_pipeline(gpt_pipeline)
mainpipe.add_pipeline(image_prompt_pipeline)

signal_queue.run_async()
whatsapp_queue.run_async()
stock_notifier.run_async()
try:
    whatsapp.start_session()
except:
    logging.warning("Could not start Whatsapp session")


while(True):
    time.sleep(1)

# TODO: proper thread handling 