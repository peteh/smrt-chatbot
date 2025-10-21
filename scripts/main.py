"""Main application"""
import time
import logging
import threading
import schedule
from multiprocessing import Process


logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

import yaml

import smrt.db
import smrt.bot.pipeline as pipeline
import smrt.bot.messenger as messenger
import smrt.bot.messagequeue as messagequeue
from smrt.web.galleryweb import GalleryFlaskApp

#from senate_stocks import SenateStockNotification

import smrt.bot.tools

schema = {
    "storage_path": {"type": "string", "required": False},
    "signal": {
        "type": "dict",
        "schema": {
            "host": {"type": "string", "required": True},
            "port": {"type": "integer", "required": True},
            "number": {"type": "string", "required": True}
        },
        "required": False
    },
    "whatsapp": {
        "type": "dict",
        "schema": {
            "wppconnect_api_key": {"type": "string", "required": True},
            "wppconnect_server": {"type": "string", "required": True}
        },
        "required": False
    },
    "telegram": {
        "type": "dict",
        "schema": {
            "telegram_api_key": {"type": "string", "required": True},
        },
        "required": False
    },
    "ollama": {
        "type": "dict",
        "schema": {
            "host": {"type": "string", "required": True}
        },
        "required": False
    },
    "llama_cpp": {
        "type": "dict",
        "schema": {
            "host": {"type": "string", "required": True}  # URL of the llama.cpp server, e.g. http://localhost:8000
        },
        "required": False
    },
    "voice_transcription": {
        "type": "dict",
        "schema": {
            "min_words_for_summary": {"type": "integer", "required": True},
            "summary_bot": {"type": "string", "required": False},
            "chat_id_blacklist": {
                "type": "list",
                "schema": {"type": "string"},
                "required": False
            }
        },
        "required": False
    },
    "article_summary": {
        "type": "dict",
        "schema": {
            "summary_bot": {"type": "string", "required": True}
        },
        "required": False
    },
    "text_to_speech": {
        "type": "dict",
        "schema": {},
        "nullable": True,  # Accepts `null` or empty dict as valid
        "required": False
    },
    "tinder": {
        "type": "dict",
        "schema": {
            "tinder_bot": {"type": "string", "required": True},
            "chat_id_whitelist": {
                "type": "list",
                "schema": {"type": "string"},
                "required": False
            },
            "chat_id_blacklist": {
                "type": "list",
                "schema": {"type": "string"},
                "required": False
            }
        },
        "required": False
    },
    "image_generation": {
        "type": "dict",
        "schema": {
            "generator": {"type": "string", "required": True}
        },
        "required": False
    },
    "homeassistant": {
        "type": "dict",
        "schema": {
            "token": {"type": "string", "required": True},
            "ws_api_url": {"type": "string", "required": True},
            "chat_id_whitelist": {
                "type": "list",
                "schema": {"type": "string"},
                "required": False
            },
            "process_without_command": {
                "type": "boolean",
                "default": False,  # Default to False if not specified
                "required": False
            }
        },
        "required": False
    },
    "chatid": {
        "type": "dict",
        "schema": {},
        "nullable": True,  # Accepts `null` or empty dict as valid
        "required": False
    },
    "debug": {
        "type": "dict",
        "schema": {},
        "nullable": True,  # Accepts `null` or empty dict as valid
        "required": False
    },
    "gallery": {
        "type": "dict",
        "schema": {
            "base_url": {"type": "string", "required": True},
            "port": {"type": "integer", "required": True},
            "chat_id_whitelist": {
                "type": "list",
                "schema": {"type": "string"},
                "required": False
            },
            "chat_id_blacklist": {
                "type": "list",
                "schema": {"type": "string"},
                "required": False
            }
        },
        "required": False
    },
    "gaudeam": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "gaudeam_session": {"type": "string", "required": True},
                "gaudeam_subdomain": {"type": "string", "required": True},
                "chat_id_whitelist": {
                    "type": "list",
                    "schema": {"type": "string"},
                    "required": False
                },
                "chat_id_blacklist": {
                    "type": "list",
                    "schema": {"type": "string"},
                    "required": False
                }
            }
        },
        "required": False
    }
}

from cerberus import Validator
def validate_config(config, schema):
    validator = Validator(schema)
    if validator.validate(config):
        return True
    else:
        print("❌ Configuration is invalid:")
        for field, errors in validator.errors.items():
            print(f" - {field}: {errors}")
        return False

class BotLoader():
    def __init__(self):
        self._ollama_server = None
        self._llama_cpp_server = None

    def set_ollama_server(self, server: str):
        """Set the ollama server to use."""
        self._ollama_server = server
        logging.info(f"Using ollama server: {self._ollama_server}")
        
    def set_llama_cpp_server(self, server: str):
        """Set the llama.cpp server to use."""
        self._llama_cpp_server = server
        logging.info(f"Using llama.cpp server: {self._llama_cpp_server}")
        
    def create(self, bot_name: str) -> smrt.bot.tools.QuestionBotInterface:
        """Factory function to create a question bot instance based on the bot name."""
        if bot_name.startswith("ollama:"):
            if self._ollama_server is None:
                raise ValueError("Ollama server not set. Use \"ollama:\" configuration option to set it.")
            model_name = bot_name[bot_name.find(":")+1:]
            logging.debug(f"Creating QuestionBotOllama with model: {model_name}")
            return smrt.bot.tools.question_bot.QuestionBotOllama(self._ollama_server, model_name)
        elif bot_name.startswith("llama_cpp:"):
            if self._llama_cpp_server is None:
                raise ValueError("Llama.cpp server not set. Use set_llama_cpp_server() to set it.")
            #model_name = bot_name[bot_name.find(":")+1:]
            #logging.debug(f"Creating QuestionBotLlamaCppServer with model: {model_name}")
            return smrt.bot.tools.question_bot.QuestionBotLlamaCppServer(self._llama_cpp_server)
        elif bot_name.startswith("openai:"):
            api_key = bot_name[bot_name.find(":"):]
            return smrt.bot.tools.question_bot.QuestionBotOpenAIAPI(api_key)
        else:
            raise ValueError(f"Unknown bot name: {bot_name}")

# TODO: put this into a production server too if debug is false


def run():
    config_file = open("config.yml", "r", encoding="utf-8")
    configuration = yaml.safe_load(config_file)
    config_file.close()
    
    messenger_manager = messenger.MessengerManager()
    message_server = messagequeue.MessageServerFlaskApp(messenger_manager)
    

    if not validate_config(configuration, schema):
        exit(1)
        
    CONFIG_DEBUG = "debug"
    debug_flag = False
    if CONFIG_DEBUG in configuration:
        debug_flag = True
    storage_path = configuration.get("storage_path", "/storage/")
    logging.info(f"Using storage path: {storage_path}")
    
     # create main pipeline
    
    mainpipe = pipeline.MainPipeline()
    #database = db.Database("data")
    
    #questionbot_image = questionbot.QuestionBotOllama("llava")
    #image_prompt_pipeline = pipeline.ImagePromptPipeline(questionbot_image)
    #questionbot_openai = questionbot.QuestionBotOpenAIAPI(config("OPENAI_APIKEY"))
    #gpt_pipeline = pipeline.GptPipeline(questionbot_openai)
    #grammar_pipeline = pipeline.GrammarPipeline(question_bot)
    
    # image generation
    #processors = [texttoimage.StableHordeTextToImage(config("STABLEHORDE_APIKEY"))]
    #imagegen_api = texttoimage.FallbackTextToImageProcessor(processors)
    #imagegen_pipeline = pipeline.ImageGenerationPipeline(imagegen_api)
    #group_message_pipeline = pipeline.GroupMessageQuestionPipeline(database, summarizer, question_bot)
    #mainpipe.add_pipeline(group_message_pipeline)
    #mainpipe.add_pipeline(imagegen_pipeline)
    #mainpipe.add_pipeline(tts_pipeline)
    #mainpipe.add_pipeline(gpt_pipeline)
    #mainpipe.add_pipeline(image_prompt_pipeline)
    #mainpipe.add_pipeline(grammar_pipeline)
    
  
    # load ollama config if present
    bot_loader = BotLoader()
    CONFIG_OLLAMA = "ollama"
    if CONFIG_OLLAMA in configuration:
        ollama_server = configuration[CONFIG_OLLAMA]["host"]
        logging.info(f"Using Ollama server for question bots: {ollama_server}")
        bot_loader.set_ollama_server(ollama_server)

    # load llama.cpp config if present
    CONFIG_LLAMA_CPP = "llama_cpp"
    if CONFIG_LLAMA_CPP in configuration:
        llama_cpp_server = configuration[CONFIG_LLAMA_CPP]["host"]
        logging.info(f"Using llama.cpp server for question bots: {llama_cpp_server}")
        bot_loader.set_llama_cpp_server(llama_cpp_server)
    # General pipelines
    mark_seen_pipeline = pipeline.MarkSeenPipeline()
    mainpipe.add_pipeline(mark_seen_pipeline)

    # homeassistant commands and pipelines
    CONFIG_HOMEASSISTANT = "homeassistant"
    if CONFIG_HOMEASSISTANT in configuration:
        config_ha = configuration[CONFIG_HOMEASSISTANT]
        ha_token = config_ha["token"]
        ha_ws_api_url = config_ha["ws_api_url"]
        ha_chat_id_whitelist = config_ha.get("chat_id_whitelist", [])
        process_without_command = config_ha.get("process_without_command", False)
        
        ha_text_pipeline = pipeline.HomeassistantTextCommandPipeline(ha_token, ha_ws_api_url, \
            chat_id_whitelist=ha_chat_id_whitelist, process_without_command=process_without_command)
        ha_voice_pipeline = pipeline.HomeassistantVoiceCommandPipeline(ha_token, ha_ws_api_url, chat_id_whitelist=ha_chat_id_whitelist)
        ha_say_pipeline = pipeline.HomeassistantSayCommandPipeline(ha_token, ha_ws_api_url, chat_id_whitelist=ha_chat_id_whitelist)
        mainpipe.add_pipeline(ha_text_pipeline)
        mainpipe.add_pipeline(ha_voice_pipeline)
        mainpipe.add_pipeline(ha_say_pipeline)
    
    # gaudeam integration
    CONFIG_GAUDEAM = "gaudeam"
    if CONFIG_GAUDEAM in configuration:
        gaudeam_configs = configuration[CONFIG_GAUDEAM]
        for gaudeam_config in gaudeam_configs:
            gaudeam_session = gaudeam_config["gaudeam_session"]
            gaudeam_subdomain = gaudeam_config.get("gaudeam_subdomain")
            gaudeam = smrt.libgaudeam.Gaudeam(gaudeam_session, gaudeam_subdomain)
            chat_id_whitelist = gaudeam_config.get("chat_id_whitelist", None)
            chat_id_blacklist = gaudeam_config.get("chat_id_blacklist", None)
            gaudeam_pipeline = pipeline.GaudeamBdayPipeline(gaudeam, chat_id_whitelist, chat_id_blacklist)
            mainpipe.add_pipeline(gaudeam_pipeline)
            gaudeam_pipeline = pipeline.GaudeamCalendarPipeline(gaudeam, chat_id_whitelist, chat_id_blacklist)
            mainpipe.add_pipeline(gaudeam_pipeline)
            
            schedule_time = "09:00"
            # schedule daily birthday notifications
            bday_task = pipeline.GaudeamBdayScheduledTask(messenger_manager, chat_id_whitelist, gaudeam)
            
            schedule.every().day.at(schedule_time, "Europe/Berlin").do(bday_task.run)
            logging.info(f"Scheduled Gaudeam birthday notifications at {schedule_time} daily.")
            
            # schedule event notifications every day
            event_task = pipeline.GaudeamEventsScheduledTask(messenger_manager, chat_id_whitelist, gaudeam)
            schedule.every().day.at(schedule_time, "Europe/Berlin").do(event_task.run)
            logging.info(f"Scheduled Gaudeam event notifications at {schedule_time} daily.")

    # voice message transcription with whsisper
    CONFIG_VOICE_TRANSCRIPTION = "voice_transcription"
    if CONFIG_VOICE_TRANSCRIPTION in configuration:
        config_vt = configuration[CONFIG_VOICE_TRANSCRIPTION]
        vt_min_words_for_summary = config_vt.get("min_words_for_summary", 10)
        vt_chat_id_blacklist = config_vt.get("chat_id_blacklist", [])
        vt_transcriber = smrt.bot.tools.FasterWhisperTranscript()
        if "summary_bot" in config_vt:
            vt_summary_bot = bot_loader.create(config_vt["summary_bot"])
            vt_summarizer = smrt.bot.tools.QuestionBotSummary(vt_summary_bot)
        else:
            vt_summarizer = None
        voice_pipeline = pipeline.VoiceMessagePipeline(vt_transcriber,
                                                    vt_summarizer,
                                                    vt_min_words_for_summary,
                                                    chat_id_blacklist=vt_chat_id_blacklist)
        mainpipe.add_pipeline(voice_pipeline)

    CONFIG_TTS = "text_to_speech"
    if CONFIG_TTS in configuration:
        tts_pipeline = pipeline.TextToSpeechPipeline()
        mainpipe.add_pipeline(tts_pipeline)
    
    # load tinder pipeline if configured
    CONFIG_TINDER = "tinder"
    if CONFIG_TINDER in configuration:
        config_tinder = configuration[CONFIG_TINDER]
        chat_id_whitelist = config_tinder.get("chat_id_whitelist", None)
        chat_id_blacklist = config_tinder.get("chat_id_blacklist", None)
        tinder_bot = bot_loader.create(config_tinder["tinder_bot"])
        tinder_pipeline = pipeline.TinderPipeline(tinder_bot, chat_id_whitelist, chat_id_blacklist)
        mainpipe.add_pipeline(tinder_pipeline)
    
    # load pipeline for article summarization if configured
    CONFIG_ARTICLE_SUMMARY = "article_summary"
    if CONFIG_ARTICLE_SUMMARY in configuration:
        config_article_summary = configuration[CONFIG_ARTICLE_SUMMARY]
        chat_id_whitelist = config_article_summary.get("chat_id_whitelist", None)
        chat_id_blacklist = config_article_summary.get("chat_id_blacklist", None)
        article_summary_bot = bot_loader.create(config_article_summary["summary_bot"])
        article_summarizer = smrt.bot.tools.QuestionBotSummary(article_summary_bot)
        article_summary_pipeline = pipeline.URLSummaryPipeline(article_summarizer, chat_id_whitelist, chat_id_blacklist)
        mainpipe.add_pipeline(article_summary_pipeline)
    
    # image generation
    CONFIG_IMAGEGEN = "image_generation"
    if CONFIG_IMAGEGEN in configuration:
        import smrt.bot.tools.texttoimage as texttoimage
        config_imagegen = configuration[CONFIG_IMAGEGEN]
        imagegen_processors = []
        if "generator" in config_imagegen:
            if config_imagegen["generator"].startswith("stablehorde:"):
                stable_horde_api_key = config_imagegen["generator"][config_imagegen["generator"].find(":")+1:]
                imagegen_processors.append(texttoimage.StableHordeTextToImage(stable_horde_api_key))
                fallback_image_processor = texttoimage.FallbackTextToImageProcessor(imagegen_processors)
                mainpipe.add_pipeline(pipeline.ImagePromptPipeline(fallback_image_processor))
            else:
                raise ValueError(f"Unknown image generation processor: {config_imagegen['generator']}")

        if len(imagegen_processors) > 0:
            imagegen_api = texttoimage.FallbackTextToImageProcessor(imagegen_processors)
            imagegen_pipeline = pipeline.ImageGenerationPipeline(imagegen_api)
            mainpipe.add_pipeline(imagegen_pipeline)
    
    CONFIG_GALLERY = "gallery"
    if CONFIG_GALLERY in configuration:
        config_gallery = configuration[CONFIG_GALLERY]
        base_url = config_gallery["base_url"]
        port = config_gallery["port"]
        chat_id_whitelist = config_gallery.get("chat_id_whitelist", None)
        chat_id_blacklist = config_gallery.get("chat_id_blacklist", None)
        
        
        #import galleryweb
        gallery_db = smrt.db.GalleryDatabase(storage_path)

        gallery_pipe = pipeline.GalleryPipeline(gallery_db, base_url, chat_id_whitelist, chat_id_blacklist)
        mainpipe.add_pipeline(gallery_pipe)
        gallery_delete_pipe = pipeline.GalleryDeletePipeline(gallery_db, chat_id_whitelist, chat_id_blacklist)
        mainpipe.add_pipeline(gallery_delete_pipe)
        
        
        # run gallery flask app in own process if debug is True
        if debug_flag:
            def _serve_gallery(port):
                gallery_db = smrt.db.GalleryDatabase(storage_path)   # construct inside child process
                gallery_app = GalleryFlaskApp(gallery_db)
                # disable reloader/debug so Flask won't try to set signal handlers in this process
                gallery_app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)

            message_server_proc = Process(target=_serve_gallery, args=(port,), daemon=True)
            message_server_proc.start()
            logging.info(f"Started Gallery web server on port {port} (pid={message_server_proc.pid})")
        else:
            gallery_db = smrt.db.GalleryDatabase(storage_path)
            gallery_app = GalleryFlaskApp(gallery_db)
            from waitress import serve
            gallery_thread = threading.Thread(target=serve, args=(gallery_app._app,), kwargs={"port": port}, daemon=False)
            gallery_thread.start()
            logging.info(f"Started Gallery web server on port {port} in thread.")
    
    CONFIG_CHATID = "chatid"
    if CONFIG_CHATID in configuration:
        chatid_pipeline = smrt.bot.pipeline.ChatIdPipeline()
        mainpipe.add_pipeline(chatid_pipeline)

    # load all messengers
    CONFIG_SIGNAL = "signal"
    if CONFIG_SIGNAL in configuration:
        config_signal = configuration[CONFIG_SIGNAL]
        signal_messenger = messenger.SignalMessenger(config_signal["number"], config_signal["host"], int(config_signal["port"]))
        messenger_manager.add_messenger(signal_messenger)
        signal_queue = messagequeue.SignalMessageQueue(signal_messenger, mainpipe)
        signal_queue.run_async()
    
    CONFIG_TELEGRAM = "telegram"
    if CONFIG_TELEGRAM in configuration:
        config_telegram = configuration[CONFIG_TELEGRAM]
        telegram_messenger = messenger.TelegramMessenger(config_telegram["telegram_api_key"])
        messenger_manager.add_messenger(telegram_messenger)
        telegram_queue = messagequeue.TelegramMessageQueue(telegram_messenger, mainpipe)
        telegram_queue.run_async()

    CONFIG_WHATSAPP = "whatsapp"
    if CONFIG_WHATSAPP in configuration:

        config_whatsapp = configuration[CONFIG_WHATSAPP]
        whatsapp = messenger.WhatsappMessenger(config_whatsapp["wppconnect_server"], "smrt", config_whatsapp["wppconnect_api_key"])
        messenger_manager.add_messenger(whatsapp)
        whatsapp_queue = messagequeue.WhatsappMessageQueue(whatsapp, mainpipe)
        whatsapp_queue.run_async()

        try:
            whatsapp.start_session()
        except:
            logging.warning("Could not start Whatsapp session")
        #stock_notifier = SenateStockNotification(whatsapp)
        #mainpipe.add_pipeline(stock_notifier)
        #stock_notifier.run_async()

    # run scheduled tasks continuously in background
    stop_run_continuously = run_schedule_continuously()
    
    # run the message server
    message_server_port = 5000
    if debug_flag:
        def _serve_message(message_server_port):
            # disable reloader/debug so Flask won't try to set signal handlers in this process
            message_server.run(host="0.0.0.0", port=message_server_port, debug=True, use_reloader=False)

        message_server_proc = Process(target=_serve_message, args=(port,), daemon=True)
        message_server_proc.start()
        logging.info(f"Started Message server on port {port} (pid={message_server_proc.pid})")
    else:
        from waitress import serve
        gallery_thread = threading.Thread(target=serve, args=(message_server._app,), kwargs={"port": message_server_port}, daemon=False)
        gallery_thread.start()
        logging.info(f"Started Gallery web server on port {port} in thread.")
    


def run_schedule_continuously(interval=10):
    """Continuously run, while executing pending jobs at each
    elapsed time interval.
    @return cease_continuous_run: threading. Event which can
    be set to cease continuous run. Please note that it is
    *intended behavior that run_continuously() does not run
    missed jobs*. For example, if you've registered a job that
    should run every minute and you set a continuous run
    interval of one hour then your job won't be run 60 times
    at each interval but only once.
    """
    cease_continuous_run = threading.Event()

    class ScheduleThread(threading.Thread):
        @classmethod
        def run(cls):
            while not cease_continuous_run.is_set():
                schedule.run_pending()
                time.sleep(interval)

    continuous_thread = ScheduleThread()
    continuous_thread.start()
    return cease_continuous_run

if __name__ == "__main__":
    run()
