"""Main application"""
import time
import logging
import threading
from multiprocessing import Process
from pathlib import Path
import schedule
import yaml
from cerberus import Validator
import smrt.db
import smrt.bot.pipeline as pipeline
import smrt.bot.messenger as messenger
from smrt.web.galleryweb import GalleryFlaskApp
import smrt.bot.tools
from smrt.libgaudeam import GaudeamCalendar, GaudeamSession, GaudeamMembers
from smrt.libtranscript import FasterWhisperTranscript, WyomingTranscript
from smrt.bot.tools.question_bot import QuestionBotInterface, QuestionBotOllama, QuestionBotLlamaCppServer
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

schema = {}
schema["storage_path"] = {"type": "string", "required": False}

schema["article_summary"] = {
    "type": "dict",
    "schema": {
        "summary_bot": {"type": "string", "required": True}
    },
    "required": False
}

schema["image_generation"] = {
    "type": "dict",
    "schema": {
        "generator": {"type": "string", "required": True}
    },
    "required": False
}

schema["chatid"] = {
    "type": "dict",
    "schema": {},
    "nullable": True,  # Accepts `null` or empty dict as valid
    "required": False
}

schema["debug"] = {
    "type": "dict",
    "schema": {},
    "nullable": True,  # Accepts `null` or empty dict as valid
    "required": False
}

## messenger configuration schemas
schema["signal"] = {
    "type": "dict",
    "schema": {
        "host": {"type": "string", "required": True},
        "port": {"type": "integer", "required": True},
        "number": {"type": "string", "required": True}
    },
    "required": False
}

schema["whatsapp"] = {
    "type": "dict",
    "schema": {
        "wppconnect_api_key": {"type": "string", "required": True},
        "wppconnect_server": {"type": "string", "required": True},
        "lid": {"type": "string", "required": False}
    },
    "required": False
}

schema["telegram"] = {
    "type": "dict",
    "schema": {
        "telegram_api_key": {"type": "string", "required": True},
    },
    "required": False
}

schema["telethon"] = {
    "type": "dict",
    "schema": {
        "api_id": {"type": "integer", "required": True},
        "api_key": {"type": "string", "required": True},
        "bot_token": {"type": "string", "required": True},
    },
    "required": False
}

schema["text_to_speech"] = {
    "type": "dict",
    "schema": {},
    "nullable": True,  # Accepts `null` or empty dict as valid
    "required": False
}

schema["tinder"] = {
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
}

schema["voice_transcription"] = {
    "type": "dict",
    "schema": {
        "min_words_for_summary": {"type": "integer", "required": True},
        "asr_engine":  {"type": "string", "required": False},
        "summary_bot": {"type": "string", "required": False},
        "chat_id_blacklist": {
            "type": "list",
            "schema": {"type": "string"},
            "required": False
        }
    },
    "required": False
}

schema["homeassistant"] = {
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
}

schema["gallery"] = {
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
}

schema["ccc"] = {
    "type": "dict",
    "schema": {
        "chat_id_whitelist": {
            "type": "list",
            "schema": {"type": "string"},
            "required": True
        }
    },
    "required": False
}

schema["netcup"] = {
    "type": "dict",
    "schema": {
        "chat_id_whitelist": {
            "type": "list",
            "schema": {"type": "string"},
            "required": True
        }
    },
    "required": False
}

schema["message_gpt"] = {
    "type": "dict",
    "schema": {
        "answer_bot": {"type": "string", "required": True},
        "max_chat_history_messages": {"type": "integer", "required": False}
    },
    "required": False
}

schema["gaudeam"]= {
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

schema["ai"] = {
    "type": "list",
    "schema": {
        "type": "dict",
        "schema": {
            "ollama": {
                "type": "dict",
                "schema": {
                    "name": {"type": "string", "required": True},     # mandatory
                    "model": {"type": "string", "required": True},    # mandatory
                    "host": {"type": "string", "required": True},     # mandatory
                    # optional fields can be added here
                },
                "required": False
            },
            "llama_cpp": {
                "type": "dict",
                "schema": {
                    "name": {"type": "string", "required": True},     # mandatory
                    "model": {"type": "string", "required": True},    # mandatory
                    "host": {"type": "string", "required": True},     # mandatory
                    # optional fields can be added here
                },
                "required": False
            }
        }
    },
    "required": False
}

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
        self._bots = {}

    def add_bot(self, bot_name: str, bot_instance: QuestionBotInterface):
        """Add a bot instance with the given name."""
        if bot_name in self._bots:
            raise ValueError(f"Bot with name {bot_name} already exists.")
        self._bots[bot_name] = bot_instance

    def get_bot(self, bot_name: str) -> QuestionBotInterface:
        """Get a bot instance by name."""
        if bot_name not in self._bots:
            raise ValueError(f"Bot with name {bot_name} does not exist.")
        return self._bots[bot_name]


def run():
    config_file = open("config.yml", "r", encoding="utf-8")
    configuration = yaml.safe_load(config_file)
    config_file.close()

    messenger_manager = messenger.MessengerManager()
    message_server = messenger.MessageServerFlaskApp(messenger_manager)

    if not validate_config(configuration, schema):
        exit(1)

    CONFIG_DEBUG = "debug"
    debug_flag = False
    if CONFIG_DEBUG in configuration:
        debug_flag = True
    storage_path = Path(configuration.get("storage_path", "/storage/"))
    logging.info(f"Using storage path: {storage_path}")

     # create main pipeline

    mainpipe = pipeline.MainPipeline()
    #database = db.Database("data")

    #questionbot_image = questionbot.QuestionBotOllama("llava")
    #image_prompt_pipeline = pipeline.ImagePromptPipeline(questionbot_image)
    #grammar_pipeline = pipeline.GrammarPipeline(question_bot)

    # image generation
    #processors = [texttoimage.StableHordeTextToImage(config("STABLEHORDE_APIKEY"))]
    #imagegen_api = texttoimage.FallbackTextToImageProcessor(processors)
    #imagegen_pipeline = pipeline.ImageGenerationPipeline(imagegen_api)
    #mainpipe.add_pipeline(group_message_pipeline)
    #mainpipe.add_pipeline(imagegen_pipeline)
    #mainpipe.add_pipeline(image_prompt_pipeline)
    #mainpipe.add_pipeline(grammar_pipeline)

    # load ollama config if present
    bot_loader = BotLoader()
    
    CONFIG_AI = "ai"
    if CONFIG_AI in configuration:
        ai_configs = configuration[CONFIG_AI]
        for ai_config in ai_configs:
            if "ollama" in ai_config:
                ollama_conf = ai_config["ollama"]
                ollama_server = ollama_conf["host"]
                model = ollama_conf["model"]
                bot_loader.add_bot(ollama_conf["name"], QuestionBotOllama(ollama_server, model))
                logging.info(f"Registered Ollama '{ollama_conf['name']}' with model '{model}' at {ollama_server}")
            if "llama_cpp" in ai_config:
                llama_cpp_conf = ai_config["llama_cpp"]
                llama_cpp_server = llama_cpp_conf["host"]
                bot_loader.add_bot(llama_cpp_conf["name"], QuestionBotLlamaCppServer(llama_cpp_server))
                logging.info(f"Registered llama.cpp model {llama_cpp_conf['name']} at {llama_cpp_server}")
    
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
            gaudeam_session_cookie = gaudeam_config["gaudeam_session"]
            gaudeam_subdomain = gaudeam_config.get("gaudeam_subdomain")
            gaudeam_session = GaudeamSession(gaudeam_session_cookie, gaudeam_subdomain)
            gaudeam_calendar = GaudeamCalendar(gaudeam_session)
            gaudeam_members = GaudeamMembers(gaudeam_session)

            chat_id_whitelist = gaudeam_config.get("chat_id_whitelist", None)
            chat_id_blacklist = gaudeam_config.get("chat_id_blacklist", None)
            gaudeam_pipeline = pipeline.GaudeamBdayPipeline(gaudeam_members, chat_id_whitelist, chat_id_blacklist)
            mainpipe.add_pipeline(gaudeam_pipeline)
            gaudeam_pipeline = pipeline.GaudeamCalendarPipeline(gaudeam_calendar, chat_id_whitelist, chat_id_blacklist)
            mainpipe.add_pipeline(gaudeam_pipeline)

            schedule_time = "09:00"
            # schedule daily birthday notifications
            bday_task = pipeline.GaudeamBdayScheduledTask(messenger_manager, chat_id_whitelist, gaudeam_members)

            schedule.every().day.at(schedule_time, "Europe/Berlin").do(bday_task.run)
            logging.info(f"Scheduled Gaudeam birthday notifications at {schedule_time} daily.")

            # schedule event notifications every day
            event_task = pipeline.GaudeamEventsScheduledTask(messenger_manager, chat_id_whitelist, gaudeam_calendar)
            schedule.every().day.at(schedule_time, "Europe/Berlin").do(event_task.run)
            logging.info(f"Scheduled Gaudeam event notifications at {schedule_time} daily.")

    # message answer pipeline
    CONFIG_MESSAGE_GPT = "message_gpt"
    if CONFIG_MESSAGE_GPT in configuration:
        config_ma = configuration[CONFIG_MESSAGE_GPT]
        answer_bot = bot_loader.get_bot(config_ma["answer_bot"])
        chat_id_whitelist = config_ma.get("chat_id_whitelist", None)
        chat_id_blacklist = config_ma.get("chat_id_blacklist", None)
        max_chat_history_messages = config_ma.get("max_chat_history_messages", 20)
        message_db = smrt.db.MessageDatabase(storage_path)
        message_answer_pipeline = pipeline.MessageQuestionPipeline(message_db,answer_bot, max_chat_history_messages,
                                                                   chat_id_whitelist, chat_id_blacklist)
        mainpipe.add_pipeline(message_answer_pipeline)
        logging.info("Loaded Message GPT Pipeline.")

    # voice message transcription with whsisper
    CONFIG_VOICE_TRANSCRIPTION = "voice_transcription"
    if CONFIG_VOICE_TRANSCRIPTION in configuration:
        config_vt = configuration[CONFIG_VOICE_TRANSCRIPTION]
        vt_min_words_for_summary = config_vt.get("min_words_for_summary", 10)
        vt_chat_id_blacklist = config_vt.get("chat_id_blacklist", [])
        asr_engine = config_vt.get("asr_engine", "faster_whisper")
        if asr_engine == "faster_whisper":
            vt_transcriber = FasterWhisperTranscript()
        else:
            if not asr_engine.startswith("tcp://"):
                raise ValueError("asr_engine must 'faster_whisper' or uri to wyoming server, e.g. tcp://127.0.0.1:10300")
            vt_transcriber = WyomingTranscript(asr_engine)
        if "summary_bot" in config_vt:
            vt_summary_bot = bot_loader.get_bot(config_vt["summary_bot"])
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
        tts_pipeline = pipeline.TextToSpeechPipeline(storage_path / "custom_models")
        mainpipe.add_pipeline(tts_pipeline)

    # load tinder pipeline if configured
    CONFIG_TINDER = "tinder"
    if CONFIG_TINDER in configuration:
        config_tinder = configuration[CONFIG_TINDER]
        chat_id_whitelist = config_tinder.get("chat_id_whitelist", None)
        chat_id_blacklist = config_tinder.get("chat_id_blacklist", None)
        tinder_bot = bot_loader.get_bot(config_tinder["tinder_bot"])
        tinder_pipeline = pipeline.TinderPipeline(tinder_bot, chat_id_whitelist, chat_id_blacklist)
        mainpipe.add_pipeline(tinder_pipeline)

    # load pipeline for article summarization if configured
    CONFIG_ARTICLE_SUMMARY = "article_summary"
    if CONFIG_ARTICLE_SUMMARY in configuration:
        config_article_summary = configuration[CONFIG_ARTICLE_SUMMARY]
        chat_id_whitelist = config_article_summary.get("chat_id_whitelist", None)
        chat_id_blacklist = config_article_summary.get("chat_id_blacklist", None)
        article_summary_bot = bot_loader.get_bot(config_article_summary["summary_bot"])
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
        gallery_port = config_gallery.get("port", 9000)
        chat_id_whitelist = config_gallery.get("chat_id_whitelist", None)
        chat_id_blacklist = config_gallery.get("chat_id_blacklist", None)

        gallery_db = smrt.db.GalleryDatabase(storage_path)

        gallery_pipe = pipeline.GalleryPipeline(gallery_db, base_url, chat_id_whitelist, chat_id_blacklist)
        mainpipe.add_pipeline(gallery_pipe)
        gallery_delete_pipe = pipeline.GalleryDeletePipeline(gallery_db, chat_id_whitelist, chat_id_blacklist)
        mainpipe.add_pipeline(gallery_delete_pipe)

        gallery_app = GalleryFlaskApp(gallery_db)

        # run gallery flask app if debug is True
        if debug_flag:
            def _serve_gallery(port):
                gallery_app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)

            message_server_proc = Process(target=_serve_gallery, args=(gallery_port,), daemon=True)
            message_server_proc.start()
            logging.info(f"Started Gallery web server on port {gallery_port} (pid={message_server_proc.pid})")
        else:
            from waitress import serve
            gallery_thread = threading.Thread(target=serve, args=(gallery_app.get_app(),), kwargs={"port": gallery_port}, daemon=False)
            gallery_thread.start()
            logging.info(f"Started Gallery web server on port {gallery_port} in thread.")

    CONFIG_CHATID = "chatid"
    if CONFIG_CHATID in configuration:
        chatid_pipeline = pipeline.ChatIdPipeline()
        mainpipe.add_pipeline(chatid_pipeline)
        lid_pipeline = pipeline.WhatsappLidPipeline()
        mainpipe.add_pipeline(lid_pipeline)

    CONFIG_CCC = "ccc"
    if CONFIG_CCC in configuration:
        config_ccc = configuration[CONFIG_CCC]
        chat_id_whitelist = config_ccc.get("chat_id_whitelist", [])
        ccc_task = pipeline.CCCScheduledTask(messenger_manager, chat_id_whitelist)
        # run in background thread as we want to schedule internally
        threading.Thread(target=ccc_task.run, daemon=True).start()
    
    CONFIG_NETCUP = "netcup"
    if CONFIG_NETCUP in configuration:
        config_netcup = configuration[CONFIG_NETCUP]
        chat_id_whitelist = config_netcup.get("chat_id_whitelist", [])
        netcup_task = pipeline.NetcupScheduledTask(messenger_manager, chat_id_whitelist)
        # run in background thread as we want to schedule internally
        threading.Thread(target=netcup_task.run, daemon=True).start()

    # load all messengers
    CONFIG_SIGNAL = "signal"
    if CONFIG_SIGNAL in configuration:
        config_signal = configuration[CONFIG_SIGNAL]
        signal_messenger = messenger.SignalMessenger(config_signal["number"], config_signal["host"], int(config_signal["port"]))
        messenger_manager.add_messenger(signal_messenger)
        signal_queue = messenger.SignalMessageQueue(signal_messenger, mainpipe.process)
        signal_queue.run_async()

    CONFIG_TELEGRAM = "telegram"
    if CONFIG_TELEGRAM in configuration:
        config_telegram = configuration[CONFIG_TELEGRAM]
        telegram_messenger = messenger.TelegramMessenger(config_telegram["telegram_api_key"])
        messenger_manager.add_messenger(telegram_messenger)
        telegram_queue = messenger.TelegramMessageQueue(telegram_messenger, mainpipe.process)
        telegram_queue.run_async()
    
    CONFIG_TELETHON = "telethon"
    if CONFIG_TELETHON in configuration:
        config_telethon = configuration[CONFIG_TELETHON]
        telethon_messenger = messenger.TelethonMessenger(config_telethon["api_id"], config_telethon["api_key"], config_telethon["bot_token"])
        messenger_manager.add_messenger(telethon_messenger)
        telethon_queue = messenger.TelethonMessageQueue(telethon_messenger, mainpipe.process)
        telethon_queue.run_async()

    CONFIG_WHATSAPP = "whatsapp"
    if CONFIG_WHATSAPP in configuration:

        config_whatsapp = configuration[CONFIG_WHATSAPP]
        lid = config_whatsapp.get("lid", "")
        whatsapp = messenger.WhatsappMessenger(config_whatsapp["wppconnect_server"],
                                               "smrt", 
                                               config_whatsapp["wppconnect_api_key"],
                                               lid)

        messenger_manager.add_messenger(whatsapp)
        whatsapp_queue = messenger.WhatsappMessageQueue(whatsapp, mainpipe.process)
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

        message_server_proc = Process(target=_serve_message, args=(message_server_port,), daemon=True)
        message_server_proc.start()
        logging.info(f"Started Message server on port {message_server_port} (pid={message_server_proc.pid})")
    else:
        from waitress import serve
        gallery_thread = threading.Thread(target=serve, args=(message_server.get_app(),), kwargs={"port": message_server_port}, daemon=False)
        gallery_thread.start()
        logging.info(f"Started Message server on port {message_server_port} in thread.")

    # run mainapp forever
    while True:
        time.sleep(10)

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
