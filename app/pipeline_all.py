"""Implemenations of different pipelines to process messages. """
import time
import logging
import re
from typing import List

import tempfile
import os

from summary import SummaryInterface
from transcript import TranscriptInterface
from messenger import MessengerInterface
from questionbot import QuestionBotInterface, QuestionBotImageInterface
import texttoimage
import utils


# article summary pipeline
import trafilatura
from db import Database
from pipeline import PipelineInterface, PipelineHelper
import youtubeextract


class GrammarPipeline(PipelineInterface):
    """A pipeline that checks incoming messages for grammar 
    and spelling mistakes and fixes them. """

    GRAMMAR_COMMAND = "grammar"
    GRAMMATIK_COMMAND = "grammatik"

    def __init__(self, question_bot: QuestionBotInterface) -> None:
        super().__init__()
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


class UndeletePipeline(PipelineInterface):
    """A pipe that stores the last few messages and can recover deleted. """
    
    UNDELETE_COMMAND = "#undelete"

    def __init__(self) -> None:
        pass

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

class VoiceMessagePipeline(PipelineInterface):
    """A pipe that converts audio messages to text and summarizes them. """
    def __init__(self, transcriber: TranscriptInterface,
                 summarizer: SummaryInterface,
                 min_words_for_summary: int, chat_id_blacklist: List[str] = None):
        self._transcriber = transcriber
        self._summarizer = summarizer
        self._min_words_for_summary = min_words_for_summary
        self._store_files = False
        self._chat_id_blacklist = chat_id_blacklist


    def matches(self, messenger: MessengerInterface, message: dict):
        if not messenger.has_audio_data(message):
            return False
        if self._chat_id_blacklist is not None and messenger.get_chat_id(message) in self._chat_id_blacklist:
            return False
        return True

    def process(self, messenger: MessengerInterface, message: dict):
        try:
            print("Processing in Voice Pipeline")
            debug = {}
            messenger.mark_in_progress_0(message)

            (_, decoded) = messenger.download_media(message)
            if self._store_files:
                with open('out.opus', 'wb') as output_file:
                    output_file.write(decoded)

            start = time.time()
            transcript = self._transcriber.transcribe(decoded)
            end = time.time()
            debug['transcript_time'] = end - start

            transcript_text = transcript['text']
            words = transcript['words']
            language = transcript['language']

            response_message = f"Transcribed: \n{transcript_text}"
            messenger.reply_message(message, response_message)

            debug['transcript_language'] = language
            debug['transcript_language_probability'] = transcript['language_probability']
            debug['transcript_words'] = transcript['words']
            debug['transcript_cost'] = transcript['cost']
            if words > self._min_words_for_summary and self._summarizer is not None:
                messenger.mark_in_progress_50(message)

                start = time.time()
                summary = self._summarizer.summarize(transcript_text, language)
                end = time.time()
                debug['summary_time'] = end - start

                summary_text = summary['text']
                debug['summary_cost'] = summary['cost']
                messenger.reply_message(message, f"Summary: \n{summary_text}")

            messenger.mark_in_progress_done(message)
            if utils.is_debug():
                debug_text = "Debug: \n"
                for debug_key, debug_value in debug.items():
                    debug_text += debug_key + ": " + str(debug_value) + "\n"
                debug_text = debug_text.strip()
                messenger.reply_message(message, debug_text)
        except Exception as ex:
            logging.critical(ex, exc_info=True)
            messenger.mark_in_progress_fail(message)
            return

    def get_help_text(self) -> str:
        return \
"""*Voice Message Transcription*
Forward voice messages to the bot to transcribe them. """

# TODO split into message storage pipeline and command pipeline
class GroupMessageQuestionPipeline(PipelineInterface):
    """Allows to summarize and ask questions in a group conversation. """
    QUESTION_COMMAND = "#question"
    SUMMARY_COMMAND = "#summary"

    def __init__(self, database: Database,
                 summarizer: SummaryInterface,
                 question_bot: QuestionBotInterface):
        self._database = database
        self._summarizer = summarizer
        self._question_bot = question_bot

    def matches(self, messenger: MessengerInterface, message: dict):
        # TODO: abstract chat type
        return messenger.is_group_message(message) and messenger.get_message_text(message) != ""

    def _get_chat_text(self, identifier, max_message_count):
        chat_text = ""
        rows = self._database.get_group_messages(identifier, max_message_count)
        actual_message_count = 0
        for row in rows:
            chat_text += f"{row['sender']}: {row['message']}\n"
            actual_message_count += 1
        return (chat_text, actual_message_count)

    def _process_question_command(self, messenger: MessengerInterface, message: dict):
        message_text = messenger.get_message_text(message)
        messenger.mark_in_progress_0(message)
        question = message_text[len(self.QUESTION_COMMAND)+1:]
        print(f"Question: {question}")
        # TODO: make number configurable
        chat_id = messenger.get_chat_id(message)
        (chat_text, _) = self._get_chat_text(chat_id, 100)
        print(chat_text)
        prompt = \
f"Der folgende Text beinhaltet eine Konversation mehrere Individuen, \
beantworte folgende Frage zu dieser Konversation: {question}\n\nText:\n{chat_text}"
        answer = self._question_bot.answer(prompt)
        answer_text = answer['text']
        print(f"Answer: {answer_text}")
        messenger.send_message_to_group(message, answer_text)
        messenger.mark_in_progress_done(message)

    def _process_summary_command(self, messenger: MessengerInterface, message: dict):
        debug = {}
        message_text = messenger.get_message_text(message)
        chat_id = messenger.get_chat_id(message)
        messenger.mark_in_progress_0(message)
        # TODO: put to configuration
        max_message_count = 20
        command = message_text.split(" ")
        if len(command) > 1:
            max_message_count = int(command[1])

        (chat_text, actual_message_count) = self._get_chat_text(chat_id,
                                                                max_message_count)

        start = time.time()
        summary = self._summarizer.summarize(chat_text, 'de')
        end = time.time()

        debug['summmary_input'] = chat_text
        debug['summmary_maxMessages'] = max_message_count
        debug['summmary_actualMessages'] = actual_message_count
        debug['summary_time'] = end - start
        debug['summary_cost'] = summary['cost']

        summary_text = f"Summary (last {actual_message_count} messages)\n{summary['text']}"
        messenger.send_message_to_group(message, summary_text)
        messenger.mark_in_progress_done(message)
        if utils.is_debug():
            debug_text = "Debug: \n"
            for debug_key, debug_value in debug.items():
                debug_text += debug_key + ": " + str(debug_value) + "\n"
            debug_text = debug_text.strip()
            messenger.send_message_to_group(message, debug_text)

    def process(self, messenger: MessengerInterface, message: dict):
        # TODO: abstract this
        push_name = messenger.get_sender_name(message)
        message_text = messenger.get_message_text(message)
        # TODO: force messenger to make it unique or do we add meta information to make it unique here
        # e.g. numbers are not unique as identifiers in different messengers
        chat_id = messenger.get_chat_id(message)

        if message_text.startswith(self.QUESTION_COMMAND):
            self._process_question_command(messenger, message)

        elif message_text.startswith(self.SUMMARY_COMMAND):
            self._process_summary_command(messenger, message)
        else:
            # TODO: filter messages with command
            self._database.add_group_message(chat_id, push_name, message_text)

    def get_help_text(self) -> str:
        return \
"""*Group Summary*
_#summary [num]_ Summarizes the last _num_ messages
_#question Question?_ answers questions to the last messages in the group"""

import requests
import langid
class ArticleSummaryPipeline(PipelineInterface):
    """Summarizes an article or a youtube video. """

    MAX_TRANSCRIPT_LENGTH = 20000

    def __init__(self, summarizer: SummaryInterface):
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
        processor = youtubeextract.YoutubeExtract(link)
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
                if youtubeextract.YoutubeExtract.is_youtube_link(link):
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

class ImageGenerationPipeline(PipelineInterface):
    """Pipe to turn prompts into images. """
    IMAGE_COMMAND = "image"

    def __init__(self, image_api: texttoimage.ImagePromptInterface):
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

class ImagePromptPipeline(PipelineInterface):
    """Pipe to turn prompts into images. """
    COMMAND = "llava"

    def __init__(self, image_api: QuestionBotImageInterface):
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

class TinderPipeline(PipelineInterface):
    """A pipeline to write answers to tinder messages. """
    TINDER_COMMAND = "tinder"

    def __init__(self, question_bot: QuestionBotInterface) -> None:
        super().__init__()
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
"""*Tinder Help*
_#tinder[(Context)] message_ Proposes a response to a message from a girl. Additional context can be given to adapt the message. """



class TalkPipeline(PipelineInterface):
    
    def __init__(self, question_bot: QuestionBotInterface) -> None:
        self._question_bot = question_bot
        self._pipelines = []
    
    def set_pipelines(self, pipelines: List[PipelineInterface]):
        self._pipelines = pipelines
    
    def matches(self, messenger: MessengerInterface, message: dict) -> bool:
        text = messenger.get_message_text(message)
        return len(text) > 0 and text[0] != "#" \
            and (not messenger.is_group_message(message) or messenger.is_bot_mentioned(message)) \

    def process(self, messenger: MessengerInterface, message: dict) -> None:
        system_message = "Your name is Echo, an AI assistant for chat messages. Messages with # as a prefix are used as commands. "
        commands_text = ""
        for pipe in self._pipelines:
            help_text = pipe.get_help_text()
            if help_text is not None and  len(help_text) > 0:
                commands_text += f"\n{help_text}"
        user_prompt = messenger.get_message_text(message)
        prompt = f"{system_message}\nYour commands are: {commands_text}\n\nAnswer this prompt: {user_prompt}"
        try: 
            messenger.mark_in_progress_0(message)
            answer = self._question_bot.answer(prompt)
            messenger.mark_in_progress_done(message)
            messenger.reply_message(message, answer.get("text"))
        except Exception as ex:
            logging.critical(ex, exc_info=True)
            messenger.mark_in_progress_fail(message)
            return
    
    def get_help_text(self) -> str:
        return None

class GptPipeline(PipelineInterface):
    """A pipeline to talk to gpt models. """
    GPT_COMMAND = "gpt"

    def __init__(self, question_bot: QuestionBotInterface) -> None:
        super().__init__()
        self._question_bot = question_bot

    def matches(self, messenger: MessengerInterface, message: dict):
        command = PipelineHelper.extract_command(messenger.get_message_text(message))
        return self.GPT_COMMAND in command

    def process(self, messenger: MessengerInterface, message: dict):
        (cmd, _, prompt) = PipelineHelper.extract_command_full(
            messenger.get_message_text(message))
        bot = self._question_bot

        answer = bot.answer(prompt)
        try: 
            messenger.mark_in_progress_0(message)
            answer = bot.answer(prompt)
            messenger.mark_in_progress_done(message)
            messenger.reply_message(message, answer.get("text"))
            messenger.mark_in_progress_done(message)
        except Exception as ex:
            logging.critical(ex, exc_info=True)
            messenger.mark_in_progress_fail(message)
            return

    def get_help_text(self) -> str:
        return \
"""*ChatGPT*
_#gpt [prompt]_ Allows you to talk to GPT, the bot does not have memory of previous messages though. """

