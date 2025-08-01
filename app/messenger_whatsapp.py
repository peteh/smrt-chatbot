import logging
import tempfile
import subprocess
import os
import threading
import time
import base64

import requests
import socketio

from messenger import MessengerInterface
from main_pipeline import MainPipeline

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
        logging.debug(response.json())
    
    def send_message(self, chat_id: str, text: str):
        # The chat_id is in the format "whatsapp://<phone-number>@c.us"
        # We need to extract the phone number part
        if chat_id.startswith("whatsapp://"):
            recipient = chat_id.split("whatsapp://")[1]
        else:
            recipient = chat_id
        is_group = chat_id.endswith("@g.us")
        self._send_message(recipient, is_group, text)

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

    def mark_seen(self, message: dict) -> None:
        is_group_message = self.is_group_message(message)
        recipient = message['chatId'] if is_group_message else message['sender']['id']
        data = {
            "phone": recipient,
            "isGroup": is_group_message
        }
        requests.post(self._endpoint_url("mark-seen"),
                      json=data,
                      headers=self._headers,
                      timeout=self.DEFAULT_TIMEOUT)

    def is_group_message(self, message: dict):
        return 'isGroupMsg' in message and message['isGroupMsg'] is True

    def is_self_message(self, message: dict):
        return "fromMe" in message and message["fromMe"]

    def send_message_to_group(self, group_message: dict, text: str):
        self._send_message(group_message['chatId'], True, text)

    def send_message_to_individual(self, message: dict, text: str):
        self._send_message(message['sender']['id'], False, text)
    
    def get_name(self) -> str:
        return "whatsapp"

    def reply_message(self, message: dict, text: str) -> None:
        is_group_message = self.is_group_message(message)
        recipient = message['chatId'] if is_group_message else message['sender']['id']
        data = {
            "phone": recipient,
            "message": text,
            "isGroup": is_group_message, 
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
        logging.debug(response.json())

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
        return f"whatsapp://{message['chatId']}"

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



class WhatsappMessageQueue():

    def __init__(self, messenger_instance: Whatsapp, mainpipe: MainPipeline) -> None:
        self._messenger = messenger_instance
        self._mainpipe = mainpipe
        self._thread = None
        self._sio = socketio.Client()

        # Register event handlers
        self._sio.on('connect', self.on_connect)
        self._sio.on('disconnect', self.on_disconnect)
        self._sio.on('received-message', self.on_new_message)
        self._sio.on('message', self.on_message)
        self._sio.on('*', self.on_catch_all)
    
    def run_async(self):
        self._thread = threading.Thread(target=self.run)
        self._thread.start()

    def on_connect(self):
        logging.info("Connected to WPPConnect server")

    def on_disconnect(self):
        logging.info("Disconnected from WPPConnect server")

    def on_message(self, data):
        logging.info(f"Received message: {data}")
        
    
    def on_new_message(self, data):
        logging.info(f"Received new message: {data}")
        self._mainpipe.process(self._messenger, data['response'])

    def on_catch_all(self, identifier, data):
        #print("Received catch all identifier:", identifier)
        #print("Received catch all event:", data)
        pass

    def run(self):
        try:
            self._sio.connect(self._messenger.get_server())

            while True:
                time.sleep(3)
            # TODO: reconnect handling

            self._sio.disconnect()
        except Exception as e:
            logging.error(f"Error in WhatsappMessageQueue: {e}")
            self._sio.disconnect()
            #raise e