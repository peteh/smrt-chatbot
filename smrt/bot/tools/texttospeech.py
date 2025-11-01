import logging
from abc import ABC, abstractmethod
import torch
from TTS.api import TTS

from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts
import torchaudio

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
        pass
    
    def tts(self, text: str, output_wav_file : str, language : str = None) -> bool:
        tts = TTS("tts_models/de/thorsten/tacotron2-DDC")
        tts.tts_to_file(text=text, file_path=output_wav_file)

class XttsModel(TextToSpeechInterface):
    # TODO: don't load directly but only when doing tts
    def __init__(self, model_path: str, reference_wav: str = "reference.wav", default_lang : str = "en") -> None:
        self._xtts_config = "config.json"
        xtts_checkpoint = "model.pth"
        xtts_vocab = "vocab.json"
        self._reference_wav = reference_wav
        self._model_path = model_path
        self._default_lang = default_lang

    def tts(self, text: str, output_wav_file : str, language : str|None = None) -> None:
        config = XttsConfig()
        config.load_json(f"{self._model_path}/{self._xtts_config}")
        model = Xtts.init_from_config(config)

        logging.info(f"Loading XTTS model: {self._model_path}")
        #self._model.load_checkpoint(self._config, checkpoint_path=f"{self._model_path}/{xtts_checkpoint}", vocab_path=f"{self._model_path}/{xtts_vocab}", use_deepspeed=False)
        model.load_checkpoint(config, checkpoint_dir=self._model_path, use_deepspeed=False)
        if torch.cuda.is_available():
            model.cuda()
        logging.info("Model Loaded!")

        gpt_cond_latent, speaker_embedding = model.get_conditioning_latents(audio_path=f"{self._model_path}/{self._reference_wav}", 
                                                                                  gpt_cond_len=model.config.gpt_cond_len, 
                                                                                  max_ref_length=model.config.max_ref_len, 
                                                                                  sound_norm_refs=model.config.sound_norm_refs)
        target_lang = language if language is not None else self._default_lang

        out = model.inference(
            text=text,
            language=target_lang,
            gpt_cond_latent=gpt_cond_latent,
            speaker_embedding=speaker_embedding,
            temperature=model.config.temperature, # Add custom parameters here
            length_penalty=model.config.length_penalty,
            repetition_penalty=model.config.repetition_penalty,
            top_k=model.config.top_k,
            top_p=model.config.top_p,
            enable_text_splitting = True
        )
        out["wav"] = torch.tensor(out["wav"]).unsqueeze(0)
        torchaudio.save(output_wav_file, out["wav"], 24000)
