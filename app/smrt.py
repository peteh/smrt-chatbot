"""Main application"""
import time
import logging
import messenger
from decouple import config
from main_pipeline import MainPipeline
from signalcli import SignalMessageQueue
from whatsappsocketio import WhatsappMessageQueue
from senate_stocks import SenateStockNotification
logging.basicConfig(level=logging.DEBUG)
root = logging.getLogger()
root.setLevel(logging.DEBUG)

#handler = logging.StreamHandler(sys.stdout)
#handler.setLevel(logging.DEBUG)
#formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#handler.setFormatter(formatter)
#root.addHandler(handler)

whatsapp = messenger.Whatsapp(config("WPPCONNECT_SERVER"), "smrt", config('WPPCONNECT_APIKEY'))
signalMessenger = messenger.SignalMessenger(config("SIGNAL_NUMBER"), config("SIGNAL_HOST"), int(config("SIGNAL_PORT")))

mainpipe = MainPipeline()

signal_queue = SignalMessageQueue(signalMessenger, mainpipe)
whatsapp_queue = WhatsappMessageQueue(whatsapp, mainpipe)

stock_notifier = SenateStockNotification(whatsapp)


signal_queue.run_async()
whatsapp_queue.run_async()
stock_notifier.run_async()
try:
    whatsapp.start_session()
except:
    logging.warn("Could not start Whatsapp session")


while(True):
    time.sleep(1)

# TODO: proper thread handling 