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
import openai

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
        openai.api_key = self._api_key
        completion = openai.ChatCompletion.create(model="gpt-3.5-turbo",
                                                  messages=[{"role": "user",
                                                             "content": prompt}])
        cost = completion['usage']['total_tokens'] * self._cost_per_token
        response = completion['choices'][0]['message']['content']
        return {
            'text': response, 
            'cost': cost
        }

import json
class QuestionBotBingGPT(QuestionBotInterface):
    """Question bot based on Microsoft's Bing search engine chat feature"""

    def __init__(self, cookie_path = "cookie.json") -> None:
        with open(cookie_path, "r", encoding = "utf-8") as cookie_fp:
            self._cookies = json.load(cookie_fp)

    async def _answer(self, prompt):
        bot = await EdgeGPT.EdgeGPT.Chatbot.create(cookies=self._cookies)
        try:
            #response = await bot.ask(prompt=prompt,
            #                         conversation_style=EdgeGPT.EdgeGPT.ConversationStyle.creative,
            #                         wss_link="wss://sydney.bing.com/sydney/ChatHub")
            response = await bot.ask(prompt, conversation_style=EdgeGPT.EdgeGPT.ConversationStyle.creative, simplify_response=True)
            print(json.dumps(response, indent = 4))
            text = response['text']
            first_sentence = text[:text.find(".")+1:]
            text = re.sub(r"\[\^[0-9]+\^\]", "", text)
            if "Bing" in first_sentence:
                # we dropt the first sentence because is Bing introducing itself
                text = text[text.find(".")+1:]
            text = text.strip()
        except Exception as ex:
            logging.critical(ex, exc_info=True)  # log exception info at CRITICAL log level
            return None
        finally:
            if bot is not None:
                await bot.close()

        return {
            'text': text,
            'cost': 0
        }

    def answer(self, prompt: str):
        return asyncio.run(self._answer(prompt))

class QuestionBotRevChatGPT(QuestionBotInterface):
    """A question bot based on revChatGPT"""
    def __init__(self, cookie):
        self._cookie = cookie

    def answer(self, prompt: str):
        try:
            config = {
                "access_token": self._cookie
                }

            chatbot = revChatGPT.V1.Chatbot(config)

            response = {}
            for data in chatbot.ask(
                prompt,
            ):
                response = data
            # delete the previous question again
            chatbot.delete_conversation(response["conversation_id"])
            return {
                'text': response['message'], 
                'cost': 0
            }
        except Exception as ex:
            logging.critical(ex, exc_info=True)  # log exception info at CRITICAL log level
            return None

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
    