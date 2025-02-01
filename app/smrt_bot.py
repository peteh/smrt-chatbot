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

def run():
    whatsapp = messenger.Whatsapp(config("WPPCONNECT_SERVER"), "smrt", config('WPPCONNECT_APIKEY'))
    signal_messenger = messenger.SignalMessenger(config("SIGNAL_NUMBER"), config("SIGNAL_HOST"), int(config("SIGNAL_PORT")))

    mainpipe = MainPipeline()
    stock_notifier = SenateStockNotification(whatsapp)
    CONFIG_MIN_WORDS_FOR_SUMMARY=int(config("MIN_WORDS_FOR_SUMMARY"))
    database = db.Database("data")
    questionbot_mistral_nemo = questionbot.QuestionBotMistralNemo()
    questionbot_llama3_1 = questionbot.QuestionBotLlama3_1()
    questionbot_image = questionbot.QuestionBotOllama("llava")
    questionbot_openai = questionbot.QuestionBotOpenAIAPI(config("OPENAI_APIKEY"))
    bots = [
            questionbot_llama3_1,
            questionbot_mistral_nemo,
            questionbot_openai
            ]
    question_bot = questionbot.FallbackQuestionbot(bots)

    summarizer = summary.QuestionBotSummary(questionbot_llama3_1)

    transcriber = transcript.FasterWhisperTranscript()
    voice_pipeline = pipeline.VoiceMessagePipeline(transcriber,
                                                summarizer,
                                                CONFIG_MIN_WORDS_FOR_SUMMARY)

    gpt_pipeline = pipeline.GptPipeline(questionbot_openai)

    group_message_pipeline = pipeline.GroupMessageQuestionPipeline(database, summarizer, question_bot)
    article_summary_pipeline = pipeline.ArticleSummaryPipeline(summarizer)

    processors = [texttoimage.BingImageProcessor(),
                    texttoimage.StableHordeTextToImage(config("STABLEHORDE_APIKEY"))]
    imagegen_api = texttoimage.FallbackTextToImageProcessor(processors)
    imagegen_pipeline = pipeline.ImageGenerationPipeline(imagegen_api)

    image_prompt_pipeline = pipeline.ImagePromptPipeline(questionbot_image)
    mark_seen_pipeline = pipeline.MarkSeenPipeline()

    tts_pipeline = pipeline_tts.TextToSpeechPipeline()
    grammar_pipeline = pipeline.GrammarPipeline(question_bot)
    tinder_pipeline = pipeline.TinderPipelinePipelineInterface(question_bot)

    mainpipe.add_pipeline(mark_seen_pipeline)
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

    signal_queue = SignalMessageQueue(signal_messenger, mainpipe)
    whatsapp_queue = WhatsappMessageQueue(whatsapp, mainpipe)
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