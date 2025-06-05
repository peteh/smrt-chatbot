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
import pipeline_ha
import questionbot
import transcript
import texttoimage
#import pipeline_tts
import db
import summary
import yaml

def run():
    config_file = open("app/config.yml", "r", encoding="utf-8")
    configuration = yaml.safe_load(config_file)
    config_file.close()

    print(configuration)
    
    mainpipe = MainPipeline()
    database = db.Database("data")
    questionbot_bot = questionbot.QuestionBotOllama("gemma3:12b")
    questionbot_image = questionbot.QuestionBotOllama("llava")
    questionbot_openai = questionbot.QuestionBotOpenAIAPI(config("OPENAI_APIKEY"))
    bots = [
            questionbot_bot,
            questionbot_openai
            ]
    question_bot = questionbot.FallbackQuestionbot(bots)

    summarizer = summary.QuestionBotSummary(questionbot_bot)

    transcriber = transcript.FasterWhisperTranscript()
    

    gpt_pipeline = pipeline.GptPipeline(questionbot_openai)

    group_message_pipeline = pipeline.GroupMessageQuestionPipeline(database, summarizer, question_bot)
    article_summary_pipeline = pipeline.ArticleSummaryPipeline(summarizer)

    processors = [texttoimage.StableHordeTextToImage(config("STABLEHORDE_APIKEY"))]
    imagegen_api = texttoimage.FallbackTextToImageProcessor(processors)
    imagegen_pipeline = pipeline.ImageGenerationPipeline(imagegen_api)

    image_prompt_pipeline = pipeline.ImagePromptPipeline(questionbot_image)
    mark_seen_pipeline = pipeline.MarkSeenPipeline()

    #tts_pipeline = pipeline_tts.TextToSpeechPipeline()
    grammar_pipeline = pipeline.GrammarPipeline(question_bot)
    tinder_pipeline = pipeline.TinderPipelinePipelineInterface(question_bot)


    # General pipelines
    mainpipe.add_pipeline(mark_seen_pipeline)
    
    CONFIG_HOMEASSISTANT = "homeassistant"
    if CONFIG_HOMEASSISTANT in configuration:
        config_ha = configuration[CONFIG_HOMEASSISTANT]
        ha_token = config_ha["token"]
        ha_ws_api_url = config_ha["ws_api_url"]
        ha_chat_id_whitelist = config_ha.get("chat_id_whitelist", [])
        ha_text_pipeline = pipeline_ha.HomeassistantTextCommandPipeline(ha_token, ha_ws_api_url, chat_id_whitelist=ha_chat_id_whitelist)
        ha_voice_pipeline = pipeline_ha.HomeassistantVoiceCommandPipeline(ha_token, ha_ws_api_url, chat_id_whitelist=ha_chat_id_whitelist)
        mainpipe.add_pipeline(ha_text_pipeline)
        mainpipe.add_pipeline(ha_voice_pipeline)
    
    CONFIG_VOICE_TRANSCRIPTION = "voice_transcription"
    if CONFIG_VOICE_TRANSCRIPTION in configuration:
        config_vt = configuration[CONFIG_VOICE_TRANSCRIPTION]
        vt_min_words_for_summary = config_vt.get("min_words_for_summary", 10)
        vt_chat_id_blacklist = config_vt.get("chat_id_blacklist", [])
        voice_pipeline = pipeline.VoiceMessagePipeline(transcriber,
                                                    summarizer,
                                                    vt_min_words_for_summary,
                                                    chat_id_blacklist=vt_chat_id_blacklist)
        mainpipe.add_pipeline(voice_pipeline)

    
    mainpipe.add_pipeline(group_message_pipeline)
    mainpipe.add_pipeline(article_summary_pipeline)
    mainpipe.add_pipeline(imagegen_pipeline)
    #mainpipe.add_pipeline(tts_pipeline)

    mainpipe.add_pipeline(grammar_pipeline)
    mainpipe.add_pipeline(tinder_pipeline)
    mainpipe.add_pipeline(gpt_pipeline)
    mainpipe.add_pipeline(image_prompt_pipeline)
    
    CONFIG_SIGNAL = "signal"
    if CONFIG_SIGNAL in configuration:
        config_signal = configuration[CONFIG_SIGNAL]
        signal_messenger = messenger.SignalMessenger(config_signal["number"], config_signal["host"], int(config_signal["port"]))
        signal_queue = SignalMessageQueue(signal_messenger, mainpipe)
        signal_queue.run_async()
    
    CONFIG_WHATSAPP = "whatsapp"
    if CONFIG_WHATSAPP in configuration:
        config_whatsapp = configuration[CONFIG_WHATSAPP]
        whatsapp = messenger.Whatsapp(config_whatsapp["wppconnect_server"], "smrt", config_whatsapp["wppconnect_api_key"])

        whatsapp_queue = WhatsappMessageQueue(whatsapp, mainpipe)
        whatsapp_queue.run_async()
    
        try:
            whatsapp.start_session()
        except:
            logging.warning("Could not start Whatsapp session")
        stock_notifier = SenateStockNotification(whatsapp)
        mainpipe.add_pipeline(stock_notifier)
        stock_notifier.run_async()

    while(True):
        time.sleep(1)

    # TODO: proper thread handling 