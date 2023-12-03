import logging
import threading
import time
import json
import websockets.sync.client as wsclient
import websockets.exceptions
from messenger import SignalMessenger
from main_pipeline import MainPipeline


class SignalMessageQueue():
    """Implementation to read messages from signal cli web serivce """
    WEBSOCKET_TIMEOUT = 600
    WEBSOCKET_MAXSIZE = 1024*1024*50

    def __init__(self, messenger_instance: SignalMessenger, mainpipe: MainPipeline) -> None:
        self._messenger = messenger_instance
        self._mainpipe = mainpipe
        self._thread = None

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
                print(message)
                print(f"is_group_message: {self._messenger.is_group_message(message)}")
                print(f"has_audio_data: {self._messenger.has_audio_data(message)}")
                print(f"get_message_text: {self._messenger.get_message_text(message)}")

                if "dataMessage" in message["envelope"]:
                    self._mainpipe.process(self._messenger, message)
            except (TimeoutError, websockets.exceptions.ConnectionClosed, \
                    ConnectionRefusedError, ConnectionError):
                logging.warning("Failed to connect to signal service, retrying")
                web_sock = None
                time.sleep(3)
    
    def run_async(self):
        self._thread = threading.Thread(target=self.get_messages)
        self._thread.start()
