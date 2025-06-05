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
import websockets.sync.client

from pipeline import PipelineInterface, PipelineHelper
from messenger import MessengerInterface


class HomeassistantTextCommandPipeline(PipelineInterface):
    """Pipe to handle ha commands in text. """
    HA_COMMAND = "ha"

    def __init__(self, ha_token: str, ha_ws_api_url: str, chat_id_whitelist: typing.List[str]):
        self._ha_token = ha_token
        self._ha_ws_api_url = ha_ws_api_url
        self._chat_id_whitelist = chat_id_whitelist
        self._commands = [self.HA_COMMAND]


    def matches(self, messenger: MessengerInterface, message: dict):
        # TODO: need to also filter group
        command = PipelineHelper.extract_command(messenger.get_message_text(message))
        return command in self._commands \
            and messenger.get_chat_id(message) in self._chat_id_whitelist
    
    def process_text_command(self, ha_command: str):
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
            }
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
        (command, _, text) = PipelineHelper.extract_command_full(messenger.get_message_text(message))
        messenger.mark_in_progress_0(message)
        try:            
            ha_command = text.strip()
            messenger.mark_in_progress_0(message)
            responst_text = self.process_text_command(ha_command)
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
_#ha text_ Sends a homeassistant command to homeassistant. """

class HomeassistantVoiceCommandPipeline(PipelineInterface):
    """Pipe to generate a voice messages based on audio input. """
    def __init__(self, ha_token: str, ha_ws_api_url: str, chat_id_whitelist: typing.List[str]):
        self._ha_token = ha_token
        self._ha_ws_api_url = ha_ws_api_url
        self._chat_id_whitelist = chat_id_whitelist


    def matches(self, messenger: MessengerInterface, message: dict):
        return messenger.has_audio_data(message) \
            and messenger.get_chat_id(message) in self._chat_id_whitelist

    def process_voice_command(self, wav_path: str):
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
            }
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
                responst_text = self.process_voice_command(voice_data_wav_file_path)
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
_#tts text_ Generates a voice message by Thorsten voice with the given text"""
