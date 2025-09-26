"""Implementations of a pipeline for processing text and voice for homeassistant. """
import logging

import subprocess

# text to speech pipeline standard imports
import tempfile
import os
import typing
import json
import wave
import time
import uuid
import websockets.sync.client

from smrt.bot.pipeline import PipelineInterface, PipelineHelper
from smrt.bot.messenger import MessengerInterface


class AbstractHomeassistantPipeline(PipelineInterface):
    """Abstract base class for Homeassistant pipelines."""
    def __init__(self, ha_token: str, ha_ws_api_url: str, chat_id_whitelist: typing.List[str]):
        self._ha_token = ha_token
        self._ha_ws_api_url = ha_ws_api_url
        self._chat_id_whitelist = chat_id_whitelist
        self._root_uuid = uuid.UUID("BEEEEEEF-DEAD-DEAD-DEAD-BEEEEEEEEEEF")

    def _get_chat_id_whitelist(self) -> typing.List[str]:
        """Get the list of chat IDs that are allowed to use this pipeline."""
        return self._chat_id_whitelist

    def _get_uuid_from_chat_id(self, chat_id: str) -> uuid.UUID:
        return uuid.uuid5(namespace=self._root_uuid, name=chat_id)

    def matches(self, messenger: MessengerInterface, message: dict):
        raise NotImplementedError("Subclasses should implement this method.")

    def process(self, messenger: MessengerInterface, message: dict):
        raise NotImplementedError("Subclasses should implement this method.")

    def get_help_text(self) -> str:
        raise NotImplementedError("Subclasses should implement this method.")

class HomeassistantTextCommandPipeline(AbstractHomeassistantPipeline):
    """Pipe to handle ha commands in text. """
    HA_COMMAND = "ha"

    def __init__(self, ha_token: str, ha_ws_api_url: str, chat_id_whitelist: typing.List[str], process_without_command = False):
        super().__init__(ha_token, ha_ws_api_url, chat_id_whitelist)
        self._commands = [self.HA_COMMAND]
        self._process_without_command = process_without_command  # if true, will process any text command without the #ha prefix

    def matches(self, messenger: MessengerInterface, message: dict):
        if messenger.get_chat_id(message) not in self._get_chat_id_whitelist():
            return False
        message_text = messenger.get_message_text(message)
        if message_text is None:
            return False

        if self._process_without_command and not message_text.startswith("#"):
            # If we process without command, we just check if the message has text and does not start with a command
            message_text = messenger.get_message_text(message)
            return message_text is not None and len(messenger.get_message_text(message)) > 0

        # we check if the mesage is a ha command
        command = PipelineHelper.extract_command(messenger.get_message_text(message))
        return command in self._commands

    def process_text_command(self, ha_command: str, conversation_id: str):
        ws =  websockets.sync.client.connect(self._ha_ws_api_url)

        # Step 1: Receive auth_required
        ws.recv()

        # Step 2: Authenticate
        ws.send(json.dumps({
            "type": "auth",
            "access_token": self._ha_token
        }))
        ws.recv()  # auth_ok

        # Step 3: Start the pipeline
        msg_id = 1
        ws.send(json.dumps({
            "id": msg_id,
            "type": "assist_pipeline/run",
            "start_stage": "intent",
            "end_stage": "intent",
            "input": {
                "text": ha_command,
            },
            "conversation_id": conversation_id
        }))
        logging.debug("Pipeline started, waiting for run_start...")

        msg = json.loads(ws.recv())
        if not (msg["type"] == "result" and msg["success"] == True):
            raise Exception(f"Unexpected message type: {msg['type']}")

        msg = json.loads(ws.recv())
        if not (msg["type"] == "event" and msg["event"]["type"] == "run-start"):
            raise Exception(f"Unexpected message type: {msg['type']} with event {msg['event']['type']}")

        conversation_id = msg["event"]["data"]["conversation_id"]

        msg_id += 1

        logging.debug(f"Pipeline started with conversation_id: {conversation_id}")

        msg = json.loads(ws.recv())
        if msg["event"]["type"] != "intent-start":
            raise Exception(f"Unexpected message type: {msg['type']} with event {msg['event']['type']}")

        msg = json.loads(ws.recv())
        print("Pipeline response:", msg)
        if msg["event"]["type"] != "intent-end":
            raise Exception(f"Unexpected message type: {msg['type']} with event {msg['event']['type']}")
        response_text = msg["event"]["data"]["intent_output"]["response"]["speech"]["plain"]["speech"]
        logging.info(f"Response text: {response_text}")
        ws.close()
        return response_text

    def process(self, messenger: MessengerInterface, message: dict):
        text = messenger.get_message_text(message)
        if self._process_without_command:
            text = text.strip()
        if text.startswith(f"#{self.HA_COMMAND}"):
            (command, _, text) = PipelineHelper.extract_command_full(messenger.get_message_text(message))

        messenger.mark_in_progress_0(message)
        try:            
            ha_command = text.strip()
            messenger.mark_in_progress_0(message)
            conversation_id = self._get_uuid_from_chat_id(messenger.get_chat_id(message))
            responst_text = self.process_text_command(ha_command, str(conversation_id))
            messenger.reply_message(message, responst_text)
            messenger.mark_in_progress_done(message)
       
        except Exception as ex:
            logging.critical(ex, exc_info=True)  # log exception info at CRITICAL log level
            messenger.mark_in_progress_fail(message)
            return
    def get_help_text(self) -> str:
        # TODO: automatically tell which models we have
        return \
"""*Text to Speech*
_#ha text_ Sends a homeassistant command to homeassistant (You can also send voice messages with HA commands). """

class HomeassistantSayCommandPipeline(AbstractHomeassistantPipeline):
    """Pipe to handle ha commands in text. """
    HA_COMMAND = "say"

    def __init__(self, ha_token: str, ha_ws_api_url: str, chat_id_whitelist: typing.List[str]):
        super().__init__(ha_token, ha_ws_api_url, chat_id_whitelist)
        self._commands = [self.HA_COMMAND]


    def matches(self, messenger: MessengerInterface, message: dict):
        command = PipelineHelper.extract_command(messenger.get_message_text(message))
        return command in self._commands \
            and messenger.get_chat_id(message) in self._get_chat_id_whitelist()

    def process_say_command(self, text: str):
        ws =  websockets.sync.client.connect(self._ha_ws_api_url)

        # Step 1: Receive auth_required
        ws.recv()

        # Step 2: Authenticate
        ws.send(json.dumps({
            "type": "auth",
            "access_token": self._ha_token
        }))
        ws.recv()  # auth_ok

        msg_id = 1

        # Send label registry list request
        #ws.send(json.dumps({
        #    "id": msg_id,
        #    "type": "config/label_registry/list"
        #}))

        # Step 5: Receive label list response
        #response = ws.recv()
        #data = json.loads(response)

        # Pretty print results
        #for label in data.get("result", []):
        #    print(f"Label: {label}")
        
        #msg_id += 1
        
        # Step 3: Run TTS pipeline
        tts_msg = {
            "id": msg_id,
            "type": "call_service",
            "domain": "assist_satellite",
            "service": "announce",

            "service_data": {
                "message": text,
            },
            "target": {
                #"entity_id": ["assist_satellite.living_room_assist_assist_satellite"]
                "label_id": "saycommand"
            },
            "return_response": False
        }


        ws.send(json.dumps(tts_msg))

        # Step 4: Receive all messages until done
        msg = ws.recv()
        data = json.loads(msg)
        logging.debug(f"Received: {data}")
        ws.close()

    def process(self, messenger: MessengerInterface, message: dict):
        (command, _, text) = PipelineHelper.extract_command_full(messenger.get_message_text(message))
        messenger.mark_in_progress_0(message)
        try:            
            ha_command = text.strip()
            messenger.mark_in_progress_0(message)
            self.process_say_command(ha_command)
            messenger.mark_in_progress_done(message)    
        except Exception as ex:
            logging.critical(ex, exc_info=True)  # log exception info at CRITICAL log level
            messenger.mark_in_progress_fail(message)
            return
    def get_help_text(self) -> str:
        # TODO: automatically tell which models we have
        return \
"""*Text to Speech*
_#say text_ Sends a message to homeassistant to be spoken by the voice assistant."""

class HomeassistantVoiceCommandPipeline(AbstractHomeassistantPipeline):
    """Pipe to generate a voice messages based on audio input. """
    def __init__(self, ha_token: str, ha_ws_api_url: str, chat_id_whitelist: typing.List[str]):
        super().__init__(ha_token, ha_ws_api_url, chat_id_whitelist)



    def matches(self, messenger: MessengerInterface, message: dict):
        return messenger.has_audio_data(message) \
            and messenger.get_chat_id(message) in self._get_chat_id_whitelist()

    def process_voice_command(self, wav_path: str, conversation_id: str) -> typing.Tuple[str, str]:
        ws =  websockets.sync.client.connect(self._ha_ws_api_url)

        # Step 1: Receive auth_required
        ws.recv()

        # Step 2: Authenticate
        ws.send(json.dumps({
            "type": "auth",
            "access_token": self._ha_token
        }))
        ws.recv()  # auth_ok

        # Step 3: Start the pipeline
        msg_id = 1
        ws.send(json.dumps({
            "id": msg_id,
            "type": "assist_pipeline/run",
            "start_stage": "stt",
            "end_stage": "intent",
            "input": {
                "sample_rate": 16000,
            },
            "conversation_id": conversation_id
        }))
        logging.debug("Pipeline started, waiting for run_start...")

        msg = json.loads(ws.recv())
        if not (msg["type"] == "result" and msg["success"] == True):
            raise Exception(f"Unexpected message type: {msg['type']}")

        msg = json.loads(ws.recv())
        if not (msg["type"] == "event" and msg["event"]["type"] == "run-start"):
            raise Exception(f"Unexpected message type: {msg['type']} with event {msg['event']['type']}")

        conversation_id = msg["event"]["data"]["conversation_id"]
        stt_binary_handler_id = msg["event"]["data"]["runner_data"]["stt_binary_handler_id"]

        msg_id += 1

        msg = json.loads(ws.recv())
        if not (msg["type"] == "event" and msg["event"]["type"] == "stt-start"):
            raise Exception(f"Unexpected message type: {msg['type']} with event {msg['event']['type']}")

        logging.debug(f"Pipeline started with conversation_id: {conversation_id}, stt_binary_handler_id: {stt_binary_handler_id}")

        # Step 5: Stream audio in chunks
        print("Streaming audio to pipeline...")
        with wave.open(wav_path, "rb") as wf:
            chunk_size = 2048
            while True:
                data = wf.readframes(chunk_size)
                if not data:
                    break
                logging.debug(f"Sending chunk of size {len(data)}")
                ws.send(bytes([stt_binary_handler_id]) + data)
                time.sleep(0.01)  # slight delay to simulate streaming

        # Step 6: Send audio end marker
        ws.send(bytes([stt_binary_handler_id]))
        print("Audio stream ended.")

        # Step 7: Wait for response
        msg = json.loads(ws.recv())
        if msg["event"]["type"] != "stt-vad-start":
            raise Exception(f"Unexpected message type: {msg['type']} with event {msg['event']['type']}")

        msg = json.loads(ws.recv())
        if msg["event"]["type"] != "stt-end":
            raise Exception(f"Unexpected message type: {msg['type']} with event {msg['event']['type']}")
        
        command_text = msg["event"]["data"]["stt_output"]["text"]
        print(f"STT output: {command_text}")

        msg = json.loads(ws.recv())
        if msg["event"]["type"] != "intent-start":
            raise Exception(f"Unexpected message type: {msg['type']} with event {msg['event']['type']}")

        msg = json.loads(ws.recv())
        print("Pipeline response:", msg)
        if msg["event"]["type"] != "intent-end":
            raise Exception(f"Unexpected message type: {msg['type']} with event {msg['event']['type']}")
        response_text = msg["event"]["data"]["intent_output"]["response"]["speech"]["plain"]["speech"]
        logging.info(f"Response text: {response_text}")
        ws.close()
        return (command_text, response_text)

    def process(self, messenger: MessengerInterface, message: dict):
        messenger.mark_in_progress_0(message)
        try:            
            (_, decoded) = messenger.download_media(message)
            with tempfile.TemporaryDirectory() as tmp:
                voice_data_file_path = os.path.join(tmp, 'audio.opus')
                f = open(voice_data_file_path, "wb")
                f.write(decoded)
                f.close()
                voice_data_wav_file_path = os.path.join(tmp, 'audio.wav')
                subprocess.run(["ffmpeg", "-i", voice_data_file_path, "-ar", "16000", "-ac", "1", "-sample_fmt", "s16", voice_data_wav_file_path, ], check=True)
                conversation_id = self._get_uuid_from_chat_id(messenger.get_chat_id(message))
                command_text, responst_text = self.process_voice_command(voice_data_wav_file_path, str(conversation_id))
                messenger.reply_message(message, f"Command: {command_text}\nResponse: {responst_text}")
                messenger.mark_in_progress_done(message)
        except Exception as ex:
            logging.critical(ex, exc_info=True)  # log exception info at CRITICAL log level
            messenger.mark_in_progress_fail(message)
            return
    def get_help_text(self) -> str:
        # no extra need for help
        return ""
