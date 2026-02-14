import logging
import threading
import time
import json
import base64
import subprocess
import tempfile
import os
import requests
import websockets.sync.client as wsclient
import websockets.exceptions
from typing import Tuple, override, Callable

from .messenger import MessengerInterface

class SignalMessenger(MessengerInterface):
    """Interface for messengers to communicate with the underlying framework. """
    DEFAULT_TIMEOUT = 60
    REACT_HOURGLASS_HALF = "\u231b"
    REACT_HOURGLASS_FULL = "\u23f3"
    REACT_CHECKMARK = "\u2714\ufe0f"
    REACT_SKIP = "\U0001F4A4"
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

    @override
    def get_name(self) -> str:
        return "signal"

    def _get_group_id_from_message(self, message: dict):
        internal_id = message["envelope"]["dataMessage"]["groupInfo"]["groupId"]
        if internal_id not in self._group_cache:
            self._update_group_cache()
        return self._group_cache[internal_id]

    def _react(self, message: dict, reaction_text):
        if self.is_group_message(message):
            recipient = self._get_group_id_from_message(message)
        else:
            recipient = message["envelope"]["sourceNumber"]
        data = {
            "reaction": reaction_text,
            "recipient": recipient,
            "target_author": message["envelope"]["sourceNumber"],
            "timestamp": message["envelope"]["timestamp"]
        }

        requests.post(self._endpoint_url("v1/reactions", self._number),
                      json=data,
                      timeout=self.DEFAULT_TIMEOUT)
    @override
    def mark_in_progress_0(self, message: dict):
        self._react(message, self.REACT_HOURGLASS_FULL)
        self.send_typing(message, True)

    @override
    def mark_in_progress_50(self, message: dict):
        self._react(message, self.REACT_HOURGLASS_HALF)
        self.send_typing(message, True)

    @override
    def mark_in_progress_done(self, message: dict):
        self._react(message, self.REACT_CHECKMARK)
        self.send_typing(message, False)

    @override
    def mark_skipped(self, message):
        self._react(message, self.REACT_SKIP)
        self.send_typing(message, False)

    @override
    def mark_in_progress_fail(self, message: dict):
        self._react(message, self.REACT_FAIL)
        self.send_typing(message, False)

    @override
    def mark_seen(self, message: dict) -> None:
        # read receipts are always based on individual message sender, even in groups
        recipient = message["envelope"]["sourceNumber"]
        data = {
            "receipt_type": "read",
            "recipient": recipient,
            "timestamp": message["envelope"]["timestamp"]
        }
        endpoint = "v1/receipts"
        response = requests.post(self._endpoint_url(endpoint, self._number),
                      json=data,
                      timeout=self.DEFAULT_TIMEOUT)
        if response.status_code != 204:
            logging.warning(f"Failed to send receipt: {response.text} on {endpoint}, code: {response.status_code}")

    @override
    def mark_unseen(self, message: dict) -> None:
        # Signal API does not support marking messages as unseen, so we will just not send a read receipt
        return

    @override
    def is_group_message(self, message: dict):
        return ("dataMessage" in message["envelope"] \
            and "groupInfo" in message["envelope"]["dataMessage"])

    @override
    def is_self_message(self, message: dict):
        # TODO: we currently don't get messages we send ourselves, but we could double check
        return False

    def _update_group_cache(self):
        response = requests.get(self._endpoint_url("v1/groups", self._number),
                                timeout=self.DEFAULT_TIMEOUT)
        groups = response.json()
        for group in groups:
            self._group_cache[group["internal_id"]] = group["id"]

    @override
    def send_message(self, chat_id: str, text: str):
        # The chat_id is in the format "signal://<group-id>" or "signal://<phone-number>"
        # We need to extract the group id or phone number part
        if chat_id.startswith("signal://"):
            recipient = chat_id.split("signal://")[1]
        else:
            recipient = chat_id

        if not recipient.startswith("+"):
            # do group cache handling
            if recipient not in self._group_cache:
                self._update_group_cache()
            recipient = self._group_cache.get(recipient, recipient)

        data = {
            "message": text,
            "text_mode": "styled",
            "number": self._number,
            "recipients": [
                recipient
            ]
        }
        #TODO: handle error codes
        requests.post(self._endpoint_url("v2/send"),
                      json=data,
                      timeout=self.DEFAULT_TIMEOUT)

    @override
    def send_message_to_group(self, group_message: dict, text: str):
        data = {
            "message": text,
            "text_mode": "styled",
            "number": self._number,
            "recipients": [
                self._get_group_id_from_message(group_message)
            ]
        }
        requests.post(self._endpoint_url("v2/send"),
                      json=data,
                      timeout=self.DEFAULT_TIMEOUT)

    @override
    def send_message_to_individual(self, message: dict, text: str):
        data = {
            "message": text,
            "text_mode": "styled",
            "number": self._number,
            "recipients": [
                message["envelope"]["sourceNumber"]
            ]
        }
        requests.post(self._endpoint_url("v2/send"),
                      json=data,
                      timeout=self.DEFAULT_TIMEOUT)

    @override
    def reply_message(self, message: dict, text: str) -> None:
        if self.is_group_message(message):
            recipient = self._get_group_id_from_message(message)
        else:
            recipient = message["envelope"]["sourceNumber"]

        data = {
            "message": text,
            "text_mode": "styled",
            "number": self._number,
            "quote_author": message["envelope"]["sourceNumber"],
            "quote_timestamp": message["envelope"]["timestamp"],
            "recipients": [
                recipient
            ]
        }
        requests.post(self._endpoint_url("v2/send"),
                    json=data,
                    timeout=self.DEFAULT_TIMEOUT)

    @override
    def delete_message(self, message: dict):
        pass

    @override
    def create_poll(self, message: dict, question: str, options: list[str]):
        pass

    def vote_poll(self, message: dict, option_index: int):
        pass

    def close_poll(self, message: dict):
        pass

    @override
    def has_audio_data(self, message: dict):
        if "dataMessage" in message["envelope"] \
            and "attachments" in message["envelope"]["dataMessage"]:
            for attachment in message["envelope"]["dataMessage"]["attachments"]:
                if attachment["contentType"] in ["audio/aac", "audio/ogg; codecs=opus"]:
                    return True
        return False

    @override
    def has_image_data(self, message: dict):
        if "dataMessage" in message["envelope"] \
            and "attachments" in message["envelope"]["dataMessage"]:
            for attachment in message["envelope"]["dataMessage"]["attachments"]:
                if attachment["contentType"] in ["image/png", "image/jpeg", "image/jpg"]:
                    return True
        return False

    @override
    def is_bot_mentioned(self, message: dict):
        if "dataMessage" in message["envelope"] \
            and "mentions" in message["envelope"]["dataMessage"]:
            for mention in message["envelope"]["dataMessage"]["mentions"]:
                logging.debug(f"Checking mention number: {mention.get('number')} against bot number: {self._number}")
                if mention.get("number") == self._number:
                    logging.debug("Bot mentioned in message.")
                    return True
        return False

    @override
    def get_message_text(self, message: dict) -> str:
        if "dataMessage" in message["envelope"] \
            and "message" in message["envelope"]["dataMessage"] \
            and message["envelope"]["dataMessage"]["message"] is not None:
            return message["envelope"]["dataMessage"]["message"]
        return ""

    @override
    def get_chat_id(self, message: dict) -> str:
        if self.is_group_message(message):
            chatid = message["envelope"]["dataMessage"]["groupInfo"]["groupId"]
        else:
            chatid = message["envelope"]["sourceNumber"]
        return f"signal://{chatid}"

    @override
    def get_sender_name(self, message: dict):
        return message["envelope"]["sourceName"]

    @override
    def send_image_to_group(self, group_message: dict, file_name: str,
                            binary_data: bytes, caption: str = ""):
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
                self._get_group_id_from_message(group_message)
            ]
        }
        requests.post(self._endpoint_url("v2/send"),
                      json=data,
                      timeout=self.DEFAULT_TIMEOUT)

    @override
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

    @override
    def send_audio_to_group(self, group_message, audio_file_path):
        self._send_audio(self._get_group_id_from_message(group_message), audio_file_path)

    @override
    def send_audio_to_individual(self, message, audio_file_path):
        self._send_audio(message["envelope"]["sourceNumber"], audio_file_path)

    @override
    def download_media(self, message: dict) -> Tuple[str, bytes]:
        # TODO: looks like signal could return a list of attachments,
        # thus we should have a list here too
        # we will just get the first one here for now though
        if "dataMessage" in message["envelope"] \
            and "attachments" in message["envelope"]["dataMessage"]:
            attachment = message["envelope"]["dataMessage"]["attachments"][0]
            content_type = attachment["contentType"]
            attachment_id = attachment["id"]
            response = requests.get(self._endpoint_url("v1/attachments", attachment_id),
                            timeout=self.DEFAULT_TIMEOUT)
            return (content_type, response.content)
        return None

    @override
    def send_typing(self, message: dict, typing: bool):
        if self.is_group_message(message):
            recipient = self._get_group_id_from_message(message)
        else:
            recipient = message["envelope"]["sourceNumber"]

        data = {
            "recipient": recipient
        }
        endpoint = self._endpoint_url("v1/typing-indicator", self._number)
        if typing:
            response = requests.put(endpoint,
                        json=data,
                        timeout=self.DEFAULT_TIMEOUT)
            if response.status_code != 200:
                logging.warning(f"Failed to send typing indicator: {response.text} on {endpoint}")
        else:
            response = requests.delete(endpoint,
                        json=data,
                        timeout=self.DEFAULT_TIMEOUT)
            if response.status_code != 200:
                logging.warning(f"Failed to send typing indicator: {response.text} on {endpoint}")


class SignalMessageQueue():
    """Implementation to read messages from signal cli web service """
    WEBSOCKET_TIMEOUT = 600
    WEBSOCKET_MAXSIZE = 1024*1024*50

    def __init__(self, messenger_instance: SignalMessenger, callback: Callable[[MessengerInterface, dict], None]) -> None:
        self._messenger = messenger_instance
        self._thread = None
        self._callback = callback

    def get_messages(self):
        api_url = f"ws://{self._messenger.get_host()}:{self._messenger.get_port()}/v1/receive/{self._messenger.get_number()}"
        web_sock = None

        while True:
            try:
                if web_sock is None:
                    web_sock = wsclient.connect(api_url, max_size=self.WEBSOCKET_MAXSIZE)
                    logging.info("Connected to Signal Service")
                message = json.loads(web_sock.recv())
                # TODO: fix logs
                logging.debug(message)
                logging.debug(f"is_group_message: {self._messenger.is_group_message(message)}")
                logging.debug(f"has_audio_data: {self._messenger.has_audio_data(message)}")
                logging.debug(f"get_message_text: {self._messenger.get_message_text(message)}")

                if "dataMessage" in message["envelope"]:
                    self._callback(self._messenger, message)
            except (TimeoutError, websockets.exceptions.ConnectionClosed, \
                    ConnectionRefusedError, ConnectionError):
                logging.warning("Failed to connect to signal service, retrying")
                web_sock = None
                time.sleep(3)

    def run_async(self):
        self._thread = threading.Thread(target=self.get_messages)
        self._thread.start()
