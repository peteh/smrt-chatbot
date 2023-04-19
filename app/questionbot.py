from abc import ABC, abstractmethod

import asyncio
import EdgeGPT
import revChatGPT.V1
import logging

class QuestionBotInterface(ABC):
    @abstractmethod
    def answer(self, prompt: str):
        pass

import openai
class QuestionBotOpenAIAPI(QuestionBotInterface):
    def __init__(self, apiKey) -> None:
        super().__init__()
        self._apiKey = apiKey
        self._costPerToken = 0.002 / 1000.
        
    def answer(self, prompt: str):
        openai.api_key = self._apiKey
        #response = openai.Completion.create(model="text-davinci-003", prompt="Say this is a test", temperature=0, max_tokens=100)
        completion = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}])
        cost = completion['usage']['total_tokens'] * self._costPerToken
        response = completion['choices'][0]['message']['content']
        return {
            'text': response, 
            'cost': cost
        }
        
import re
class QuestionBotBingGPT(QuestionBotInterface):
    def __init__(self, cookePath = "cookie.json") -> None:
        self._cookePath = cookePath

    async def _answer(self, prompt):
        bot = EdgeGPT.Chatbot(cookiePath=self._cookePath)
        try:
            response = await bot.ask(prompt=prompt, conversation_style=EdgeGPT.ConversationStyle.creative, wss_link="wss://sydney.bing.com/sydney/ChatHub")
            #print(json.dumps(response, indent = 4))
            text = response['item']['messages'][1]['text']
            firstSentence = text[:text.find(".")+1:]
            text = re.sub("\[\^[0-9]+\^\]", "", text)
            if "Bing" in firstSentence:
                # we dropt the first sentence because is Bing introducing itself
                text = text[text.find(".")+1:]
            text = text.strip()
        except Exception as e:
                logging.critical(e, exc_info=True)  # log exception info at CRITICAL log level
                return None
        finally:
            await bot.close()
        
        return {
            'text': text,
            'cost': 0
        }
    
    def answer(self, prompt: str):
        return asyncio.run(self._answer(prompt))

class QuestionBotRevChatGPT(QuestionBotInterface):
    def __init__(self, cookie):
        self._cookie = cookie

    def answer(self, prompt: str):
        try:
            config = {
                "access_token": self._cookie
                }
            
            chatbot = revChatGPT.V1.Chatbot(config)

            message = ""
            for data in chatbot.ask(
                prompt,
            ):
                message = data["message"]
            # delete the previous question again
            chatbot.delete_conversation(data["conversation_id"])
            return {
                'text': message, 
                'cost': 0
            }
        except Exception as e:
            logging.critical(e, exc_info=True)  # log exception info at CRITICAL log level
            return None

import typing
class FallbackQuestionbot(QuestionBotInterface):
    def __init__(self, bots: typing.List[QuestionBotInterface]) -> None:
        super().__init__()
        self._bots = bots
        
    def answer(self, prompt: str):
        count = 0
        for bot in self._bots:
            count += 1
            try:
                answer = bot.answer(prompt)
                if answer is not None:
                    if count > 1:
                        answer['text'] += " (%d/%d)" % (count, len(self._bots))
                    return answer
            except Exception as e:
                logging.critical(e, exc_info=True)  # log exception info at CRITICAL log level
        return None
    