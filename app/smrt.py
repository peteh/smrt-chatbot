"""Main application"""
import json
import logging
from flask import Flask, request, Response
import messenger
from decouple import config
from main_pipeline import MainPipeline
from signalcli import SignalMessageQueue
app = Flask(__name__)

whatsapp = messenger.Whatsapp(config("WPPCONNECT_SERVER"), "smrt", config('WPPCONNECT_APIKEY'))
signalMessenger = messenger.SignalMessenger(config("SIGNAL_NUMBER"), config("SIGNAL_HOST"), int(config("SIGNAL_PORT")))

mainpipe = MainPipeline()

@app.route('/incoming', methods=['POST'])
def return_response():
    """Handles new incoming messages from wpp-server"""
    message = request.json
    print(json.dumps(message, indent=4))

    if 'event' in message:
        if message['event'] == "onmessage":
            mainpipe.process(whatsapp, message)
            # delete message from phone after processing
            #whatsapp.deleteMessage(message)

    return Response(status=200)


queue = SignalMessageQueue(signalMessenger, mainpipe)

queue.run_async()
try:
    whatsapp.start_session()
except:
    logging.warn("Could not start Whatsapp session")
app.run(host="0.0.0.0", port=9000)
