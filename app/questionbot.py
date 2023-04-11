from abc import ABC, abstractmethod

import asyncio
import EdgeGPT
import json

class QuestionBotInterface(ABC):
    @abstractmethod
    def answer(self, prompt: str):
        pass

class QuestionBotBingGPT(QuestionBotInterface):
    async def _answer(self, prompt):
        try:
            bot = EdgeGPT.Chatbot(cookiePath = "cookie.json")
            
            response = await bot.ask(prompt=prompt, conversation_style=EdgeGPT.ConversationStyle.creative, wss_link="wss://sydney.bing.com/sydney/ChatHub")
            print(json.dumps(response, indent = 4))
            text = response['item']['messages'][1]['text']
            
            text = text[text.find(".")+1:].strip()
            # we dropt the first sentence because it's Bing introducing itself. 

            await bot.close()
        except Exception as ex:
            text = "Prompt failed with exception: %s" % (ex)
        return {
            'text': text,
            'cost': 0
        }
    
    def answer(self, prompt: str):
        return asyncio.run(self.answer(prompt))
        