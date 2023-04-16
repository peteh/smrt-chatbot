from abc import ABC, abstractmethod

import asyncio
import EdgeGPT
from revChatGPT.V1 import Chatbot

class QuestionBotInterface(ABC):
    @abstractmethod
    def answer(self, prompt: str):
        pass

class QuestionBotBingGPT(QuestionBotInterface):
    def __init__(self, cookePath = "cookie.json") -> None:
        self._cookePath = cookePath

    async def _answer(self, prompt):
        bot = EdgeGPT.Chatbot(cookiePath=self._cookePath)
        try:
            response = await bot.ask(prompt=prompt, conversation_style=EdgeGPT.ConversationStyle.creative, wss_link="wss://sydney.bing.com/sydney/ChatHub")
            #print(json.dumps(response, indent = 4))
            text = response['item']['messages'][1]['text']
            print(text)
            firstSentence = text[text.find(".")+1:]
            if "Bing" in firstSentence:
                # we dropt the first sentence because is Bing introducing itself
                text = text[text.find(".")+1:].strip()
        except Exception as ex:
            text = "Prompt failed with exception: %s" % (ex)
            raise ex
        finally:
            await bot.close()
        
        return {
            'text': text,
            'cost': 0
        }
    
    def answer(self, prompt: str):
        return asyncio.run(self._answer(prompt))

class QuestionBotChatGPTOpenAI(QuestionBotInterface):
    def __init__(self, cookie):
        self._cookie = cookie

    def answer(self, prompt: str):
        config = {
            "access_token": self._cookie
            }
        
        chatbot = Chatbot(config)

        message = ""
        for data in chatbot.ask(
            prompt,
        ):
            message = data["message"]
        return {
            'text': message, 
            'cost': 0
        }