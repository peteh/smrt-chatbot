
import logging
import threading
from smrt.bot.messenger.telegram import TelegramMessenger
from smrt.bot.pipeline import MainPipeline

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
            logging.info(f"Received new message: {message}")
            self._mainpipe.process(self._messenger, message)
            

    def get_messages(self):
        self._telebot.infinity_polling()
    
    def run_async(self):
        self._thread = threading.Thread(target=self.get_messages)
        self._thread.start()
