import openai
import requests
import asyncio
import EdgeGPT
import Bard
import json
from abc import ABC, abstractmethod
from questionbot import QuestionBotInterface

class SummaryInterface(ABC):
    def identifier(self) -> str:
        """
        Identifies the process with a unique name
        """
        pass

    @abstractmethod
    def summarize(self, text: str, language: str) -> dict:
        """Creates a summary for the given text"""
        pass

class OpenAIChatGPTSummary(SummaryInterface):
    # TODO: abstract to a QuestionBot
    def __init__(self, apiKey: str):
        self._apiKey = apiKey
        self._costPerToken = 0.002 / 1000.
    
    def summarize(self, text: str, language: str):
        openai.api_key = self._apiKey
        if language == 'de':
            prompt = "Fasse die wichtigsten Punkte des folgenden Textes in so wenig Stichpunkten zusammen wie möglich, hebe dabei besonders Daten und Zeiten hervor, wenn sie vorhanden sind: %s" % (text)
        else:
            prompt = "Summarize the most important points in the following text in a few bullet points as short as possible, emphasize dates and time if they are present in the text: %s" % (text)
        response = openai.Completion.create(model="text-davinci-003", prompt="Say this is a test", temperature=0, max_tokens=100)
        completion = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}])
        cost = completion['usage']['total_tokens'] * self._costPerToken
        response = completion['choices'][0]['message']['content']
        return {
            'text': response, 
            'cost': cost
        }
    
class ChatGPTSummary(SummaryInterface):
    def summarize(self, text: str, language: str):
        url='http://127.0.0.1:8000/v1/completions'
        headers={'accept': 'application/json', 
                'Content-Type': 'application/json',
                'Authorization': 'Bearer [Your API Key]'
                }
        prompt = "Summarize the most important points in the following text in a few bullet points as short as possible, emphasize dates and time if they are present in the text: %s" % (text)
        data = {
            "model": "text-davinci-003",
            "prompt": prompt,
            "max_tokens": 100,
            "temperature": 1.0,
            }
        response = requests.post(url, json=data, headers=headers, verify=False)
        return response.json()['choices'][0]['text']

class QuestionBotSummary(SummaryInterface):
    def __init__(self, questionBot: QuestionBotInterface):
        self._bot = questionBot

    def summarize(self, text: str, language: str):
        if language == 'de':
            prompt = "Fasse die wichtigsten Punkte des folgenden Textes mit den wichtigsten Stichpunkten und so kurz wie möglich auf Deutsch zusammen, hebe dabei besonders Daten und Zeiten hervor, wenn sie vorhanden sind: \n\n%s" % (text)
        else:
            prompt = "Summarize the most important points in the following text in a few bullet points as short as possible, emphasize dates and time if they are present in the text: \n\n%s" % (text)
        print("======= PROMPT: ==== \n" + prompt)
        
        response = self._bot.answer(prompt=prompt)
        #print(json.dumps(response, indent = 4))
        return response


class BardSummary(SummaryInterface):
    def __init__(self, sessionId):
        self._sessionId = sessionId

    def summarize(self, text: str, language: str):
        bot = Bard.Chatbot(session_id = self._sessionId)
        if language == 'de':
            prompt = "Fasse den folgenden Text zusammen: %s" % (text)
        else:
            prompt = "Summarize the following text in a few important key points: %s" % (text)
        
        print(prompt)
        response = bot.ask(message=prompt)
        text = response['content']
        text = text.strip()
        return {
            'text': text,
            'cost': 0
        }
