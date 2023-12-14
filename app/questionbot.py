"""Question bot implementations. """
import logging
from abc import ABC, abstractmethod
from typing import List

import base64
import multiprocessing

# openai api questionbot
from openai import OpenAI

class QuestionBotInterface(ABC):
    """Interface for question bots"""

    @abstractmethod
    def answer(self, prompt: str) -> dict:
        """Returns an answer to a prompt based on the underlying bots response"""

class QuestionBotImageInterface(ABC):
    """Interface for question bots"""

    @abstractmethod
    def answer_image(self, prompt: str, image_path: str) -> dict:
        """Answers the prompt to the given image

        Args:
            prompt (str): The prompt to ask for the image
            image_path (str): the path to the image

        Returns:
            dict: _description_
        """

class QuestionBotOpenAIAPI(QuestionBotInterface):
    """Question bot based on Open AI's offical api. """
    def __init__(self, api_key) -> None:
        super().__init__()
        self._api_key = api_key
        self._cost_per_token = 0.002 / 1000.

    def answer(self, prompt: str):
        client = OpenAI(api_key=self._api_key)
        completion = client.chat.completions.create(model="gpt-3.5-turbo",
                                                  messages=[{"role": "user",
                                                             "content": prompt}])
        usage = dict(completion).get('usage')
        cost = usage.total_tokens * self._cost_per_token
        response = completion.choices[0].message.content
        print(response)
        return {
            'text': response, 
            'cost': cost
        }

import requests
from decouple import config
class QuestionBotOllama(QuestionBotInterface, QuestionBotImageInterface):
    
    DEFAULT_MODEL = "llama2-uncensored"
    #DEFAULT_MODEL = "falcon"
    #DEFAULT_MODEL = "orca-mini"
    THREADS = 6
    
    def __init__(self, model : str = None) -> None:
        self._server = config("OLLAMA_SERVER")
        self._headers = {}
        
        self._model = model if model is not None else self.DEFAULT_MODEL
        
        self._lazy_download_done = False
        
    
    def _model_available(self, model_name: str):
        response = requests.get(f"{self._server}/api/tags", headers=self._headers)
        response_json = response.json()
        for model in response_json["models"]:
            if model["name"] == model_name or model["name"] == f"{model_name}:latest":
                return True
        return False
    
    def _model_download(self, model_name):
        request = {
            "name": model_name,
            "stream": False
            }
        
        response = requests.post(f"{self._server}/api/pull", headers=self._headers, json=request)
        # TODO: json fails
        response_json = response.json()
        if "error" in response_json: 
            logging.critical(f"Ollama API call error: {response_json['error']}")
            return False
        return True
    
    def _get_num_threads(self):
        return multiprocessing.cpu_count()
        #return self.THREADS
    
    def answer(self, prompt: str):
        if not self._lazy_download_done:
            if not self._model_available(self._model):
                self._model_download(self._model)
            self._lazy_download_done = True
        # TODO: use better threads
        request = {
            "model": self._model,
            "prompt": prompt,
            #"format": "json",
            "stream": False,
            #"raw": True,
            "options": 
                {
                    "num_thread": self._get_num_threads(),
                }
            }

        response = requests.post(f"{self._server}/api/generate", headers=self._headers, json=request)
        response_json = response.json()
        if "error" in response_json: 
            logging.critical(f"Ollama API call error: {response_json['error']}")
            return None
        return {
            'text': response_json['response'], 
            'cost': 0
        }
    
    def answer_image(self, prompt: str, image_path: str):
        if not self._lazy_download_done:
            if not self._model_available(self._model):
                self._model_download(self._model)
            self._lazy_download_done = True
        f = open(image_path, "rb")
        binary_data = f.read()
        f.close()
        base64data = base64.b64encode(binary_data).decode('utf-8')
        # TODO: use better threads
        request = {
            "model": self._model,
            "prompt": prompt,
            #"format": "json",
            "stream": False,
            #"raw": True,
            "options": 
                {
                    "num_thread": self._get_num_threads(),
                }, 
            "images": [base64data]
            }

        response = requests.post(f"{self._server}/api/generate", headers=self._headers, json=request)
        response_json = response.json()
        if "error" in response_json: 
            logging.critical(f"Ollama API call error: {response_json['error']}")
            return None
        return {
            'text': response_json['response'], 
            'cost': 0
        }

class FallbackQuestionbot(QuestionBotInterface):
    """A question bot implementation that tries multiple question bots 
    until one of them succeeds. """

    def __init__(self, bots: List[QuestionBotInterface]) -> None:
        super().__init__()
        self._bots = bots

    def answer(self, prompt: str):
        count = 0
        for bot in self._bots:
            count += 1
            try:
                answer = bot.answer(prompt)
                if answer is None:
                    print(f"Chat bot {count} failed to answer, trying next")
                    continue
                if count > 1:
                    num_question_bots = len(self._bots)
                    answer['text'] += f" ({count}/{num_question_bots})"
                return answer
            except Exception as ex:
                logging.critical(ex, exc_info=True)  # log exception info at CRITICAL log level
        return None
    