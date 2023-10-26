import logging
import threading
import time
from messenger import Whatsapp
from main_pipeline import MainPipeline

import socketio

class WhatsappMessageQueue():

    def __init__(self, messenger_instance: Whatsapp, mainpipe: MainPipeline) -> None:
        self._messenger = messenger_instance
        self._mainpipe = mainpipe
        self._thread = None
        self.sio = socketio.Client()

        # Register event handlers
        self.sio.on('connect', self.on_connect)
        self.sio.on('disconnect', self.on_disconnect)
        self.sio.on('received-message', self.on_new_message)
        self.sio.on('message', self.on_message)
        self.sio.on('*', self.on_catch_all)
    
    def run_async(self):
        self._thread = threading.Thread(target=self.run)
        self._thread.start()

    def on_connect(self):
        logging.info("Connected to server")

    def on_disconnect(self):
        logging.info("Disconnected from server")

    def on_message(self, data):
        logging.info("Received message:", data)
        
    
    def on_new_message(self, data):
        logging.info("Received new message:", data)
        self._mainpipe.process(self._messenger, data['response'])

    def on_catch_all(self, identifier, data):
        #print("Received catch all identifier:", identifier)
        #print("Received catch all event:", data)
        pass

    def run(self):
        self.sio.connect(self._messenger.get_server())

        while True:
            time.sleep(1)
        # TODO: reconnect handling

        self.sio.disconnect()