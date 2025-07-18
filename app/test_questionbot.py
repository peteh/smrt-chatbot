"""Tests for QuestionBots. """
import unittest
import questionbot
from decouple import config

class QuestionBotTest(unittest.TestCase):
    """Test Cases for Questionbots"""

    def _test_questionbot(self, question_bot: questionbot.QuestionBotInterface):
        # arrange
        prompt = "Tell me the meeting time in the format HH:mm in 24h format from the following text by just \
            stating the answer: We will meet at half past 3 in the afternoon. "

        # act
        answer = question_bot.answer(prompt)

        # assert
        self.assertIsNotNone(answer)
        self.assertGreater(len(answer['text']), 4)
        self.assertIn("15:30", answer['text'])
        self.assertGreaterEqual(answer['cost'], 0)

    def test_openai_api(self):
        # arrange
        question_bot = questionbot.QuestionBotOpenAIAPI(config("OPENAI_APIKEY"))

        # act, assert
        self._test_questionbot(question_bot)
    
    def test_binggppt(self):
        # arrange
        question_bot = questionbot.QuestionBotBingGPT()

        # act, assert
        self._test_questionbot(question_bot)
    
    def test_ollama(self):
        # arrange
        question_bot = questionbot.QuestionBotOllama()

        # act, assert
        self._test_questionbot(question_bot)
    
    def test_bard(self):
        # arrange
        question_bot = questionbot.QuestionBotBard()

        # act, assert
        self._test_questionbot(question_bot)

    def test_flowgpt_gpt35(self):
        # arrange
        question_bot = questionbot.QuestionBotFlowGPT(questionbot.QuestionBotFlowGPT.MODEL_CHATGPT_35)

        # act, assert
        self._test_questionbot(question_bot)

    def test_fallback_questionbot(self):
        # TODO: use simpler mocks for this
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
        question_bot = questionbot.FallbackQuestionbot(bots)

        # act
        answer = question_bot.answer("yolo")

        # assert
        self.assertIsNotNone(answer)
        self.assertIn("text", answer)
        self.assertEqual(answer['text'], "yolo (3/3)")

if __name__ == '__main__':
    unittest.main()
