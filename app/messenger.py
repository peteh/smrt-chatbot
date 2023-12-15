"""Messenger implementations for various messengers like Whatsapp. """
from abc import ABC, abstractmethod
from typing import Tuple
import logging
import base64
import tempfile
import os
import subprocess
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
    def is_group_message(self, message: dict) -> bool:
        """Checks if a message is a group message"""
    
    @abstractmethod
    def is_self_message(self, message: dict) -> bool:
        """checks if the message is a message from the bot itself"""

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
    
    def get_server(self) -> str:
        return self._server

    def _endpoint_url(self, endpoint, endpoint_param = None) -> str:
        if endpoint_param is not None:
            return f"{self._server}/api/{self._session}/{endpoint}/{endpoint_param}"
        return f"{self._server}/api/{self._session}/{endpoint}"

    def start_session(self):
        """Starts a session at wpp-connect server"""
        data = {
            #'web-hook': 'http://10.10.0.1:9000/incoming'
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
    
    def is_self_message(self, message: dict):
        return "fromMe" in message and message["fromMe"]

    def send_message_to_group(self, group_message: dict, text: str):
        self._send_message(group_message['chatId'], True, text)

    def send_message_to_individual(self, message: dict, text: str):
        self._send_message(message['sender']['id'], False, text)
    
    def reply_message(self, message: dict, text: str) -> None:
        data = {
            "phone": message['sender']['id'],
            "message": text,
            "isGroup": self.is_group_message(message), 
            "messageId": message.get("id")
        }
        requests.post(self._endpoint_url("send-reply"),
                      json=data,
                      headers=self._headers,
                      timeout=self.DEFAULT_TIMEOUT)

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

    def send_audio_to_group(self, group_message, audio_file_path):
        self._send_audio(group_message['chatId'], True, audio_file_path)

    def send_audio_to_individual(self, message, audio_file_path):
        self._send_audio(message['sender']['id'], False, audio_file_path)

    def _send_audio(self, recipient: str, is_group: bool, audio_file_path: str):
        with tempfile.TemporaryDirectory() as tmp:
            output_file = os.path.join(tmp, 'output.opus')
            subprocess.run(["opusenc", audio_file_path, output_file], check=True)
            file = open(output_file,mode='rb')
            binary_data = file.read()
            file.close()
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
    
    def has_image_data(self, message: dict):
        #logging.info(f"Testing for image, mime-type: {message.get('mimetype')}")
        #return 'mimetype' in message and \
        #    (message['mimetype'] == "image/png" \
        #        or message['mimetype'] == "image/jpeg" \
        #        or message['mimetype'] == "image/jpg")
        return message.get("type") == "image"

    def is_bot_mentioned(self, message: dict):
        # TODO: extract this somehow
        return 'mentionedJidList' in message \
            and len(message['mentionedJidList']) == 1 \
            and message['mentionedJidList'] == '4917658696957@c.us'

    def get_message_text(self, message: dict):
        # if the message is of type image, then the text you sent is in the caption field
        if message.get("type") == "image":
            return message.get("caption", "")
        # otherwise we can get the text from the content field
        return message.get("content", "")

    def get_chat_id(self, message: dict) -> str:
        return message['chatId']

    def get_sender_name(self, message: dict):
        return message['sender']['pushname']

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


class SignalMessenger(MessengerInterface):
    """Interface for messengers to communicate with the underlying framework. """
    DEFAULT_TIMEOUT = 60
    REACT_HOURGLASS_HALF = "\u231b"
    REACT_HOURGLASS_FULL = "\u23f3"
    REACT_CHECKMARK = "\u2714\ufe0f"
    REACT_FAIL = "\u274c"

    def __init__(self, number: str, host:str, port: int) -> None:
        super().__init__()
        self._number = number
        self._host = host
        self._port = port
        self._group_cache = {}

    def get_host(self) -> str:
        return self._host

    def get_port(self) -> int:
        return self._port
    
    def get_number(self) -> str:
        return self._number

    def _endpoint_url(self, endpoint, endpoint_param = None) -> str:
        if endpoint_param is not None:
            return f"http://{self._host}:{self._port}/{endpoint}/{endpoint_param}"
        return f"http://{self._host}:{self._port}/{endpoint}"

    def _react(self, message: dict, reaction_text):
        if self.is_group_message(message):
            internal_id = message["envelope"]["dataMessage"]["groupInfo"]["groupId"]
            if internal_id not in self._group_cache:
                self._update_group_cache()
            recipient = self._group_cache[internal_id]
        else:
            recipient = message["envelope"]["sourceNumber"]
        data = {
            "reaction": reaction_text,
            # TODO: probably have to figure out group messages
            "recipient": recipient,
            "target_author": message["envelope"]["sourceNumber"],
            "timestamp": message["envelope"]["timestamp"]
        }

        requests.post(self._endpoint_url("v1/reactions", self._number),
                      json=data,
                      timeout=self.DEFAULT_TIMEOUT)

    def mark_in_progress_0(self, message: dict):
        self._react(message, self.REACT_HOURGLASS_FULL)

    def mark_in_progress_50(self, message: dict):
        self._react(message, self.REACT_HOURGLASS_HALF)

    def mark_in_progress_done(self, message: dict):
        self._react(message, self.REACT_CHECKMARK)

    def mark_in_progress_fail(self, message: dict):
        self._react(message, self.REACT_FAIL)

    def is_group_message(self, message: dict):
        return ("dataMessage" in message["envelope"] \
            and "groupInfo" in message["envelope"]["dataMessage"])
    
    def is_self_message(self, message: dict):
        # TODO: we currently don't get messages we send ourselves, but we could double check
        return False

    def _update_group_cache(self):
        response = requests.get(self._endpoint_url("v1/groups", self._number),
                                timeout=self.DEFAULT_TIMEOUT)
        groups = response.json()
        for group in groups:
            self._group_cache[group["internal_id"]] = group["id"]

    def send_message_to_group(self, group_message: dict, text: str):
        internal_id = group_message["envelope"]["dataMessage"]["groupInfo"]["groupId"]
        if internal_id not in self._group_cache:
            self._update_group_cache()
        data = {
            "message": text,
            "number": self._number,
            "recipients": [
                self._group_cache[internal_id]
            ]
        }
        requests.post(self._endpoint_url("v2/send"),
                      json=data,
                      timeout=self.DEFAULT_TIMEOUT)

    def send_message_to_individual(self, message: dict, text: str):
        data = {
            "message": text,
            "number": self._number,
            "recipients": [
                message["envelope"]["sourceNumber"]
            ]
        }
        requests.post(self._endpoint_url("v2/send"),
                      json=data,
                      timeout=self.DEFAULT_TIMEOUT)
    
    def reply_message(self, message: dict, text: str) -> None:
        pass

    def delete_message(self, message: dict):
        pass

    def has_audio_data(self, message: dict):
        if "dataMessage" in message["envelope"] \
            and "attachments" in message["envelope"]["dataMessage"]:
            for attachment in message["envelope"]["dataMessage"]["attachments"]:
                if attachment["contentType"] == "audio/aac":
                    return True
        return False
    
    def has_image_data(self, message: dict):
        if "dataMessage" in message["envelope"] \
            and "attachments" in message["envelope"]["dataMessage"]:
            for attachment in message["envelope"]["dataMessage"]["attachments"]:
                if attachment["contentType"] == "image/png" \
                    or attachment["contentType"] == "image/jpeg" \
                    or attachment["contentType"] == "image/jpg":
                    return True
        return False

    def is_bot_mentioned(self, message: dict):
        # TODO
        return False

    def get_message_text(self, message: dict) -> str:
        if "dataMessage" in message["envelope"] \
            and "message" in message["envelope"]["dataMessage"] \
            and message["envelope"]["dataMessage"]["message"] is not None:
            return message["envelope"]["dataMessage"]["message"]
        return ""

    def get_chat_id(self, message: dict) -> str:
        if self.is_group_message(message):
            return message["envelope"]["dataMessage"]["groupInfo"]["groupId"]
        return message["envelope"]["sourceNumber"]

    def get_sender_name(self, message: dict):
        return message["envelope"]["sourceName"]

    def send_image_to_group(self, group_message: dict, file_name: str,
                            binary_data: bytes, caption: str = ""):
        internal_id = group_message["envelope"]["dataMessage"]["groupInfo"]["groupId"]
        if internal_id not in self._group_cache:
            self._update_group_cache()
        base64data = base64.b64encode(binary_data).decode('utf-8')
        if file_name.endswith('.webp'):
            data_type="image/webp"
        else:
            data_type="image/png"

        data = {
            "base64_attachments": [
                f"data:{data_type};base64,{base64data}"
            ],
            "number": self._number,
            "recipients": [
                self._group_cache[internal_id]
            ]
        }
        requests.post(self._endpoint_url("v2/send"),
                      json=data,
                      timeout=self.DEFAULT_TIMEOUT)

    def send_image_to_individual(self, message, file_name, binary_data, caption = ""):
        base64data = base64.b64encode(binary_data).decode('utf-8')
        if file_name.endswith('.webp'):
            data_type="image/webp"
        else:
            data_type="image/png"

        data = {
            "base64_attachments": [
                f"data:{data_type};base64,{base64data}"
            ],
            "number": self._number,
            "recipients": [
                message["envelope"]["sourceNumber"]
            ]
        }
        requests.post(self._endpoint_url("v2/send"),
                      json=data,
                      timeout=self.DEFAULT_TIMEOUT)
    
    def _send_audio(self, recipient, audio_file_path):
        with tempfile.TemporaryDirectory() as tmp:
            #output_file = os.path.join(tmp, 'output.ogg')
            #subprocess.run(["oggenc", "-o", output_file, audio_file_path], check=True)
            output_file = os.path.join(tmp, 'output.m4a')
            subprocess.run(["ffmpeg", "-i", audio_file_path, "-c:a", "aac", output_file, ], check=True)
            file = open(output_file,mode='rb')
            binary_data = file.read()
            file.close()
        base64data = base64.b64encode(binary_data).decode('utf-8')
        data = {
            "base64_attachments": [
                #f"data:audio/ogg;base64,{base64data}"
                f"data:audio/aac;base64,{base64data}"
            ],
            "number": self._number,
            "recipients": [
                recipient
            ]
        }
        requests.post(self._endpoint_url("v2/send"),
                      json=data,
                      timeout=self.DEFAULT_TIMEOUT)

    def send_audio_to_group(self, group_message, audio_file_path):
        internal_id = group_message["envelope"]["dataMessage"]["groupInfo"]["groupId"]
        if internal_id not in self._group_cache:
            self._update_group_cache()
        self._send_audio(self._group_cache[internal_id], audio_file_path)

    def send_audio_to_individual(self, message, audio_file_path):
        self._send_audio(message["envelope"]["sourceNumber"], audio_file_path)
        


    def download_media(self, message: dict) -> Tuple[str, bytes]:
        # TODO: looks like signal could return a list of attachments, thus we should have a list here too
        # we will just get the first one here
        if "dataMessage" in message["envelope"] and "attachments" in message["envelope"]["dataMessage"]:
            attachment = message["envelope"]["dataMessage"]["attachments"][0]
            content_type = attachment["contentType"]
            attachment_id = attachment["id"]
            response = requests.get(self._endpoint_url("v1/attachments", attachment_id),
                            timeout=self.DEFAULT_TIMEOUT)
            return (content_type, response.content)
        return None