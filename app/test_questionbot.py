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
    
    def test_QuestionBotChatGPTOpenAI(self):
        questionBot = questionbot.QuestionBotChatGPTOpenAI(cookie = config('CHATGPT_COOKIE'))
        self._testQuestionbot(questionBot)

if __name__ == '__main__':
    unittest.main()

