import logging
import threading
import telebot
from messenger import MessengerInterface
from main_pipeline import MainPipeline

class TelegramMessenger(MessengerInterface):
    """Messenger implemenation based on telebot api"""


    def __init__(self, api_key: str):
        self._telebot = telebot.TeleBot(api_key)

    def get_telebot(self) -> telebot.TeleBot:
        return self._telebot

    def mark_in_progress_0(self, message: dict):
        pass

    def mark_in_progress_50(self, message: dict):
        pass

    def mark_in_progress_done(self, message: dict):
        pass

    def mark_in_progress_fail(self, message: dict):
        pass

    def mark_seen(self, message: dict) -> None:
        pass

    def is_group_message(self, message: dict):
        # TODO implement
        return False

    def is_self_message(self, message: dict):
        # TODO implement
        return False

    def send_message_to_group(self, group_message: dict, text: str):
        #self._send_message(group_message['chatId'], True, text)
        pass

    def send_message_to_individual(self, message: dict, text: str):
        #self._send_message(message['sender']['id'], False, text)
        pass

    def reply_message(self, message: dict, text: str) -> None:
        self._telebot.reply_to(message, text)

    def delete_message(self, message: dict):
        pass


    def send_image_to_group(self, group_message, file_name, binary_data, caption = ""):
        pass

    def send_image_to_individual(self, message, file_name, binary_data, caption = ""):
        pass

    def send_audio_to_group(self, group_message, audio_file_path):
        pass

    def send_audio_to_individual(self, message, audio_file_path):
        pass

    def has_audio_data(self, message: dict):
        # TODO detect media type
        return False

    def has_image_data(self, message: dict):
        # TODO detect media type
        return False

    def is_bot_mentioned(self, message: dict):
        # TODO: implement bot mention detection
        return False

    def get_message_text(self, message: dict | telebot.types.Message) -> str:
        return message.text

    def get_chat_id(self, message: telebot.types.Message) -> str:
        return f"telegram://{message.chat.id}"

    def get_sender_name(self, message: dict):
        # TODO: implement
        return ""

    def download_media(self, message):
        # TODO: implement
        #return (mime_type, decoded)
        return None
    
class TelegramMessageQueue():
    """Implementation to read messages from Telegram bot api """

    def __init__(self, messenger_instance: TelegramMessenger, mainpipe: MainPipeline) -> None:
        self._messenger = messenger_instance
        self._telebot = messenger_instance.get_telebot()
        self._mainpipe = mainpipe
        self._thread = None
        self.register_handlers()
    
    def register_handlers(self):
        @self._telebot.message_handler(commands=['help', 'start'])
        def send_welcome(message):
            self._telebot.reply_to(message, (
                "Hi there, I am EchoBot.\n"
                "I am here to echo your kind words back to you. "
                "Just say anything nice and I'll say the exact same thing to you!"
            ))

        @self._telebot.message_handler(func=lambda message: True)
        def handle_message(message):
            self._mainpipe.process(self._messenger, message)
            

    def get_messages(self):
        self._telebot.infinity_polling()
    
    def run_async(self):
        self._thread = threading.Thread(target=self.get_messages)
        self._thread.start()
