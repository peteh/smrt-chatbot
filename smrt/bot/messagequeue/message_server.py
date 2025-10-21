import logging
from flask import Flask, request, jsonify
import smrt.bot.messenger as messenger

class MessageServerFlaskApp:
    """
    A flask application that serves as a message server for sending messages 
    via different messengers.
    """
    def __init__(self, messenger_manager: messenger.MessengerManager):
        self._app = Flask(__name__)
        self._messenger_manager = messenger_manager
        self._register_routes()
        self._app.logger.setLevel(logging.INFO)

    def _register_routes(self):
        @self._app.route('/send_message', methods=['POST'])
        def send_message():
            data = request.get_json()
            self._app.logger.debug(f"Received data: {data}")
            if not data or 'chatIds' not in data or 'message' not in data:
                self._app.logger.error("Missing required fields in request data, expected 'chatIds' and 'message'")
                self._app.logger.error(f"Message data: {data}")
                return jsonify({'error': 'Missing required fields: chatIds and message'}), 400

            chat_ids = data['chatIds']
            message = data['message']

            if not isinstance(chat_ids, list) or not isinstance(message, str):
                return jsonify({'error': 'Invalid types: chatids must be a list, message must be a string'}), 400

            logging.debug(f"Sending message '{message}' to chat IDs: {chat_ids}")
            error=""
            sent_to = []
            for chat_id in chat_ids:
                messenger_from_chat_id = self._messenger_manager.get_messenger_by_chatid(chat_id)
                if messenger_from_chat_id:
                    try:
                        messenger_from_chat_id.send_message(chat_id, message)
                        sent_to.append(chat_id)
                    except Exception as e:
                        error_message = f"Error sending message to {chat_id}: {str(e)}"
                        error += f"{error_message}\n"
                        self._app.logger.error(f"Failed to send message to {chat_id}: {e}")
                else:
                    error_message = f"No messenger found for chat ID: {chat_id}"
                    self._app.logger.warning(error_message)
                    error+= f"{error_message}\n"

            if len(error) > 0:
                return jsonify({'status': 'error', 'message': error, 'sent_to': sent_to}), 500
            return jsonify({'status': 'success', 'sent_to': sent_to}), 200
    
    def run(self, **kwargs):
        self._app.run(**kwargs)

