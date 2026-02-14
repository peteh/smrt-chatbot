import asyncio
from typing import override, Callable
import logging
import threading

from .messenger import MessengerInterface
from telethon import TelegramClient, events
from telethon.tl.types import Message
from telethon.tl.types import PeerUser, PeerChat, PeerChannel
import yaml


class TelethonMessenger(MessengerInterface):
    """Messenger implemention based on telebot api"""
    REACT_HOURGLASS_HALF = "\u231b"
    REACT_HOURGLASS_FULL = "\u23f3"
    REACT_CHECKMARK = "\u2714\ufe0f"
    REACT_SKIP = "\U0001F4A4"
    REACT_FAIL = "\u274c"

    def __init__(self, api_id: str, api_key: str, bot_token: str):
        self._api_id = api_id
        self._api_key = api_key
        self._bot_token = bot_token
        self._client = None
        

    def get_telebot(self) -> TelegramClient:
        if self._client is None:
            self._client = TelegramClient('bot', self._api_id, self._api_key).start(bot_token=self._bot_token)
        return self._client

    @override
    def get_name(self) -> str:
        return "telethon"

    @override
    def mark_in_progress_0(self, message: dict | Message):
        pass

    @override
    def mark_in_progress_50(self, message: dict | Message):
        pass

    @override
    def mark_in_progress_done(self, message: dict | Message):
        pass

    @override
    def mark_in_progress_fail(self, message: dict | Message):
        pass

    @override
    def mark_seen(self, message: dict | Message) -> None:
        # Telegram API does not support marking messages as seen
        return
    
    @override
    def mark_unseen(self, message: dict | Message) -> None:
        # Telegram API does not support marking messages as unseen
        return

    @override
    def is_group_message(self, message: dict | Message) -> bool:
        # message.to_id can be PeerUser (private), PeerChat (small group), PeerChannel (supergroup/channel)
        to_id = message.to_id
        if isinstance(to_id, PeerUser):
            return False
        elif isinstance(to_id, (PeerChat, PeerChannel)):
            return True
        return False

    @override
    def is_self_message(self, message: dict):
        # TODO implement
        return False

    @override
    def send_message(self, chat_id: str, text: str):
        # chat_id is in the format "telegram://<chat-id>"
        if chat_id.startswith("telethon://"):
            chat_id = chat_id.split("telethon://")[1]
        #self._telebot.send_message(chat_id, text, parse_mode='Markdown')

    @override
    def send_message_to_group(self, group_message: dict | Message, text: str):
        pass

    @override
    def send_message_to_individual(self, message: dict | Message, text: str):
        # user needs to send at least one message to the bot before we can send messages to them
        pass

    @override
    def reply_message(self, message: dict | Message, text: str) -> None:
        asyncio.run_coroutine_threadsafe(message.reply(text), self._client.loop)

    @override
    def delete_message(self, message: dict):
        pass

    @override
    def _send_image(self, chat_id, file_name, binary_data, caption=""):
        pass

    @override
    def send_image_to_group(self, group_message: dict | Message, file_name, binary_data, caption = ""):
        # TODO: test
        self._send_image(group_message.chat.id, file_name, binary_data, caption)


    @override
    def send_image_to_individual(self, message: dict | Message, file_name, binary_data, caption = ""):
        # TODO: test
        user_id = message.from_user.id
        self._send_image(user_id, file_name, binary_data, caption)

    @override
    def send_audio_to_group(self, group_message: dict | Message, audio_file_path):
        pass

    @override
    def send_audio_to_individual(self, message: dict | Message, audio_file_path):
        pass
    
    @override
    def create_poll(self, message: dict | Message, question: str, options: list[str]):
        pass
    
    @override
    def vote_poll(self, message: dict | Message, option_index: int):
        pass
    
    @override
    def close_poll(self, message: dict | Message):
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
    def get_message_text(self, message: dict | Message) -> str:
        return message.text

    @override
    def get_chat_id(self, message: Message) -> str:
        return f"telethon://{message.chat.id}"

    @override
    def get_sender_name(self, message: Message) -> str:
        #return message.from_user.first_name if message.from_user else "Unknown"
        return "Unknown"

    @override
    def download_media(self, message):
        # TODO: implement
        #return (mime_type, decoded)
        return None

    @override
    def send_typing(self, message: dict, typing: bool):
        return


class TelethonMessageQueue:
    def __init__(self, messenger_instance: TelethonMessenger, callback):
        self._messenger = messenger_instance
        self._callback = callback
        self._messenger = messenger_instance
        self._thread = None

    def _run_client_loop(self):
        # Each thread must have its own loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        client = self._messenger.get_telebot()
        # Register handlers
        @client.on(events.NewMessage)
        async def handle_message(event):
            self._callback(self._messenger, event.message)
        # Start the client in this thread
        #loop.run_until_complete(client.start())
        loop.run_until_complete(client.run_until_disconnected())

    def run_async(self):
        self._thread = threading.Thread(target=self._run_client_loop, daemon=True)
        self._thread.start()