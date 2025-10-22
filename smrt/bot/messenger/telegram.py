
import telebot
import tempfile
from typing import override
from .messenger import MessengerInterface


class TelegramMessenger(MessengerInterface):
    """Messenger implemention based on telebot api"""


    def __init__(self, api_key: str):
        self._telebot = telebot.TeleBot(api_key)

    def get_telebot(self) -> telebot.TeleBot:
        return self._telebot

    @override
    def get_name(self) -> str:
        return "telegram"

    @override
    def mark_in_progress_0(self, message: dict):
        # Message reactions are not supported by Telegram API
        pass

    @override
    def mark_in_progress_50(self, message: dict):
        # Message reactions are not supported by Telegram API
        pass

    @override
    def mark_in_progress_done(self, message: dict):
        # Message reactions are not supported by Telegram API
        pass

    @override
    def mark_in_progress_fail(self, message: dict):
        # Message reactions are not supported by Telegram API
        pass

    @override
    def mark_seen(self, message: dict) -> None:
        # Telegram API does not support marking messages as seen
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
        if chat_id.startswith("telegram://"):
            chat_id = chat_id.split("telegram://")[1]
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
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
            temp_file.write(binary_data)
            temp_file.flush()  # Ensure the file is written before sending
            photo = open(temp_file.name, 'rb')
            self._telebot.send_photo(chat_id=chat_id, photo=photo, caption=caption, parse_mode='Markdown')
            photo.close()

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
    def get_chat_id(self, message: telebot.types.Message) -> str:
        return f"telegram://{message.chat.id}"

    @override
    def get_sender_name(self, message: telebot.types.Message) -> str:
        return message.from_user.first_name if message.from_user else "Unknown"

    @override
    def download_media(self, message):
        # TODO: implement
        #return (mime_type, decoded)
        return None
    
