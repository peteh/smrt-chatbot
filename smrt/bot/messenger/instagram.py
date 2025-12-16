import logging

import threading
import time
import random
from typing import override, Callable
from pathlib import Path
from datetime import datetime, timedelta
from instagrapi import Client
from instagrapi.types import DirectMessage

from .messenger import MessengerInterface
from smrt.db import InstaMessageSeenDB

class InstagramMessenger(MessengerInterface):
    """Messenger implemention based on telebot api"""
    REACT_HOURGLASS_HALF = "\u231b"
    REACT_HOURGLASS_FULL = "\u23f3"
    REACT_CHECKMARK = "\u2714\ufe0f"
    REACT_SKIP = "\U0001F4A4"
    REACT_FAIL = "\u274c"

    def __init__(self, username: str, password: str, session_file: Path|str):
        session_file = Path(session_file)
        self._client = Client()
        self._client.delay_range = [1, 3]
        if session_file.exists():
            self._client.load_settings(session_file)
        self._client.login (username, password) # this doesn't actually login using username/password but uses the session
        self._client.dump_settings(session_file)

    def get_instagrapi(self) -> Client:
        return self._client

    @override
    def get_name(self) -> str:
        return "instagram"

    @override
    def mark_in_progress_0(self, message: dict | DirectMessage):
        #self._telebot.set_message_reaction(message.chat.id, message.message_id, telebot.types.ReactionTypeCustomEmoji(self.REACT_HOURGLASS_FULL))
        pass

    @override
    def mark_in_progress_50(self, message: dict | telebot.types.Message):
        #self._telebot.set_message_reaction(message.chat.id, message.message_id, telebot.types.ReactionTypeCustomEmoji(self.REACT_HOURGLASS_HALF))
        pass

    @override
    def mark_in_progress_done(self, message: dict | telebot.types.Message):
        #self._telebot.set_message_reaction(message.chat.id, message.message_id, telebot.types.ReactionTypeCustomEmoji(self.REACT_CHECKMARK))
        pass

    @override
    def mark_in_progress_fail(self, message: dict | telebot.types.Message):
        #self._telebot.set_message_reaction(message.chat.id, message.message_id, telebot.types.ReactionTypeCustomEmoji(self.REACT_FAIL))
        pass

    @override
    def mark_seen(self, message: dict | telebot.types.Message) -> None:
        # TODO
        return

    @override
    def is_group_message(self, message: dict | telebot.types.Message) -> bool:
        return message.chat.type in ['group', 'supergroup']

    @override
    def is_self_message(self, message: dict):
        # TODO implement
        return False

    @override
    def send_message(self, chat_id: str, text: str):
        # chat_id is in the format "telegram://<chat-id>"
        if chat_id.startswith("instagram://"):
            chat_id = chat_id.split("instagram://")[1]
        self._telebot.send_message(chat_id, text, parse_mode='Markdown')

    @override
    def send_message_to_group(self, group_message: dict | telebot.types.Message, text: str):
        self._telebot.send_message(group_message.chat.id, text, parse_mode='Markdown')

    @override
    def send_message_to_individual(self, message: dict | telebot.types.Message, text: str):
        # user needs to send at least one message to the bot before we can send messages to them
        user_id = message.from_user.id
        self._telebot.send_message(user_id, text, parse_mode='Markdown')

    @override
    def reply_message(self, message: dict | telebot.types.Message, text: str) -> None:
        self._telebot.reply_to(message, text, parse_mode='Markdown')

    @override
    def delete_message(self, message: dict):
        pass

    @override
    def _send_image(self, chat_id, file_name, binary_data, caption=""):
        pass

    @override
    def send_image_to_group(self, group_message: dict | telebot.types.Message, file_name, binary_data, caption = ""):
        # TODO: test
        self._send_image(group_message.chat.id, file_name, binary_data, caption)


    @override
    def send_image_to_individual(self, message: dict | telebot.types.Message, file_name, binary_data, caption = ""):
        # TODO: test
        user_id = message.from_user.id
        self._send_image(user_id, file_name, binary_data, caption)

    @override
    def send_audio_to_group(self, group_message: dict | telebot.types.Message, audio_file_path):
        pass

    @override
    def send_audio_to_individual(self, message: dict | telebot.types.Message, audio_file_path):
        pass

    @override
    def has_audio_data(self, message: dict):
        # TODO detect media type
        return False

    @override
    def has_image_data(self, message: dict):
        # TODO detect media type
        return False

    @override
    def is_bot_mentioned(self, message: dict):
        # TODO: implement bot mention detection
        return False

    @override
    def get_message_text(self, message: dict | telebot.types.Message) -> str:
        return message.text

    @override
    def get_chat_id(self, message: dict|DirectMessage) -> str:
        return f"instagram://{message.thread_id}"

    @override
    def get_sender_name(self, message: telebot.types.Message) -> str:
        return message.from_user.first_name if message.from_user else "Unknown"

    @override
    def download_media(self, message):
        # TODO: implement
        #return (mime_type, decoded)
        return None

    @override
    def send_typing(self, message: dict, typing: bool):
        return

class InstagramMessageQueue():

    def __init__(self, messenger_instance: InstagramMessenger, seen_db: InstaMessageSeenDB, callback: Callable[[MessengerInterface, dict], None]) -> None:
        self._messenger = messenger_instance
        self._seen_db = seen_db
        self._callback = callback
        self._thread = None
        

    def run_async(self):
        self._thread = threading.Thread(target=self.run)
        self._thread.start()

    def on_new_message(self, data):
        logging.info(f"Received new message: {data}")
        self._callback(self._messenger, data)


    def run(self):
        cl = self._messenger.get_instagrapi()
        while True:
            try:
                threads = cl.direct_threads(10) #, selected_filter="unread")
                for thread in threads:
                    print(thread.id, thread.thread_title, thread.thread_type)
                    messages = cl.direct_messages(int(thread.id), amount=5)
                    messages = reversed(messages)
                    for message in messages:
                        # skip messages that we have already seen
                        if self._seen_db.has_seen_message(message.id):
                            logging.info(f"Skipping seen message {message.id}")
                            continue
                        self._seen_db.add_seen_message(message.id)

                        # skip messages that are older than 1 day
                        # TODO figure out timezone issues here
                        if datetime.now() - message.timestamp > timedelta(days=1):
                            logging.info(f"Skipping old message {message.id}")
                            continue
                        self.on_new_message(message)
            except Exception as e:
                logging.error(f"Error in InstagramMessageQueue: {e}")
            
            # random 45 to 75 seconds sleep to avoid rate limiting
            time.sleep(random.randint(45, 75))