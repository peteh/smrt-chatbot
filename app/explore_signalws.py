import logging
import threading
import time
import json
import websockets.sync.client as wsclient
import websockets.exceptions
from messenger import SignalMessenger, Whatsapp
from main_pipeline import MainPipeline
from decouple import config

class SignalMessageQueue():
    """Implementation to get interfaces from stabediffusionai.org. """
    WEBSOCKET_TIMEOUT = 600
    WEBSOCKET_MAXSIZE = 1024*1024*50

    def __init__(self, messenger_instance: Whatsapp, mainpipe: MainPipeline) -> None:
        self._messenger = messenger_instance
        self._mainpipe = mainpipe
        self._thread = None

    def get_messages(self):
        api_url = "ws://localhost:21465/"
        web_sock = None

        while True:
            try:
                if web_sock is None:
                    web_sock = wsclient.connect(api_url, max_size=self.WEBSOCKET_MAXSIZE)
                    logging.info("Connected to Signal Service")
                message = json.loads(web_sock.recv())
                print(message)
            except (TimeoutError, websockets.exceptions.ConnectionClosed, \
                    ConnectionRefusedError, ConnectionError):
                logging.warning("Failed to connect to signal service, retrying")
                web_sock = None
                time.sleep(3)
    
    def run_async(self):
        self._thread = threading.Thread(target=self.get_messages)
        self._thread.start()

whatsapp = Whatsapp(config("WPPCONNECT_SERVER"), "smrt", config('WPPCONNECT_APIKEY'))
mainpipe = MainPipeline()
queue = SignalMessageQueue(whatsapp, mainpipe)
queue.run_async()
time.sleep(5000)