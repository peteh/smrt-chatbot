import unittest
import questionbot
from decouple import config

class QuestionBotTest(unittest.TestCase):
    def _testQuestionbot(self, questionBot: questionbot.QuestionBotInterface):
        # arrange
        prompt = "Tell me the meeting time in the format HH:mm from the following text by just stating the answer: We will meet at half past 3 in the afternoon. "

        # act
        answer = questionBot.answer(prompt)

        # assert
        self.assertIsNotNone(answer)
        self.assertGreater(len(answer['text']), 4)
        self.assertIn("15:30", answer['text'])
        self.assertGreaterEqual(answer['cost'], 0)

    def test_BingGPT(self):
        questionBot = questionbot.QuestionBotBingGPT()
        self._testQuestionbot(questionBot)
    
    def test_QuestionBotRevChatGPT(self):
        questionBot = questionbot.QuestionBotRevChatGPT(cookie = config('CHATGPT_COOKIE'))
        self._testQuestionbot(questionBot)

    def test_QuestionBotOpenAIAPI(self):
        questionBot = questionbot.QuestionBotOpenAIAPI(config("OPENAI_APIKEY"))
        self._testQuestionbot(questionBot) 
    
    def test_FallbackQuestionbot(self):
        # arrange
        class ExceptionQuestionBot(questionbot.QuestionBotInterface):
            def answer(self, prompt: str):
                raise Exception("Epic Fail")
        
        class NoneQuestionBot(questionbot.QuestionBotInterface):
            def answer(self, prompt: str):
                return None
            
        class GoodQuestionBot(questionbot.QuestionBotInterface):
            def answer(self, prompt: str):
                return {
                    "text": prompt,
                    "cost": 0
                }
        bots = [ExceptionQuestionBot(), NoneQuestionBot(), GoodQuestionBot()]
        questionBot = questionbot.FallbackQuestionbot(bots)

        # act
        answer = questionBot.answer("yolo")

        # assert
        self.assertIsNotNone(answer)
        self.assertIn("text", answer)
        self.assertEqual(answer['text'], "yolo (3/3)")

if __name__ == '__main__':
    unittest.main()

