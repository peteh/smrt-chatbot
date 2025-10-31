"""Implemenations of different pipelines to process messages. """
import logging
import re
from typing import List

import tempfile
import os

from smrt.bot.tools.summary import SummaryInterface
from smrt.bot.messenger import MessengerInterface
from smrt.bot.tools.question_bot import QuestionBotInterface, QuestionBotImageInterface
import smrt.bot.tools.texttoimage as texttoimage



# article summary pipeline
import trafilatura
from smrt.bot.pipeline import PipelineInterface, PipelineHelper, AbstractPipeline
from smrt.bot.tools import YoutubeExtract


class GrammarPipeline(AbstractPipeline):
    """A pipeline that checks incoming messages for grammar 
    and spelling mistakes and fixes them. """

    GRAMMAR_COMMAND = "grammar"
    GRAMMATIK_COMMAND = "grammatik"

    def __init__(self, question_bot: QuestionBotInterface) -> None:
        super().__init__(None, None)
        self._question_bot = question_bot

    def matches(self, messenger: MessengerInterface, message: dict):
        command = PipelineHelper.extract_command(messenger.get_message_text(message))
        return self.GRAMMAR_COMMAND in command\
            or self.GRAMMATIK_COMMAND in command

    def process(self, messenger: MessengerInterface, message: dict):
        (command, _, text) = PipelineHelper.extract_command_full(
            messenger.get_message_text(message))
        message_text = messenger.get_message_text(message)
        if self.GRAMMAR_COMMAND in command:
            text = message_text[len(self.GRAMMAR_COMMAND)+1:]
            prompt = \
f"Enhance the quality of the text below. Grammar, punctuation, spelling, \
word choice and style should be examined in detail. Additionally, the style and \
tone must be improved to ensure the writing is polished, error-free, and \
easy to read: \n\n{text}"

        elif self.GRAMMATIK_COMMAND in command:
            text = message_text[len(self.GRAMMATIK_COMMAND)+1:]
            prompt = \
f"Verbessere die Qualität des folgenden Textes. Grammatik, Interpunktion, \
Rechtschreibung, Wortwahl und Stil soll besonders beachtet werden. Außerdem \
soll Stil und Ton so verbessert werden, dass einen eleganter, fehlerfreier \
und einfach zu lesender Text entsteht: \n\n{text}"
        else:
            # skip
            return

        messenger.mark_in_progress_0(message)
        answer = self._question_bot.answer(prompt)
        if answer is None:
            messenger.mark_in_progress_fail(message)
            return
        answer_text = answer['text']
        messenger.reply_message(message, answer_text)
        messenger.mark_in_progress_done(message)

    def get_help_text(self) -> str:
        return \
"""*Grammar*
_#grammatik German Text_ corrects German language
_#grammar English Text_ corrects English language"""


class UndeletePipeline(AbstractPipeline):
    """A pipe that stores the last few messages and can recover deleted. """
    
    UNDELETE_COMMAND = "#undelete"

    def __init__(self) -> None:
        super().__init__(None, None)

    def matches(self, messenger: MessengerInterface, message: dict):
        if messenger.is_self_message(message):
            command = PipelineHelper.extract_command(messenger.get_message_text(message))
            return self.UNDELETE_COMMAND in command
        else: 
            # we need to store it into our database/buffer
            return True

    def process(self, messenger: MessengerInterface, message: dict):
        if messenger.is_self_message(message):
            (_, _, count) = PipelineHelper.extract_command_full(messenger.get_message_text(message))
            # TODO: do stuff with the command
            return True
        else: 
            # TODO store into buffer
            return True

    def get_help_text(self) -> str:
        return ""

import requests
import langid
class URLSummaryPipeline(AbstractPipeline):
    """Summarizes an article or a youtube video. """

    MAX_TRANSCRIPT_LENGTH = 20000

    def __init__(self, summarizer: SummaryInterface, chat_id_whitelist: List[str] = None, chat_id_blacklist: List[str] = None):
        super().__init__(chat_id_whitelist, chat_id_blacklist)
        self._summarizer = summarizer
        self._link_regex = re.compile(r'((https?):((//)|(\\\\))+([\w\d:#@%/;$()~_?\+-=\\\.&](#!)?)*)',
                                      re.DOTALL)
        self._language = "en"

    def _extract_urls(self, text: str) -> List[str]:
        links = []
        for extract in re.findall(self._link_regex, text):
            links.append(extract[0])
        return links

    def matches(self, messenger: MessengerInterface, message: dict):
        message_text = messenger.get_message_text(message)
        links = self._extract_urls(message_text)
        return len(links) > 0
    
    def use_google_bot(self, url):
        no_google_urls = ["reddit.com"]
        for no_google_url in no_google_urls:
            if no_google_url in url:
                return False
        return True

    def _process_article(self, link: str):
        config = trafilatura.settings.use_config()
        # pretend we are google bot, so we don't get annoying cookie shit
        config.set("DEFAULT", "EXTRACTION_TIMEOUT", "0")
        headers = {}
        if self.use_google_bot(link):
            headers={'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'}
        session = requests.Session()
        response = session.get(link, headers=headers)

        # extract information from HTML
        extracted_text = trafilatura.extract(response.content, config=config)
        lang, conf = langid.classify(extracted_text)
        summarized_text = self._summarizer.summarize(extracted_text, "de" if lang == "de" else self._language)['text']
        print("==EXTRACTED==")
        print(extracted_text)
        print("==SUMMARY==")
        print(summarized_text)
        return summarized_text

    def _process_youtube(self, link):
        processor = YoutubeExtract(link)
        text = processor.get_script()
        text_length = len(text)
        print(f"Length of youtube transcript: {text_length}")
        # reducing to the last 10k letters to limit input for summary
        # TODO: maybe do in parts...
        if len(text) > self.MAX_TRANSCRIPT_LENGTH:
            print(f"Transcript exceeding {self.MAX_TRANSCRIPT_LENGTH} letters, reducing...")
        text = text[-self.MAX_TRANSCRIPT_LENGTH:]
        lang, conf = langid.classify(text)
        summarized_text = self._summarizer.summarize(text, "de" if lang == "de" else self._language)['text']
        return summarized_text

    def process(self, messenger: MessengerInterface, message: dict):
        message_text = messenger.get_message_text(message)
        messenger.mark_in_progress_0(message)
        links = self._extract_urls(message_text)
        total_summary = ""

        try:
            for link in links:
                if YoutubeExtract.is_youtube_link(link):
                    summarized_text = self._process_youtube(link)
                else:
                    summarized_text = self._process_article(link)
                summary_part = f"{link} : \n{summarized_text}\n"
                total_summary += summary_part
        except Exception as ex:
            logging.critical(ex, exc_info=True)
            messenger.mark_in_progress_fail(message)
            return
        messenger.reply_message(message, total_summary)
        messenger.mark_in_progress_done(message)
    def get_help_text(self) -> str:
        return \
"""*Article and Youtube Video Summary*
Sending a link or youtube video to the bot will generate a summary"""

class ImageGenerationPipeline(AbstractPipeline):
    """Pipe to turn prompts into images. """
    IMAGE_COMMAND = "image"

    def __init__(self, image_api: texttoimage.ImagePromptInterface):
        super().__init__(None, None)
        self._image_api = image_api

    def matches(self, messenger: MessengerInterface, message: dict):
        command = PipelineHelper.extract_command(messenger.get_message_text(message))
        return self.IMAGE_COMMAND in command

    def process(self, messenger: MessengerInterface, message: dict):
        (_, _, prompt) = PipelineHelper.extract_command_full(messenger.get_message_text(message))
        messenger.mark_in_progress_0(message)
        try:
            images = self._image_api.process(prompt)
            if images is None:
                messenger.mark_in_progress_fail(message)
                return

            for image in images:
                (file_name, binary) = image
                if messenger.is_group_message(message):
                    messenger.send_image_to_group(message, file_name, binary, prompt)
                else:
                    messenger.send_image_to_individual(message, file_name, binary, prompt)
        except Exception as ex:
            logging.critical(ex, exc_info=True)  # log exception info at CRITICAL log level
            messenger.mark_in_progress_fail(message)
            return

        messenger.mark_in_progress_done(message)

    def get_help_text(self) -> str:
        return \
"""*Image Generation*
_#image prompt_ Generates images based on the given prompt"""

class ImagePromptPipeline(AbstractPipeline):
    
    """Pipe to turn prompts into images. """
    COMMAND = "llava"

    def __init__(self, image_api: QuestionBotImageInterface):
        super().__init__(None, None)
        self._image_api = image_api

    def matches(self, messenger: MessengerInterface, message: dict):
        command = PipelineHelper.extract_command(messenger.get_message_text(message))
        return self.COMMAND in command and messenger.has_image_data(message) 

    def process(self, messenger: MessengerInterface, message: dict):
        (_, _, prompt) = PipelineHelper.extract_command_full(messenger.get_message_text(message))
        messenger.mark_in_progress_0(message)
        try:
            content_type, binary_data = messenger.download_media(message)
            with tempfile.TemporaryDirectory() as tmp:
            # TODO build this with generic file names
                image_file_path = os.path.join(tmp, 'image')
                f = open(image_file_path, "wb")
                f.write(binary_data)
                f.close()
                
                response = self._image_api.answer_image(prompt, image_file_path)
                response_msg = response.get("text")
                messenger.reply_message(message, response_msg)

        except Exception as ex:
            logging.critical(ex, exc_info=True)  # log exception info at CRITICAL log level
            messenger.mark_in_progress_fail(message)
            return

        messenger.mark_in_progress_done(message)

    def get_help_text(self) -> str:
        return \
"""*Image Processing*
_#llava prompt_ Answers question to a given image"""

class TinderPipeline(AbstractPipeline):
    """A pipeline to write answers to tinder messages. """
    TINDER_COMMAND = "tinder"

    def __init__(self, question_bot: QuestionBotInterface, chat_id_whitelist: List[str] = None, chat_id_blacklist: List[str] = None) -> None:
        super().__init__(chat_id_whitelist, chat_id_blacklist)
        self._question_bot = question_bot

    def matches(self, messenger: MessengerInterface, message: dict):
        command = PipelineHelper.extract_command(messenger.get_message_text(message))
        return self.TINDER_COMMAND in command

    def process(self, messenger: MessengerInterface, message: dict):
        (_, context, tinder_message) = PipelineHelper.extract_command_full(
            messenger.get_message_text(message))
        messenger.mark_in_progress_0(message)
        lang, conf = langid.classify(tinder_message)
        
        if lang == "de":
            prompt = f"Schreibe eine kurze, lockere, lustige Anwort auf folgende Nachricht von einem Mädchen: \n{tinder_message}"
            if context != "":
                prompt = f"Schreibe eine kurze, lockere, lustige Anwort auf folgende Nachricht von einem Mädchen (Kontext: {context}): \n{tinder_message}"
        else:
            prompt = f"Write a short, casual, funny response to the following message from a girl: \n{tinder_message}"
            if context != "":
                prompt = f"Write a short, casual, funny response to the following message from a girl. (Context: {context}): \n{tinder_message}"
        
        answer = self._question_bot.answer(prompt)
        if answer is None:
            messenger.mark_in_progress_fail(message)
            return

        response_text = answer['text']
        messenger.reply_message(message, response_text)

        messenger.mark_in_progress_done(message)

    def get_help_text(self) -> str:
        return \
f"""*Tinder Help*
_#{self.TINDER_COMMAND}[(Context)] message_ Proposes a response to a message from a girl. Additional context can be given to adapt the message. """
