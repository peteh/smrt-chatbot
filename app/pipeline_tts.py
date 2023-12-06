"""Implemenations of a pipeline for processing text to speech. """
import logging
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
        self._model_path = f"{utils.storage_path()}/custom_models/"
        self._models = {}
        
        subdirectories = [d[5:] for d in os.listdir(self._model_path) if os.path.isdir(os.path.join(self._model_path, d)) and d.startswith("xtts_")]
        for subdir in subdirectories:
            self._models[subdir] = None
        
        self._commands = [self.TTS_COMMAND]
        for model in self._models.keys():
            self._commands.append(f"tts_{model}")
            self._commands.append(f"tts_{model}_de")
    
    def get_model_name(self, command : str):
        if command.startswith("tts_"):
            model = command[4:]
            language = "en"
            if command.endswith("_de"):
                language = "de"
                model = model[:-3]
            return (model, language)
        return (None, None)
    
    def get_model(self, model_name):
        # lazy loading
        if self._models[model_name] is None: 
            self._models[model_name] = XttsModel(f"{utils.storage_path()}/custom_models/xtts_{model_name}")
        return self._models[model_name]
        

    def _get_tts_thorsten(self):
        # lazy loading
        if self._tts_thorsten is None:
            self._tts_thorsten = ThorstenTtsVoice()
        return self._tts_thorsten
    
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
        return command in self._commands
        

    def process(self, messenger: MessengerInterface, message: dict):
        (command, _, text) = PipelineHelper.extract_command_full(messenger.get_message_text(message))
        messenger.mark_in_progress_0(message)
        try:            
            model_name , language = self.get_model_name(command)
            tts = None
            if model_name is not None:
                tts = self.get_model(model_name)
            else: 
                tts = self._get_tts_thorsten()
                language = "en"
                
            audio_data = self._text_to_vorbis_audio(tts, text, language)

            if messenger.is_group_message(message):
                messenger.send_audio_to_group(message, audio_data)
            else:
                messenger.send_audio_to_individual(message, audio_data)

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
