"""Messenger implementations for various messengers like Whatsapp. """
from abc import ABC, abstractmethod
from typing import Tuple
import base64
import requests

class MessengerInterface(ABC):
    """Interface for messengers to communicate with the underlying framework. """

    @abstractmethod
    def mark_in_progress_0(self, message: dict):
        """Marks a message that it is currently in processing. """

    @abstractmethod
    def mark_in_progress_50(self, message: dict):
        """Marks a message that it is currently 50% processed. """

    @abstractmethod
    def mark_in_progress_done(self, message: dict):
        """Marks a message that it's processing has been finished. """

    @abstractmethod
    def mark_in_progress_fail(self, message: dict):
        """Marks a message that the processing of said message failed. """

    @abstractmethod
    def is_group_message(self, message: dict):
        """Checks if a message is a group message"""

    @abstractmethod
    def send_message_to_group(self, group_message: dict, text: str):
        """Sends a message to the group of the original message. """

    @abstractmethod
    def send_message_to_individual(self, message: dict, text: str):
        """Sends a message to the sender the given message. """

    @abstractmethod
    def delete_message(self, message: dict):
        """Deletes a message from the server"""

    @abstractmethod
    def has_audio_data(self, message: dict):
        """Returns true if the message is an audio message. """

    @abstractmethod
    def is_bot_mentioned(self, message: dict):
        """Returns true if the bot is mentioned in the message. """

    @abstractmethod
    def get_message_text(self, message: dict) -> str:
        """Returns the text of the given message. """

    @abstractmethod
    def send_image_to_group(self, group_message: dict, file_name: str,
                            binary_data: bytes, caption: str = ""):
        """Sends an image to the group of the original message. """

    @abstractmethod
    def send_image_to_individual(self, message, file_name, binary_data, caption = ""):
        """Sends an image to the sender of the original message in a direct chat. """

    @abstractmethod
    def send_audio_to_group(self, group_message, binary_data):
        """Sends an audio message to the group of the original message. """

    @abstractmethod
    def send_audio_to_individual(self, message, binary_data):
        """Sends an audio message to the sender of the original message in a direct chat. """

    @abstractmethod
    def download_media(self, message: dict) -> Tuple[str, bytes]:
        """Downloads and returns the media from a given message in the 

        Args:
            message (dict): The original message to respond to

        Returns:
            Tuple[str, bytes]: mime type and binary data of the downloaded media
        """


class Whatsapp(MessengerInterface):
    """Messenger implemenation based on wpp-server whatsapp"""
    REACT_HOURGLASS_HALF = "\u231b"
    REACT_HOURGLASS_FULL = "\u23f3"
    REACT_CHECKMARK = "\u2714\ufe0f"
    REACT_FAIL = "\u274c"

    DEFAULT_TIMEOUT = 60

    def __init__(self, server: str, session: str, api_key: str):
        self._server = server
        self._session = session
        self._api_key = api_key
        self._headers = {"Authorization": f"Bearer {self._api_key}"}

    def _endpoint_url(self, endpoint, endpoint_param = None) -> str:
        if endpoint is not None:
            return f"{self._server}/api/{self._session}/{endpoint}/{endpoint_param}"
        return f"{self._server}/api/{self._session}/{endpoint}"

    def start_session(self):
        """Starts a session at wpp-connect server"""
        data = {
            #'web-hook': 'http://smrt:9000/incoming'
        }
        response = requests.post(self._endpoint_url("start-session"),
                                 json=data,
                                 headers=self._headers,
                                 timeout=self.DEFAULT_TIMEOUT)
        print(response.json())

    def _send_message(self, recipient: str, is_group, text: str):
        data = {
            "phone": recipient,
            "message": text,
            "isGroup": is_group
        }
        requests.post(self._endpoint_url("send-message"),
                      json=data,
                      headers=self._headers,
                      timeout=self.DEFAULT_TIMEOUT)

    def _react(self, message_id, reaction_text):
        data = {
            "msgId": message_id,
            "reaction": reaction_text
        }
        requests.post(self._endpoint_url("react-message"),
                      json=data,
                      headers=self._headers,
                      timeout=self.DEFAULT_TIMEOUT)

    def mark_in_progress_0(self, message: dict):
        self._react(message['id'], self.REACT_HOURGLASS_FULL)

    def mark_in_progress_50(self, message: dict):
        self._react(message['id'], self.REACT_HOURGLASS_HALF)

    def mark_in_progress_done(self, message: dict):
        self._react(message['id'], self.REACT_CHECKMARK)

    def mark_in_progress_fail(self, message: dict):
        self._react(message['id'], self.REACT_FAIL)

    def is_group_message(self, message: dict):
        return 'isGroupMsg' in message and message['isGroupMsg'] is True

    def send_message_to_group(self, group_message: dict, text: str):
        self._send_message(group_message['chatId'], True, text)

    def send_message_to_individual(self, message: dict, text: str):
        self._send_message(message['sender']['id'], False, text)

    def delete_message(self, message: dict):
        is_group = self.is_group_message(message)
        recpipient = message['chatId'] if is_group else message['sender']['id']
        data = {
            "phone": recpipient,
            "messageId": message['id'],
            "isGroup": is_group
        }
        response = requests.post(self._endpoint_url("delete-message"),
                                 json=data,
                                 headers=self._headers,
                                 timeout=self.DEFAULT_TIMEOUT)
        print(response.json())

    def _send_image(self, recipient: str, is_group: bool,
                    file_name: str, binary_data, caption: str):
        base64data = base64.b64encode(binary_data).decode('utf-8')
        if file_name.endswith('.webp'):
            data_type="image/webp"
        else:
            data_type="image/png"

        data = {
            "phone": recipient,
            "base64": f"data:{data_type};base64,{base64data}",
            "filename": file_name,
            "message": caption,
            "isGroup": is_group, 
        }
        requests.post(self._endpoint_url("send-image"),
                      json=data,
                      headers=self._headers,
                      timeout=self.DEFAULT_TIMEOUT)

    def send_image_to_group(self, group_message, file_name, binary_data, caption = ""):
        self._send_image(group_message['chatId'], True, file_name, binary_data, caption)

    def send_image_to_individual(self, message, file_name, binary_data, caption = ""):
        self._send_image(message['sender']['id'], False, file_name, binary_data, caption)

    def send_audio_to_group(self, group_message, binary_data):
        self._send_audio(group_message['chatId'], True, binary_data)

    def send_audio_to_individual(self, message, binary_data):
        self._send_audio(message['sender']['id'], False, binary_data)

    def _send_audio(self, recipient: str, is_group: bool, binary_data):
        base64data = base64.b64encode(binary_data).decode('utf-8')

        data = {
            "phone": recipient,
            "base64Ptt": f"data:audio/ogg;base64,{base64data}",
            "isGroup": is_group, 
        }
        requests.post(self._endpoint_url("send-voice-base64"),
                      json=data,
                      headers=self._headers,
                      timeout=self.DEFAULT_TIMEOUT)

    def has_audio_data(self, message: dict):
        return 'mimetype' in message and message['mimetype'] == "audio/ogg; codecs=opus"

    def is_bot_mentioned(self, message: dict):
        # TODO: extract this somehow
        return 'mentionedJidList' in message \
            and len(message['mentionedJidList']) == 1 \
            and message['mentionedJidList'] == '4917658696957@c.us'

    def get_message_text(self, message: dict):
        return message['content']


    def download_media(self, message):
        msg_id = message['id']
        response = requests.get(self._endpoint_url("get-media-by-message", msg_id),
                                headers=self._headers,
                                timeout=self.DEFAULT_TIMEOUT)

        json_response = response.json()
        data = json_response['base64']
        decoded = base64.b64decode(data)
        mime_type = json_response['mimetype']
        return (mime_type, decoded)
