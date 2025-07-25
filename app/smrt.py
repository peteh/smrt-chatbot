"""Main application"""
import time
import logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
from flask import Flask, request, jsonify

from main_pipeline import MainPipeline
from senate_stocks import SenateStockNotification
import pipeline
import pipeline_all
import pipeline_ha
import questionbot
import transcript
import summary
import yaml
import texttoimage



schema = {
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
    "tinder": {
        "type": "dict",
        "schema": {
            "tinder_bot": {"type": "string", "required": True}
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
        
    def create(self, bot_name: str) -> questionbot.QuestionBotInterface:
        """Factory function to create a question bot instance based on the bot name."""
        if bot_name.startswith("ollama:"):
            if self._ollama_server is None:
                raise ValueError("Ollama server not set. Use \"ollama:\" configuration option to set it.")
            model_name = bot_name[bot_name.find(":")+1:]
            logging.debug(f"Creating QuestionBotOllama with model: {model_name}")
            return questionbot.QuestionBotOllama(self._ollama_server, model_name)
        elif bot_name.startswith("llama_cpp:"):
            if self._llama_cpp_server is None:
                raise ValueError("Llama.cpp server not set. Use set_llama_cpp_server() to set it.")
            #model_name = bot_name[bot_name.find(":")+1:]
            #logging.debug(f"Creating QuestionBotLlamaCppServer with model: {model_name}")
            return questionbot.QuestionBotLlamaCppServer(self._llama_cpp_server)
        elif bot_name.startswith("openai:"):
            api_key = bot_name[bot_name.find(":"):]
            return questionbot.QuestionBotOpenAIAPI(api_key)
        else:
            raise ValueError(f"Unknown bot name: {bot_name}")

class MessageServer:
    def __init__(self, host='0.0.0.0', port=5000):
        self.app = Flask(__name__)
        self.host = host
        self.port = port
        self._register_routes()
        self._messengers = {}
        self.app.logger.setLevel(logging.INFO)

    def _register_routes(self):
        @self.app.route('/send_message', methods=['POST'])
        def send_message():
            data = request.get_json()
            self.app.logger.debug(f"Received data: {data}")
            if not data or 'chatIds' not in data or 'message' not in data:
                self.app.logger.error("Missing required fields in request data, expected 'chatIds' and 'message'")
                self.app.logger.error(f"Message data: {data}")
                return jsonify({'error': 'Missing required fields: chatIds and message'}), 400

            chat_ids = data['chatIds']
            message = data['message']

            if not isinstance(chat_ids, list) or not isinstance(message, str):
                return jsonify({'error': 'Invalid types: chatids must be a list, message must be a string'}), 400

            print(f"Sending message '{message}' to chat IDs: {chat_ids}")
            error=""
            sent_to = []
            for chat_id in chat_ids:
                messenger = self._get_messenger_by_chatid(chat_id)
                if messenger:
                    try:
                        messenger.send_message(chat_id, message)
                        sent_to.append(chat_id)
                    except Exception as e:
                        error_message = f"Error sending message to {chat_id}: {str(e)}"
                        error += f"{error_message}\n"
                        self.app.logger.error(f"Failed to send message to {chat_id}: {e}")
                else:
                    error_message = f"No messenger found for chat ID: {chat_id}"
                    self.app.logger.warning(error_message)
                    error+= f"{error_message}\n"

            if len(error) > 0:
                return jsonify({'status': 'error', 'message': error, 'sent_to': sent_to}), 500
            return jsonify({'status': 'success', 'sent_to': sent_to}), 200

    def add_messenger(self, messenger):
        self._messengers[messenger.get_name()] = messenger
    
    def _get_messenger_by_chatid(self, chat_id: str):
        identifier = chat_id.split("://")[0]  # Extract the identifier from the chat_id
        
        if identifier in self._messengers:
            return self._messengers[identifier]
        return None
    
    def run(self):
        self.app.run(host=self.host, port=self.port)

def run():
    config_file = open("config.yml", "r", encoding="utf-8")
    configuration = yaml.safe_load(config_file)
    config_file.close()
    
    message_server = MessageServer()
    

    if not validate_config(configuration, schema):
        exit(1)
    
    mainpipe = MainPipeline()
    #database = db.Database("data")
    
    #questionbot_image = questionbot.QuestionBotOllama("llava")
    #image_prompt_pipeline = pipeline.ImagePromptPipeline(questionbot_image)
    #questionbot_openai = questionbot.QuestionBotOpenAIAPI(config("OPENAI_APIKEY"))
    #gpt_pipeline = pipeline.GptPipeline(questionbot_openai)
    #tts_pipeline = pipeline_tts.TextToSpeechPipeline()
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
        
        ha_text_pipeline = pipeline_ha.HomeassistantTextCommandPipeline(ha_token, ha_ws_api_url, \
            chat_id_whitelist=ha_chat_id_whitelist, process_without_command=process_without_command)
        ha_voice_pipeline = pipeline_ha.HomeassistantVoiceCommandPipeline(ha_token, ha_ws_api_url, chat_id_whitelist=ha_chat_id_whitelist)
        ha_say_pipeline = pipeline_ha.HomeassistantSayCommandPipeline(ha_token, ha_ws_api_url, chat_id_whitelist=ha_chat_id_whitelist)
        mainpipe.add_pipeline(ha_text_pipeline)
        mainpipe.add_pipeline(ha_voice_pipeline)
        mainpipe.add_pipeline(ha_say_pipeline)

    # voice message transcription with whsisper
    CONFIG_VOICE_TRANSCRIPTION = "voice_transcription"
    if CONFIG_VOICE_TRANSCRIPTION in configuration:
        config_vt = configuration[CONFIG_VOICE_TRANSCRIPTION]
        vt_min_words_for_summary = config_vt.get("min_words_for_summary", 10)
        vt_chat_id_blacklist = config_vt.get("chat_id_blacklist", [])
        vt_transcriber = transcript.FasterWhisperTranscript()
        if "summary_bot" in config_vt:
            vt_summary_bot = bot_loader.create(config_vt["summary_bot"])
            vt_summarizer = summary.QuestionBotSummary(vt_summary_bot)
        else:
            vt_summarizer = None
        voice_pipeline = pipeline_all.VoiceMessagePipeline(vt_transcriber,
                                                    vt_summarizer,
                                                    vt_min_words_for_summary,
                                                    chat_id_blacklist=vt_chat_id_blacklist)
        mainpipe.add_pipeline(voice_pipeline)

    # load tinder pipeline if configured
    CONFIG_TINDER = "tinder"
    if CONFIG_TINDER in configuration:
        config_tinder = configuration[CONFIG_TINDER]
        tinder_bot = bot_loader.create(config_tinder["tinder_bot"])
        tinder_pipeline = pipeline_all.TinderPipeline(tinder_bot)
        mainpipe.add_pipeline(tinder_pipeline)
    
    # load pipeline for article summarization if configured
    CONFIG_ARTICLE_SUMMARY = "article_summary"
    if CONFIG_ARTICLE_SUMMARY in configuration:
        config_article_summary = configuration[CONFIG_ARTICLE_SUMMARY]
        article_summary_bot = bot_loader.create(config_article_summary["summary_bot"])
        article_summarizer = summary.QuestionBotSummary(article_summary_bot)
        article_summary_pipeline = pipeline_all.ArticleSummaryPipeline(article_summarizer)
        mainpipe.add_pipeline(article_summary_pipeline)
    
    # image generation
    CONFIG_IMAGEGEN = "image_generation"
    if CONFIG_IMAGEGEN in configuration:
        config_imagegen = configuration[CONFIG_IMAGEGEN]
        imagegen_processors = []
        if "generator" in config_imagegen:
            if config_imagegen["generator"].startswith("stablehorde:"):
                stable_horde_api_key = config_imagegen["generator"][config_imagegen["generator"].find(":")+1:]
                imagegen_processors.append(texttoimage.StableHordeTextToImage(stable_horde_api_key))
                fallback_image_processor = texttoimage.FallbackTextToImageProcessor(imagegen_processors)
                mainpipe.add_pipeline(pipeline_all.ImagePromptPipeline(fallback_image_processor))
            else:
                raise ValueError(f"Unknown image generation processor: {config_imagegen['generator']}")

        if len(imagegen_processors) > 0:
            imagegen_api = texttoimage.FallbackTextToImageProcessor(imagegen_processors)
            imagegen_pipeline = pipeline_all.ImageGenerationPipeline(imagegen_api)
            mainpipe.add_pipeline(imagegen_pipeline)

    CONFIG_CHATID = "chatid"
    if CONFIG_CHATID in configuration:
        chatid_pipeline = pipeline.ChatIdPipeline()
        mainpipe.add_pipeline(chatid_pipeline)


    # load all messengers
    CONFIG_SIGNAL = "signal"
    if CONFIG_SIGNAL in configuration:
        import messenger_signal
        config_signal = configuration[CONFIG_SIGNAL]
        signal_messenger = messenger_signal.SignalMessenger(config_signal["number"], config_signal["host"], int(config_signal["port"]))
        message_server.add_messenger(signal_messenger)
        signal_queue = messenger_signal.SignalMessageQueue(signal_messenger, mainpipe)
        signal_queue.run_async()
    
    CONFIG_TELEGRAM = "telegram"
    if CONFIG_TELEGRAM in configuration:
        import messenger_telegram
        config_telegram = configuration[CONFIG_TELEGRAM]
        telegram_messenger = messenger_telegram.TelegramMessenger(config_telegram["telegram_api_key"])
        message_server.add_messenger(telegram_messenger)
        telegram_queue = messenger_telegram.TelegramMessageQueue(telegram_messenger, mainpipe)
        telegram_queue.run_async()

    CONFIG_WHATSAPP = "whatsapp"
    if CONFIG_WHATSAPP in configuration:
        import messenger_whatsapp
        config_whatsapp = configuration[CONFIG_WHATSAPP]
        whatsapp = messenger_whatsapp.Whatsapp(config_whatsapp["wppconnect_server"], "smrt", config_whatsapp["wppconnect_api_key"])
        message_server.add_messenger(whatsapp)
        whatsapp_queue = messenger_whatsapp.WhatsappMessageQueue(whatsapp, mainpipe)
        whatsapp_queue.run_async()

        try:
            whatsapp.start_session()
        except:
            logging.warning("Could not start Whatsapp session")
        #stock_notifier = SenateStockNotification(whatsapp)
        #mainpipe.add_pipeline(stock_notifier)
        #stock_notifier.run_async()
    
    message_server.run()

if __name__ == "__main__":
    run()
