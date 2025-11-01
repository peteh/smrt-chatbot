"""Implemenations of a pipeline for processing text to speech. """
import logging
import tempfile
import os
from pathlib import Path
from smrt.bot.messenger import MessengerInterface
from smrt.bot.pipeline import PipelineHelper, AbstractPipeline
import smrt.utils.utils as utils

from smrt.bot.tools.texttospeech import XttsModel, ThorstenTtsVoice
from smrt.bot.tools.texttospeech_piper import PiperTTSModel


class TextToSpeechPipeline(AbstractPipeline):
    """Pipe to generate a voice messages based on input text. """
    TTS_COMMAND = "tts"

    def __init__(self, model_path: Path|str):
        super().__init__(None, None)
        self._tts_thorsten = None
        self._model_path = Path(model_path)
        self._xtts_models = {}

        xtts_models = [d[5:] for d in os.listdir(self._model_path) if os.path.isdir(os.path.join(self._model_path, d)) and d.startswith("xtts_")]
        for subdir in xtts_models:
            logging.info(f"Found xtts model: {subdir}")
            self._xtts_models[subdir] = XttsModel(self._model_path / f"xtts_{subdir}")
        
        piper_models = [d for d in os.listdir(self._model_path) if os.path.isdir(os.path.join(self._model_path, d)) and d.startswith("piper_")]
        for subdir in piper_models:
            model_folder = self._model_path / subdir
            model_name = subdir[6:]
            logging.info(f"Found piper model: {model_name}")
            onnx_files = list(model_folder.glob("*.onnx"))
            if len(onnx_files) != 1:
                logging.error(f"Folder {model_folder} does contain none or multiple onnx files")
                continue
            self._xtts_models[model_name] = PiperTTSModel(onnx_files[0])
        self._xtts_models["thorsten"] = ThorstenTtsVoice()
        self._xtts_models[""] = ThorstenTtsVoice() # default model
        
        self._commands = [self.TTS_COMMAND]
        for model in self._xtts_models.keys():
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
        if model_name is None:
            model_name = ""
        return self._xtts_models[model_name]

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
                tts = self.get_model("")

            with tempfile.TemporaryDirectory() as tmp:
                tmp_path = Path(tmp)
                output_file = tmp_path / "output.wav"
                tts.tts(text, output_file, language)

                if messenger.is_group_message(message):
                    messenger.send_audio_to_group(message, output_file)
                else:
                    messenger.send_audio_to_individual(message, output_file)

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
