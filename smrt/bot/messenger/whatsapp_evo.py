import logging
import tempfile
import subprocess
import os
import base64
import requests
import threading
import time
import json
from typing import Callable, override

import socketio
from .messenger import MessengerInterface


class WhatsappEvoMessenger(MessengerInterface):
    """Messenger implementation based on evolution-api (https://github.com/evolution-foundation/evolution-api)"""
    REACT_HOURGLASS_HALF = "\u231b"
    REACT_HOURGLASS_FULL = "\u23f3"
    REACT_CHECKMARK = "\u2714\ufe0f"
    REACT_SKIP = "\U0001F4A4"
    REACT_FAIL = "\u274c"

    DEFAULT_TIMEOUT = 60

    def __init__(self, server: str, instance_name: str, api_key: str) -> None:
        """
        Initialize WhatsApp Evolution messenger.
        
        Args:
            server: Base URL of evolution-api server (e.g., http://localhost:8080)
            instance_name: Name of the WhatsApp instance
            api_key: API key for authentication
        """
        self._server = server
        self._instance_name = instance_name
        self._api_key = api_key
        self._phone_number = ""
        self._headers = {"apikey": self._api_key}

    def get_server(self) -> str:
        return self._server
    
    def get_instance_name(self) -> str:
        return self._instance_name

    def _endpoint_url(self, endpoint: str, param: str = None) -> str:
        """Build endpoint URL for evolution-api."""
        base = f"{self._server}/message/{self._instance_name}"
        if endpoint == "instance":
            return f"{self._server}/instance/{self._instance_name}"
        elif param is not None:
            return f"{base}/{endpoint}/{param}"
        return f"{base}/{endpoint}"

    def start_session(self):
        """Connects and starts a session with evolution-api instance."""
        try:
            # Get instance connection state
            response = requests.get(
                f"{self._server}/instance/{self._instance_name}",
                headers=self._headers,
                timeout=self.DEFAULT_TIMEOUT
            )
            response.raise_for_status()
            instance_data = response.json()
            logging.debug(f"Instance info: {instance_data}")
            
            # Extract phone number from instance data
            if instance_data.get("instance") and instance_data["instance"].get("wid"):
                self._phone_number = instance_data["instance"]["wid"]
                logging.info(f"WhatsApp Phone: {self._phone_number}")
            
            # Set up webhook for message events if not already configured
            self._setup_webhook()
            
        except Exception as e:
            logging.error(f"Failed to start session: {e}")
            raise

    def _setup_webhook(self):
        """Configure webhook for message events."""
        try:
            # This would need to be implemented based on your environment
            # For now, we'll rely on WebSocket events instead
            logging.info("Using WebSocket for real-time events")
        except Exception as e:
            logging.warning(f"Webhook setup skipped: {e}")

    def logout_clear_session(self):
        """Logout and disconnect instance."""
        try:
            response = requests.post(
                f"{self._server}/instance/{self._instance_name}/logout",
                headers=self._headers,
                timeout=self.DEFAULT_TIMEOUT
            )
            logging.debug(response.json())
        except Exception as e:
            logging.error(f"Error during logout: {e}")

    def get_session_qr_code(self):
        """Get QR code for instance connection."""
        try:
            response = requests.get(
                f"{self._server}/instance/{self._instance_name}/qrcode",
                headers=self._headers,
                timeout=self.DEFAULT_TIMEOUT
            )
            qr_data = response.json()
            logging.debug(qr_data)
            return qr_data
        except Exception as e:
            logging.error(f"Error getting QR code: {e}")

    @override
    def send_message(self, chat_id: str, text: str):
        """Send a text message."""
        # The chat_id is in the format "whatsapp://<phone-number>" or just phone number
        if chat_id.startswith("whatsapp://"):
            recipient = chat_id.split("whatsapp://")[1]
        else:
            recipient = chat_id
        
        # Ensure phone number has proper format (should end with @c.us for individual or @g.us for group)
        if not recipient.endswith(("@c.us", "@g.us")):
            recipient = f"{recipient}@c.us"
        
        is_group = recipient.endswith("@g.us")
        self._send_message(recipient, is_group, text)

    def _send_message(self, recipient: str, is_group: bool, text: str):
        """Send text message using evolution-api."""
        logging.debug(f"Sending message to recipient: {recipient}")
        
        data = {
            "number": recipient,
            "text": text
        }
        
        try:
            response = requests.post(
                self._endpoint_url("send", "text"),
                json=data,
                headers=self._headers,
                timeout=self.DEFAULT_TIMEOUT
            )
            response.raise_for_status()
            logging.debug(response.json())
        except Exception as e:
            logging.error(f"Error sending message: {e}")

    def _react(self, message_id: str, recipient: str, reaction_text: str):
        """Send emoji reaction to a message."""
        data = {
            "number": recipient,
            "messageId": message_id,
            "emoji": reaction_text
        }
        
        try:
            response = requests.post(
                self._endpoint_url("send", "reaction"),
                json=data,
                headers=self._headers,
                timeout=self.DEFAULT_TIMEOUT
            )
            response.raise_for_status()
            logging.debug(response.json())
        except Exception as e:
            logging.error(f"Error sending reaction: {e}")

    @override
    def mark_in_progress_0(self, message: dict):
        recipient = message.get('chatId') or message.get('from')
        self._react(message['id'], recipient, self.REACT_HOURGLASS_FULL)
        self.send_typing(message, True)

    @override
    def mark_in_progress_50(self, message: dict):
        recipient = message.get('chatId') or message.get('from')
        self._react(message['id'], recipient, self.REACT_HOURGLASS_HALF)
        self.send_typing(message, True)

    @override
    def mark_skipped(self, message: dict):
        recipient = message.get('chatId') or message.get('from')
        self._react(message['id'], recipient, self.REACT_SKIP)
        self.send_typing(message, False)

    @override
    def mark_in_progress_done(self, message: dict):
        recipient = message.get('chatId') or message.get('from')
        self._react(message['id'], recipient, self.REACT_CHECKMARK)
        self.send_typing(message, False)

    @override
    def mark_in_progress_fail(self, message: dict):
        recipient = message.get('chatId') or message.get('from')
        self._react(message['id'], recipient, self.REACT_FAIL)
        self.send_typing(message, False)

    @override
    def mark_seen(self, message: dict) -> None:
        """Mark message as read."""
        message_id = message.get('id')
        chat_id = message.get('chatId') or message.get('from')
        
        data = {
            "number": chat_id,
            "messageId": message_id
        }
        
        try:
            response = requests.put(
                self._endpoint_url("read"),
                json=data,
                headers=self._headers,
                timeout=self.DEFAULT_TIMEOUT
            )
            response.raise_for_status()
            logging.debug(response.json())
        except Exception as e:
            logging.error(f"Error marking message as read: {e}")

    @override
    def mark_unseen(self, message: dict) -> None:
        """Mark message as unread (if supported by evolution-api)."""
        logging.warning("mark_unseen not directly supported by evolution-api")

    @override
    def is_group_message(self, message: dict):
        """Check if message is from a group."""
        return message.get('isGroupMsg') is True or (message.get('chatId') or '').endswith('@g.us')

    @override
    def is_self_message(self, message: dict):
        """Check if message is from bot itself."""
        return message.get('fromMe') is True

    @override
    def send_message_to_group(self, group_message: dict, text: str):
        recipient = group_message.get('chatId')
        if not recipient.endswith('@g.us'):
            recipient = f"{recipient}@g.us"
        self._send_message(recipient, True, text)

    @override
    def send_message_to_individual(self, message: dict, text: str):
        recipient = message.get('from') or message.get('chatId')
        if not recipient.endswith('@c.us'):
            recipient = f"{recipient}@c.us"
        self._send_message(recipient, False, text)

    @override
    def get_name(self) -> str:
        return "whatsapp-evo"

    @override
    def reply_message(self, message: dict, text: str) -> None:
        """Send a reply to a message."""
        recipient = message.get('chatId') or message.get('from')
        message_id = message.get('id')
        is_group = self.is_group_message(message)
        
        logging.debug(f"Replying to message ID: {message_id} in chat: {recipient}")
        
        data = {
            "number": recipient,
            "text": text,
            "quotedMessageId": message_id
        }
        
        try:
            response = requests.post(
                self._endpoint_url("send", "text"),
                json=data,
                headers=self._headers,
                timeout=self.DEFAULT_TIMEOUT
            )
            response.raise_for_status()
            logging.debug(response.json())
        except Exception as e:
            logging.error(f"Error sending reply: {e}")

    @override
    def delete_message(self, message: dict):
        """Delete a message."""
        message_id = message.get('id')
        chat_id = message.get('chatId') or message.get('from')
        
        data = {
            "number": chat_id,
            "messageId": message_id
        }
        
        try:
            response = requests.delete(
                self._endpoint_url("delete"),
                json=data,
                headers=self._headers,
                timeout=self.DEFAULT_TIMEOUT
            )
            response.raise_for_status()
            logging.debug(response.json())
        except Exception as e:
            logging.error(f"Error deleting message: {e}")

    def _send_image(self, recipient: str, file_name: str, binary_data, caption: str = ""):
        """Send an image message."""
        base64data = base64.b64encode(binary_data).decode('utf-8')
        
        if file_name.endswith('.webp'):
            data_type = "image/webp"
        elif file_name.endswith('.jpg') or file_name.endswith('.jpeg'):
            data_type = "image/jpeg"
        else:
            data_type = "image/png"
        
        data = {
            "number": recipient,
            "media": {
                "url": f"data:{data_type};base64,{base64data}",
                "caption": caption
            }
        }
        
        try:
            response = requests.post(
                self._endpoint_url("send", "media"),
                json=data,
                headers=self._headers,
                timeout=self.DEFAULT_TIMEOUT
            )
            response.raise_for_status()
            logging.debug(response.json())
        except Exception as e:
            logging.error(f"Error sending image: {e}")

    @override
    def send_image_to_group(self, group_message: dict, file_name: str, binary_data, caption: str = ""):
        recipient = group_message.get('chatId')
        if not recipient.endswith('@g.us'):
            recipient = f"{recipient}@g.us"
        self._send_image(recipient, file_name, binary_data, caption)

    @override
    def send_image_to_individual(self, message: dict, file_name: str, binary_data, caption: str = ""):
        recipient = message.get('from') or message.get('chatId')
        if not recipient.endswith('@c.us'):
            recipient = f"{recipient}@c.us"
        self._send_image(recipient, file_name, binary_data, caption)

    @override
    def send_audio_to_group(self, group_message: dict, audio_file_path: str):
        recipient = group_message.get('chatId')
        if not recipient.endswith('@g.us'):
            recipient = f"{recipient}@g.us"
        self._send_audio(recipient, audio_file_path)

    @override
    def send_audio_to_individual(self, message: dict, audio_file_path: str):
        recipient = message.get('from') or message.get('chatId')
        if not recipient.endswith('@c.us'):
            recipient = f"{recipient}@c.us"
        self._send_audio(recipient, audio_file_path)

    @override
    def create_poll(self, message: dict, question: str, options: list[str]):
        """Create a poll (not yet implemented for evolution-api)."""
        pass

    @override
    def vote_poll(self, message: dict, option_index: int):
        """Vote on a poll (not yet implemented for evolution-api)."""
        pass

    @override
    def close_poll(self, message: dict):
        """Close a poll (not yet implemented for evolution-api)."""
        pass

    def _send_audio(self, recipient: str, audio_file_path: str):
        """Send an audio message (voice note)."""
        try:
            # Convert audio to opus format if needed
            with tempfile.TemporaryDirectory() as tmp:
                output_file = os.path.join(tmp, 'output.ogg')
                subprocess.run(["opusenc", audio_file_path, output_file], check=True)
                
                with open(output_file, 'rb') as file:
                    binary_data = file.read()
            
            base64data = base64.b64encode(binary_data).decode('utf-8')
            
            data = {
                "number": recipient,
                "media": {
                    "url": f"data:audio/ogg;base64,{base64data}"
                }
            }
            
            response = requests.post(
                self._endpoint_url("send", "media"),
                json=data,
                headers=self._headers,
                timeout=self.DEFAULT_TIMEOUT
            )
            response.raise_for_status()
            logging.debug(response.json())
        except Exception as e:
            logging.error(f"Error sending audio: {e}")

    @override
    def has_audio_data(self, message: dict):
        """Check if message contains audio data."""
        message_type = message.get('type', '').lower()
        return message_type in ['audio', 'ptt']

    @override
    def has_image_data(self, message: dict):
        """Check if message contains image data."""
        message_type = message.get('type', '').lower()
        return message_type == 'image'

    @override
    def is_bot_mentioned(self, message: dict):
        """Check if bot is mentioned in the message."""
        mentions = message.get('mentions', [])
        for mention in mentions:
            if mention == self._phone_number:
                logging.debug("Bot mentioned in message.")
                return True
        return False

    @override
    def get_message_text(self, message: dict):
        """Extract text from message."""
        # Handle different message types
        message_type = message.get('type', '').lower()
        
        if message_type == 'image':
            return message.get('caption', "")
        elif message_type in ['audio', 'ptt']:
            return ""  # Audio messages typically don't have text
        
        return message.get('body', "") or message.get('text', "")

    @override
    def get_chat_id(self, message: dict) -> str:
        """Get chat ID in standard format."""
        chat_id = message.get('chatId') or message.get('from')
        return f"whatsapp://{chat_id}"

    @override
    def get_sender_name(self, message: dict):
        """Get sender display name."""
        return message.get('pushName', message.get('senderName', "Unknown"))

    @override
    def download_media(self, message: dict):
        """Download media from message."""
        try:
            msg_id = message.get('id')
            chat_id = message.get('chatId') or message.get('from')
            
            response = requests.get(
                f"{self._server}/chat/{self._instance_name}/download-media",
                params={"messageId": msg_id, "number": chat_id},
                headers=self._headers,
                timeout=self.DEFAULT_TIMEOUT
            )
            response.raise_for_status()
            
            # The response should contain base64 encoded media
            response_data = response.json()
            if 'base64' not in response_data or 'mimeType' not in response_data:
                raise ValueError("Invalid media response: missing 'base64' or 'mimeType'")
            
            data = response_data['base64']
            decoded = base64.b64decode(data)
            mime_type = response_data['mimeType']
            
            return (mime_type, decoded)
        except Exception as e:
            logging.error(f"Error downloading media: {e}")
            raise

    @override
    def send_typing(self, message: dict, typing: bool):
        """Send typing indicator."""
        recipient = message.get('chatId') or message.get('from')
        is_group = self.is_group_message(message)
        
        data = {
            "number": recipient,
            "typing": typing
        }
        
        try:
            response = requests.post(
                self._endpoint_url("send", "presence"),
                json=data,
                headers=self._headers,
                timeout=self.DEFAULT_TIMEOUT
            )
            response.raise_for_status()
            logging.debug(response.json())
        except Exception as e:
            logging.debug(f"Could not send typing indicator: {e}")


class WhatsappEvoMessageQueue:
    """Handle WebSocket connection for real-time message events from evolution-api."""

    def __init__(self, messenger_instance: WhatsappEvoMessenger, callback: Callable[[MessengerInterface, dict], None]) -> None:
        self._messenger = messenger_instance
        self._callback = callback
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
        logging.info("Connected to Evolution-API server")

    def on_disconnect(self):
        logging.info("Disconnected from Evolution-API server")

    def on_message(self, data):
        logging.info(f"Received message: {data}")

    def on_new_message(self, data):
        # shorten the log message in the middle with '...' if it's too long
        max_length = 750
        if "response" not in data:
            logging.warning(f"Received message without 'response' field: {data}")
            return
        
        if "session" not in data["response"]:
            logging.warning(f"Received message without 'session' field in response: {data}")
            return
        
        session = data["response"]["session"]
        if session != self._messenger.get_session():
            logging.warning(f"Received message for session {session}, but current session is {self._messenger.get_session()}. Ignoring message.")
            return
        
        if len(str(data)) > max_length:
            logging.info(f"Message: {str(data)[:int(max_length/2)]}...{str(data)[-int(max_length/2):]}")
        else:
            logging.info(f"Message: {data}")
        self._callback(self._messenger, data['response'])

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
