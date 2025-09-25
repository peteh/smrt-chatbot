
from abc import ABC, abstractmethod
import torch
from TTS.api import TTS

from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts
import torchaudio
from decouple import config
import logging

class TextToSpeechInterface(ABC):
    @abstractmethod
    def tts(self, text: str, output_wav_file : str, language : str = None) -> bool:
        """Outputs a wav file with the given tts text. 

        Args:
            text (str): The text to say
            output_wav_file (str): the target file where to write to
            language (str, optional): Language id, e.g. de, en, es... , some models support a target language. Defaults to None.

        Returns:
            bool: True if the processing was successful
        """

class ThorstenTtsVoice(TextToSpeechInterface):
    def __init__(self) -> None:
        self._tts = TTS("tts_models/de/thorsten/tacotron2-DDC")
    
    def tts(self, text: str, output_wav_file : str, language : str = None) -> bool:
        self._tts.tts_to_file(text=text, file_path=output_wav_file)

class XttsModel(TextToSpeechInterface):
    def __init__(self, model_path: str, reference_wav: str = "reference.wav", default_lang : str = "en") -> None:
        xtts_config = "config.json"
        xtts_checkpoint = "model.pth"
        xtts_vocab = "vocab.json"
        self._reference_wav = reference_wav
        self._model_path = model_path
        self._config = XttsConfig()
        self._config.load_json(f"{self._model_path}/{xtts_config}")
        self._model = Xtts.init_from_config(self._config)
        self._language = default_lang
        logging.info(f"Loading XTTS model: {self._model_path}")
        #self._model.load_checkpoint(self._config, checkpoint_path=f"{self._model_path}/{xtts_checkpoint}", vocab_path=f"{self._model_path}/{xtts_vocab}", use_deepspeed=False)
        self._model.load_checkpoint(self._config, checkpoint_dir=self._model_path, use_deepspeed=False)
        if torch.cuda.is_available():
            self._model.cuda()
        logging.info("Model Loaded!")
    
    def tts(self, text: str, output_wav_file : str, language : str = None) -> bool:
        gpt_cond_latent, speaker_embedding = self._model.get_conditioning_latents(audio_path=f"{self._model_path}/{self._reference_wav}", 
                                                                                  gpt_cond_len=self._model.config.gpt_cond_len, 
                                                                                  max_ref_length=self._model.config.max_ref_len, 
                                                                                  sound_norm_refs=self._model.config.sound_norm_refs)
        target_lang = language if language is not None else self._language
        
        out = self._model.inference(
            text=text,
            language=target_lang,
            gpt_cond_latent=gpt_cond_latent,
            speaker_embedding=speaker_embedding,
            temperature=self._model.config.temperature, # Add custom parameters here
            length_penalty=self._model.config.length_penalty,
            repetition_penalty=self._model.config.repetition_penalty,
            top_k=self._model.config.top_k,
            top_p=self._model.config.top_p,
            enable_text_splitting = True
        )
        out["wav"] = torch.tensor(out["wav"]).unsqueeze(0)
        torchaudio.save(output_wav_file, out["wav"], 24000)