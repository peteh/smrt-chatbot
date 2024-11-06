"""Main application"""
import time
import logging
import messenger
from decouple import config
from main_pipeline import MainPipeline
from whatsappsocketio import WhatsappMessageQueue
import pipeline
import questionbot
import transcript
import db
import summary

def run():
    whatsapp = messenger.Whatsapp(config("WPPCONNECT_SERVER"), "smrt", config('WPPCONNECT_APIKEY'))

    mainpipe = MainPipeline()
    CONFIG_MIN_WORDS_FOR_SUMMARY=int(config("MIN_WORDS_FOR_SUMMARY"))
    database = db.Database("data_private")
    questionbot_mistral_nemo = questionbot.QuestionBotMistralNemo()
    questionbot_llama3_2 = questionbot.QuestionBotLlama3_2()
    questionbot_openai = questionbot.QuestionBotOpenAIAPI(config("OPENAI_APIKEY"))

    summarizer = summary.QuestionBotSummary(questionbot_llama3_2)

    transcriber = transcript.FasterWhisperTranscript()
    voice_pipeline = pipeline.VoiceMessagePipeline(transcriber,
                                                summarizer,
                                                CONFIG_MIN_WORDS_FOR_SUMMARY)
    mainpipe.add_pipeline(voice_pipeline)
    whatsapp_queue = WhatsappMessageQueue(whatsapp, mainpipe)
    whatsapp_queue.run_async()

    try:
        whatsapp.start_session()
    except:
        logging.warning("Could not start Whatsapp session")


    while(True):
        time.sleep(1)

    # TODO: proper thread handling 