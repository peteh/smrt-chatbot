"""Implemenations of a pipeline for processing text to speech. """
from decouple import config
from pipeline import PipelineInterface, PipelineHelper
import utils

# text to speech pipeline standard imports
import tempfile
import os
import subprocess

from texttospeech import XttsModel, ThorstenTtsVoice, TextToSpeechInterface
from messenger import MessengerInterface

class TextToSpeechPipeline(PipelineInterface):
    """Pipe to generate a voice messages based on input text. """
    TTS_COMMAND = "tts"
    ARNY_COMMAND = "arny"
    ARNYDE_COMMAND = "arnyde"
    ARNY2_COMMAND = "arny2"
    ARNY2DE_COMMAND = "arny2de"
    
    TTSMAX_COMMAND = "ttsmax"
    TTSMAXDE_COMMAND = "ttsmaxde"

    def __init__(self):
        self._tts_thorsten = None
        self._tts_arny1 = None
        self._tts_arny2 = None

    def _get_tts_thorsten(self):
        # lazy loading
        if self._tts_thorsten is None:
            self._tts_thorsten = ThorstenTtsVoice()
        return self._tts_thorsten
    
    def _get_tts_arny1(self):
        if self._tts_arny1 is None: 
            self._tts_arny1 = XttsModel(f"{utils.storage_path()}/custom_models/xtts_arny1")
        return self._tts_arny1
    
    def _get_tts_arny2(self):
        if self._tts_arny2 is None: 
            self._tts_arny2 = XttsModel(f"{utils.storage_path()}/custom_models/xtts_arny2")
        return self._tts_arny2
    
    def _get_tts_max1(self):
        if self._tts_max1 is None: 
            self._tts_max1 = XttsModel(f"{utils.storage_path()}/custom_models/xtts_maxerndwein1")
        return self._tts_max1

    def _text_to_vorbis_audio(self, tts : TextToSpeechInterface, text: str, language: str):
        with tempfile.TemporaryDirectory() as tmp:
            # TODO build this with generic file names
            input_file = os.path.join(tmp, 'input.wav')
            tts.tts(text, input_file, language)
            output_file = os.path.join(tmp, 'output.opus')

            subprocess.run(["opusenc", input_file, output_file], check=True)
            file = open(output_file,mode='rb')
            ogg_data = file.read()
            file.close()
        return ogg_data

    def matches(self, messenger: MessengerInterface, message: dict):
        command = PipelineHelper.extract_command(messenger.get_message_text(message))
        return self.TTS_COMMAND in command \
            or self.ARNY_COMMAND in command \
            or self.ARNYDE_COMMAND in command \
            or self.ARNY2_COMMAND in command \
            or self.ARNY2DE_COMMAND in command \
            or self.TTSMAX_COMMAND in command \
            or self.TTSMAXDE_COMMAND in command

    def process(self, messenger: MessengerInterface, message: dict):
        (command, _, text) = PipelineHelper.extract_command_full(messenger.get_message_text(message))
        messenger.mark_in_progress_0(message)
        language = None
        
        tts = None
        if command == self.ARNY_COMMAND:
            tts = self._get_tts_arny1()
            language = "en"
        elif command == self.ARNYDE_COMMAND:
            tts = self._get_tts_arny1()
            language = "de"
        if command == self.ARNY2_COMMAND:
            tts = self._get_tts_arny2()
            language = "en"
        elif command == self.ARNY2DE_COMMAND:
            tts = self._get_tts_arny2()
            language = "de"
        if command == self.TTSMAX_COMMAND:
            tts = self._get_tts_max1()
            language = "en"
        elif command == self.TTSMAXDE_COMMAND:
            tts = self._get_tts_max1()
            language = "de"
        else: 
            tts = self._get_tts_thorsten()
            language = "en"
        audio_data = self._text_to_vorbis_audio(tts, text, language)

        if messenger.is_group_message(message):
            messenger.send_audio_to_group(message, audio_data)
        else:
            messenger.send_audio_to_individual(message, audio_data)

        messenger.mark_in_progress_done(message)
    def get_help_text(self) -> str:
        return \
"""*Text to Speech*
_#arny text_ Generates a voice message by Arnold Schwarzenegger voice with the given text
_#arnyde text_ Generates a voice message by German Arnold Schwarzenegger voice with the given text
_#tts text_ Generates a voice message by Thorsten voice with the given text"""
