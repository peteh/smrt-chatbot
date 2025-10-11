"""Messenger implementations for various messengers like Whatsapp. """
from abc import ABC, abstractmethod
from typing import Tuple

class MessengerInterface(ABC):
    """Interface for messengers to communicate with the underlying framework. """
    
    @abstractmethod
    def get_name(self) -> str:
        """Returns the name of the messenger, e.g. 'whatsapp' or 'telegram'. 

        Returns:
            str: The name of the messenger
        """

    @abstractmethod
    def mark_in_progress_0(self, message: dict) -> None:
        """Marks a message that it is currently in processing. """

    @abstractmethod
    def mark_in_progress_50(self, message: dict) -> None:
        """Marks a message that it is currently 50% processed. """

    @abstractmethod
    def mark_in_progress_done(self, message: dict) -> None:
        """Marks a message that it's processing has been finished. """
    
    def mark_skipped(self, message: dict) -> None:
        """Marks a message skipped from processing"""

    @abstractmethod
    def mark_in_progress_fail(self, message: dict) -> None:
        """Marks a message that the processing of said message failed. """

    @abstractmethod
    def mark_seen(self, message: dict) -> None:
        """Marks a message/chat from the message as seen. 

        Args:
            message (dict): The message to mark the chat as seen. 
        """

    @abstractmethod
    def is_group_message(self, message: dict) -> bool:
        """Checks if a message is a group message"""

    @abstractmethod
    def is_self_message(self, message: dict) -> bool:
        """checks if the message is a message from the bot itself"""

    @abstractmethod
    def send_message(self, chat_id: str, text: str):
        """Sends a message to the given chat id.

        Args:
            chat_id (str): The unique identifier of the chat
            text (str): The message text to send
        """

    @abstractmethod
    def send_message_to_group(self, group_message: dict, text: str):
        """Sends a message to the group of the original message. """

    @abstractmethod
    def send_message_to_individual(self, message: dict, text: str):
        """Sends a message to the sender the given message. """

    @abstractmethod
    def reply_message(self, message: dict, text: str) -> None:
        """Responds to the given message. 

        Args:
            message (dict): The message to reply to
            text (str): The reply message text
        """

    @abstractmethod
    def delete_message(self, message: dict):
        """Deletes a message from the server"""

    @abstractmethod
    def has_audio_data(self, message: dict) -> bool:
        """Returns true if the message is an audio message. """

    @abstractmethod
    def has_image_data(self, message: dict) -> bool:
        """Returns true if the message contains an image. """

    @abstractmethod
    def is_bot_mentioned(self, message: dict) -> bool:
        """Returns true if the bot is mentioned in the message. """

    @abstractmethod
    def get_message_text(self, message: dict) -> str:
        """Returns the text of the given message. """

    @abstractmethod
    def get_chat_id(self, message: dict) -> str:
        """Returns a unique identifier to identify the chat, e.g. a group id or sender id

        Args:
            message (dict): The received message

        Returns:
            str: The unique identifier of the chat
        """

    @abstractmethod
    def get_sender_name(self, message: dict) -> str:
        """Returns the name of the sender of the message

        Args:
            message (dict): the received message

        Returns:
            str: The name of the sender
        """

    @abstractmethod
    def send_image_to_group(self, group_message: dict, file_name: str,
                            binary_data: bytes, caption: str = ""):
        """Sends an image to the group of the original message. """

    @abstractmethod
    def send_image_to_individual(self, message, file_name, binary_data, caption = ""):
        """Sends an image to the sender of the original message in a direct chat. """

    @abstractmethod
    def send_audio_to_group(self, group_message: dict, audio_file_path: str):
        """Sends an audio message to the group of the original message. """

    @abstractmethod
    def send_audio_to_individual(self, message: dict, audio_file_path: str):
        """Sends an audio message to the sender of the original message in a direct chat. """

    @abstractmethod
    def download_media(self, message: dict) -> Tuple[str, bytes]:
        """Downloads and returns the media from a given message in the 

        Args:
            message (dict): The original message to respond to

        Returns:
            Tuple[str, bytes]: mime type and binary data of the downloaded media
        """

class MessengerManager():
    def __init__(self):

        self._messengers = {}

    def add_messenger(self, messenger: MessengerInterface):
        self._messengers[messenger.get_name()] = messenger
    
    def get_messenger_by_chatid(self, chat_id: str) -> MessengerInterface | None:
        identifier = chat_id.split("://")[0]  # Extract the identifier from the chat_id
        
        if identifier in self._messengers:
            return self._messengers[identifier]
        return None