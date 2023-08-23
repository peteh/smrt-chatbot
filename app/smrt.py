"""Main application"""
import json
import logging
from flask import Flask, request, Response
import messenger
from decouple import config
from main_pipeline import MainPipeline
from signalcli import SignalMessageQueue
from whatsappsocketio import WhatsappMessageQueue
import time

whatsapp = messenger.Whatsapp(config("WPPCONNECT_SERVER"), "smrt", config('WPPCONNECT_APIKEY'))
signalMessenger = messenger.SignalMessenger(config("SIGNAL_NUMBER"), config("SIGNAL_HOST"), int(config("SIGNAL_PORT")))

mainpipe = MainPipeline()

queue = SignalMessageQueue(signalMessenger, mainpipe)
queue.run_async()
whatsapp_queue = WhatsappMessageQueue(whatsapp, mainpipe)
whatsapp_queue.run_async()
try:
    whatsapp.start_session()
    pass
except:
    logging.warn("Could not start Whatsapp session")
while(True):
    time.sleep(1)

# TODO: proper thread handling 