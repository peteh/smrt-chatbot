"""Question bot implementations. """
import logging
from abc import ABC, abstractmethod
from typing import List

# bing gpt standard imports
import re

import asyncio
import EdgeGPT.EdgeGPT
import revChatGPT.V1

# openai api questionbot
from openai import OpenAI

class QuestionBotInterface(ABC):
    """Interface for question bots"""

    @abstractmethod
    def answer(self, prompt: str) -> dict:
        """Returns an answer to a prompt based on the underlying bots response"""


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
    