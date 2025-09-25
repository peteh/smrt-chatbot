"""Tests for QuestionBots. """
import unittest
import smrt.bot.tools.question_bot as question_bot
import smrt.bot.tools.summary as summary
from decouple import config

class QuestionBotTest(unittest.TestCase):
    """Test Cases for Questionbots"""

    def _test_questionbot(self, question_bot: question_bot.QuestionBotInterface):
        # arrange
        summary_bot = question_bot.QuestionBotSolar()
        text = """Also ich habe gestern Alex getroffen. Zwickstraße 30. Also in Lippenhausen will er komplett 30
Abzonen machen. Also von unten, von Tischnass bis hoch zu uns oder durchs ganze Kaffee eigentlich.
Aber das kann er halt nur machen, weil es halt nur gemeine Straße ist. Das in Hammersheim war
ja schon öfters der Fall. Es war ja auch letztes Jahr Begehung wieder, weil wir uns ja beschwert haben,
weil die so schnell fahren und schießen nicht. Keine Ahnung. Soll ich jetzt sagen. Auf jeden
Fall ist es gar nicht so einfach da was auf die Straße zu machen. Da muss man einen Kreis
fragen bzw. einen Ballmann sagen und der muss das in die Wiege leiten. Das kann dann
wieder etwas dauern. Einfach so ein Geschwindigkeitsmesser hinstellen auf
Kreisstraße ist auch schwierig. Muss man auch eine Genehmigung holen. Wegen Behinderungs-Straßesverkehrsablenkung schießen dort keine Ahnung.
Ich habe jetzt vergessen zu fragen, ob man Schilder aufhängen kann. Aber ich würde
wahrscheinlich auch nicht wissen. Zum Beispiel spielende Kinder. Da sind ja die Lampen, die
fahren in Masten. Ob man da zum Beispiel ein Schildchen machen könnte. Spielende Kinder.
Eigentlich ist es ja Gemeindeland oder ein Dingsbums. Das man halt dann aufmerksam macht,
weil viele wissen ja nicht einmal. Ich weiß gar nicht welche Mutti das mir noch nicht gesagt hat.
Am Anfang wo sie da reingekommen sind. Kindergarten. Da ist es zigtausendmal
vorbeigefahren, weil ein Kindergarten nicht gefunden hat. Weil es halt wirklich nicht viel aussteht.
Muss man mit dem Ball noch mal reden. Auf jeden Fall, wenn man was auf die Straße machen will,
muss man es im Kreis beantragen."""
        summarizer = summary.QuestionBotSummary(summary_bot)

        # act
        answer = question_bot.summarize(text)

        # assert
        print(answer)

    def test_openai_api(self):
        # arrange
        question_bot = question_bot.QuestionBotOpenAIAPI(config("OPENAI_APIKEY"))

        # act, assert
        self._test_questionbot(question_bot)
    
    def test_binggppt(self):
        # arrange
        question_bot = question_bot.QuestionBotBingGPT()

        # act, assert
        self._test_questionbot(question_bot)
    
    def test_ollama(self):
        # arrange
        question_bot = question_bot.QuestionBotOllama()

        # act, assert
        self._test_questionbot(question_bot)

    def test_fallback_questionbot(self):
        # TODO: use simpler mocks for this
        # arrange
        class ExceptionQuestionBot(question_bot.QuestionBotInterface):
            def answer(self, prompt: str):
                raise Exception("Epic Fail")

        class NoneQuestionBot(question_bot.QuestionBotInterface):
            def answer(self, prompt: str):
                return None

        class GoodQuestionBot(question_bot.QuestionBotInterface):
            def answer(self, prompt: str):
                return {
                    "text": prompt,
                    "cost": 0
                }
        bots = [ExceptionQuestionBot(), NoneQuestionBot(), GoodQuestionBot()]
        question_bot = question_bot.FallbackQuestionbot(bots)

        # act
        answer = question_bot.answer("yolo")

        # assert
        self.assertIsNotNone(answer)
        self.assertIn("text", answer)
        self.assertEqual(answer['text'], "yolo (3/3)")

if __name__ == '__main__':
    unittest.main()
