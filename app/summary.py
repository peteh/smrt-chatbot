"""Implemenations of text summarizers. """
from abc import ABC, abstractmethod
from questionbot import QuestionBotInterface

class SummaryInterface(ABC):
    """Summarizer Interface for different implementations. """
    def identifier(self) -> str:
        """
        Identifies the process with a unique name
        """

    @abstractmethod
    def summarize(self, text: str, language: str) -> dict:
        """Creates a summary for the given text"""

class QuestionBotSummary(SummaryInterface):
    """A summarizer based on generic question bots. """
    def __init__(self, question_bot: QuestionBotInterface):
        self._bot = question_bot

    def summarize(self, text: str, language: str) -> dict:
        if language == 'de':
            prompt = \
f"Fasse die wichtigsten Punkte des folgenden Textes mit den \
wichtigsten Stichpunkten und so kurz wie möglich in Deutsch zusammen, \
hebe dabei besonders Daten und Zeiten hervor, wenn sie vorhanden sind.\n\n\
Text:\n{text}\nZusammenfassung (Deutsch):\n"
        else:
            prompt = \
f"Summarize the most important points in the following text in a few \
bullet points as short as possible, emphasize dates and time if they are \
present in the text. \n\nText:\n{text}\nZusammenfassung (English):\n"
        print("======= PROMPT: ==== \n" + prompt)

        response = self._bot.answer(prompt=prompt)
        return response
