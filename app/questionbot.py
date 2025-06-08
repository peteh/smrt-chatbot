"""Question bot implementations. """
import logging
from abc import ABC, abstractmethod
from typing import List
from enum import Enum


import base64
import multiprocessing

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
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}"
        }

        data = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": prompt}]
        }

        response = requests.post(url, headers=headers, json=data)
        if response.status_code != 200:
            logging.error(f"Error: {response.status_code}, {response.text}")
            return None

        completion = response.json()
        print(completion)
        usage = completion.get("usage")
        cost = usage.get("total_tokens") * self._cost_per_token
        response = completion.get("choices")[0].get("message").get("content")
        print(response)
        return {
            'text': response, 
            'cost': cost
        }
        

class ChatRole(Enum):
    SYSTEM = 1
    ASSISTANT = 2
    USER = 3

class ChatHistoryEntry:
    
    ROLE_ASSISTANT = "assistant"
    ROLE_USER = "user"
    ROLE_SYSTEM = "system"
    
    def __init__(self, role: ChatRole, message: str):
        # TODO: somehow integrate chat history
        pass
        

import json
class QuestionBotFlowGPT(QuestionBotInterface):
    MODEL_CHATGPT_35 = "model-gpt-3.5-turbo"
    
    def __init__(self, model = MODEL_CHATGPT_35) -> None:
        self._model = model

    def answer(self, prompt: str):
        url = "https://backend-k8s.flowgpt.com/v2/chat-anonymous"

        headers = {
            "Authorization": "Bearer null",
            "Content-Type": "application/json",
            "Referer": "https://flowgpt.com/",
            "Sec-Ch-Ua": '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            #"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0",
        }

        payload = {
            "model": "gpt-3.5-turbo",
            "nsfw": False,
            "question": prompt,
            "history": [
                {
                    "role": "assistant",
                    "content": "Hello there 😃, I am ChatGPT. How can I help you today?"
                }
            ],
            "system": "You are help assitant. Follow the user's instructions carefully. Respond using markdown",
            "temperature": 0.7,
            "promptId": self._model,
            "documentIds": [],
            "chatFileDocumentIds": [],
            "generateImage": False,
            "generateAudio": False
        }
        response = requests.post(url, headers=headers, json=payload)
        print(response.text)
        split = response.text.split("\n\n")
        print("Response status code:", response.status_code)

        response_text = ""
        for split_str in split:
            split_str_trimmed = split_str.strip()
            if split_str_trimmed != "":
                json_event = json.loads(split_str)
                if json_event.get("event") == "text":
                    part = json_event.get("data").replace("\n'n", "\n")
                    response_text += part

        if response_text == "Insufficient credit":
            raise ValueError("No credit for prompts")

        return {
            'text': response_text,
            'cost': 0
        }


import requests
class QuestionBotOllama(QuestionBotInterface, QuestionBotImageInterface):
    
    DEFAULT_MODEL = "llama2-uncensored"
    THREADS = 6

    def __init__(self, ollama_host: str, model : str = None, system_message = None) -> None:
        self._ollama_host = ollama_host
        self._headers = {}
        
        self._model = model if model is not None else self.DEFAULT_MODEL
        self._system_message = system_message
        self._lazy_download_done = False
    
    def _model_available(self, model_name: str):
        response = requests.get(f"{self._ollama_host}/api/tags", headers=self._headers)
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
        
        response = requests.post(f"{self._ollama_host}/api/pull", headers=self._headers, json=request)
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
        
        if self._system_message is not None: 
            request["system"] = self._system_message

        response = requests.post(f"{self._ollama_host}/api/generate", headers=self._headers, json=request)
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

        response = requests.post(f"{self._ollama_host}/api/generate", headers=self._headers, json=request)
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
                logging.critical(ex, exc_info=True)
        return None
