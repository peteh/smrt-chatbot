"""Tests for QuestionBots. """
import unittest
import smrt.bot.tools.question_bot as question_bot
from decouple import config

class QuestionBotTest(unittest.TestCase):
    """Test Cases for Questionbots"""

    def _test_questionbot(self, question_bot: question_bot.QuestionBotInterface):
        # arrange
        prompt = "What make is the car in the image off? "

        # act
        answer = question_bot.answer_image(prompt, "samples/porsche.jpg")

        # assert
        self.assertIsNotNone(answer)
        self.assertIn("Porsche", answer['text'])
        self.assertGreaterEqual(answer['cost'], 0)

    
    def test_ollama(self):
        # arrange
        question_bot = question_bot.QuestionBotOllama("llava")

        # act, assert
        self._test_questionbot(question_bot)


if __name__ == '__main__':
    unittest.main()
