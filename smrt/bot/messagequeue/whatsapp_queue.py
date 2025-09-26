import threading
import time
import socketio
from smrt.bot.pipeline import MainPipeline
from smrt.bot.messenger.whatsapp import WhatsappMessenger
import logging


class WhatsappMessageQueue():

    def __init__(self, messenger_instance: WhatsappMessenger, mainpipe: MainPipeline) -> None:
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