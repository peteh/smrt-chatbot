"""Implemenations of different pipelines to process messages. """
import time
import logging
import re
from typing import List

from abc import ABC, abstractmethod


# text to speech pipeline standard imports
import tempfile
import os
import subprocess

from summary import SummaryInterface
from transcript import TranscriptInterface
from messenger import MessengerInterface
from questionbot import QuestionBotInterface
import texttoimage



# article summary pipeline
import trafilatura
from db import Database
import youtubeextract

# text to speech pipeline
from TTS.api import TTS


class PipelineInterface(ABC):
    """Generic pipeline interface to process messages. """

    @abstractmethod
    def matches(self, messenger: MessengerInterface, message: dict):
        """Should return true if the message should be processed by the pipeline. """

    @abstractmethod
    def process(self, messenger: MessengerInterface, message: dict):
        """Processes a message by the pipeline. """

class PipelineHelper():
    """Helper functions for pipelines"""
    
    @staticmethod
    def extract_command(data: str):
        """Extracts commands from a text"""
        left_over = data.strip()
        if not left_over.startswith("#"):
            return None
        length = 0
        for i in range(1, len(left_over)):
            if left_over[i].isalpha():
                length += 1
            else:
                break
        if length == 0:
            return None
        command = left_over[1:1 + length]
        return command

    @staticmethod
    def extract_command_full(data: str) -> List[str]:
        """Extracts commands from a text"""
        left_over = data.strip()
        if not left_over.startswith("#"):
            return None
        length = 0
        for i in range(1, len(left_over)):
            if left_over[i].isalpha():
                length += 1
            else:
                break
        if length == 0:
            return None
        command = left_over[1:1 + length]
        left_over = left_over[1 + length:]

        params = ""
        if len(left_over) > 0 and left_over[0] == "(":
            end_parentesis = left_over.find(")")
            if end_parentesis == -1:
                return None
            params = left_over[1:end_parentesis]
            left_over = left_over[end_parentesis+1:]

        left_over = left_over.strip()
        return (command, params, left_over)


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
        (command, _, text) = PipelineHelper.extract_command_full(messenger.get_message_text(message))
        message_text = messenger.get_message_text(message)
        if self.GRAMMAR_COMMAND in command:
            text = message_text[len(self.GRAMMAR_COMMAND)+1:]
            prompt = f"Enhance the quality of the text below. Grammar, punctuation, spelling, \
        word choice and style should be examined in detail. Additionally, the style and \
        tone must be improved to ensure the writing is polished, error-free, and \
        easy to read: \n\n{text}"

        elif self.GRAMMATIK_COMMAND in command:
            text = message_text[len(self.GRAMMATIK_COMMAND)+1:]
            prompt = f"Verbessere die Qualität des folgenden Textes. Grammatik, Interpunktion, \
        Rechtschreibung, Wortwahl und Stil soll besonders beachtet werden. Außerdem soll Stil und Ton so verbessert werden, \
        dass einen eleganter, fehlerfreier und einfach zu lesender Text entsteht: \n\n{text}"
        else:
            # skip
            return

        messenger.mark_in_progress_0(message)
        answer = self._question_bot.answer(prompt)
        if answer is None:
            messenger.mark_in_progress_fail(message)
            return
        answer_text = answer['text']
        if messenger.is_group_message(message):
            messenger.send_message_to_group(message, answer_text)
        else:
            messenger.send_message_to_individual(message, answer_text)
        messenger.mark_in_progress_done(message)


class VoiceMessagePipeline(PipelineInterface):
    """A pipe that converts audio messages to text and summarizes them. """
    def __init__(self, transcriber: TranscriptInterface,
                 summarizer: SummaryInterface,
                 min_words_for_summary: int):
        self._transcriber = transcriber
        self._summarizer = summarizer
        self._min_words_for_summary = min_words_for_summary
        self._store_files = False


    def matches(self, messenger: MessengerInterface, message: dict):
        return messenger.has_audio_data(message)

    def process(self, messenger: MessengerInterface, message: dict):
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
        if messenger.is_group_message(message):
            messenger.send_message_to_group(message, f"Transcribed: \n{transcript_text}")
        else:
            messenger.send_message_to_individual(message, f"Transcribed: \n{transcript_text}")

        debug['transcript_language'] = language
        debug['transcript_language_probability'] = transcript['language_probability']
        debug['transcript_words'] = transcript['words']
        debug['transcript_cost'] = transcript['cost']
        if words > self._min_words_for_summary:
            messenger.mark_in_progress_50(message)

            start = time.time()
            summary = self._summarizer.summarize(transcript_text, language)
            end = time.time()
            debug['summary_time'] = end - start

            summary_text = summary['text']
            debug['summary_cost'] = summary['cost']
            if messenger.is_group_message(message):
                messenger.send_message_to_group(message, f"Summary: \n{summary_text}")
            else:
                messenger.send_message_to_individual(message, f"Summary: \n{summary_text}")
        messenger.mark_in_progress_done(message)
        debug_text = "Debug: \n"
        for debug_key, debug_value in debug.items():
            debug_text += debug_key + ": " + str(debug_value) + "\n"
        debug_text = debug_text.strip()
        if messenger.is_group_message(message):
            messenger.send_message_to_group(message, debug_text)
        else:
            messenger.send_message_to_individual(message, debug_text)


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
        return messenger.is_group_message(message) and message['type']=='chat'

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
        (chat_text, _) = self._get_chat_text(message['chatId'], 100)
        print(chat_text)
        prompt = f"Der folgende Text beinhaltet eine Konversation mehrere Individuen, \
            beantworte folgende Frage zu dieser Konversation: {question}\n\nText:\n{chat_text}"
        answer = self._question_bot.answer(prompt)
        answer_text = answer['text']
        print(f"Answer: {answer_text}")
        messenger.send_message_to_group(message, answer_text)
        messenger.mark_in_progress_done(message)

    def _process_summary_command(self, messenger: MessengerInterface, message: dict):
        debug = {}
        message_text = messenger.get_message_text(message)
        messenger.mark_in_progress_0(message)
        # TODO: put to configuration
        max_message_count = 20
        command = message_text.split(" ")
        if len(command) > 1:
            max_message_count = int(command[1])

        (chat_text, actual_message_count) = self._get_chat_text(message['chatId'],
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
        debug_text = "Debug: \n"
        for debug_key, debug_value in debug.items():
            debug_text += debug_key + ": " + str(debug_value) + "\n"
        debug_text = debug_text.strip()
        messenger.send_message_to_group(message, debug_text)

    def process(self, messenger: MessengerInterface, message: dict):
        # TODO: abstract this
        push_name = message['sender']['pushname']
        message_text = messenger.get_message_text(message)

        if message_text.startswith(self.QUESTION_COMMAND):
            self._process_question_command(messenger, message)

        elif message_text.startswith(self.SUMMARY_COMMAND):
            self._process_summary_command(messenger, message)
        else:
            # TODO: filter messages with command
            self._database.add_group_message(message['chatId'], push_name, message_text)


class ArticleSummaryPipeline(PipelineInterface):
    """Summarizes an article or a youtube video. """

    MAX_TRANSCRIPT_LENGTH = 20000

    def __init__(self, summarizer: SummaryInterface):
        self._summarizer = summarizer
        self._link_regex = re.compile('((https?):((//)|(\\\\))+([\w\d:#@%/;$()~_?\+-=\\\.&](#!)?)*)',
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

    def _process_article(self, link: str):
        config = trafilatura.settings.use_config()
        config.set("DEFAULT", "EXTRACTION_TIMEOUT", "0")

        downloaded = trafilatura.fetch_url(link)
        if downloaded is None:
            print("Failed to retrieve article, skipping")
            return ""

        # extract information from HTML
        extracted_text = trafilatura.extract(downloaded, config=config)
        summarized_text = self._summarizer.summarize(extracted_text, self._language)['text']
        print("==EXTRACTED==")
        print(extracted_text)
        print("==SUMMARY==")
        print(summarized_text)
        return summarized_text

    def _process_youtube(self, link):
        processor = youtubeextract.YoutubeExtract(link)
        text = processor.getScript()
        text_length = len(text)
        print(f"Length of youtube transcript: {text_length}")
        # reducing to the last 10k letters to limit input for summary
        # TODO: maybe do in parts...
        if len(text) > self.MAX_TRANSCRIPT_LENGTH:
            print(f"Transcript exceeding {self.MAX_TRANSCRIPT_LENGTH} letters, reducing...")
        text = text[-self.MAX_TRANSCRIPT_LENGTH:]
        summarized_text = self._summarizer.summarize(text, self._language)['text']
        return summarized_text

    def process(self, messenger: MessengerInterface, message: dict):
        message_text = messenger.get_message_text(message)
        messenger.mark_in_progress_0(message)
        links = self._extract_urls(message_text)
        total_summary = ""

        try:
            for link in links:
                if youtubeextract.YoutubeExtract.isYoutubeLink(link):
                    summarized_text = self._process_youtube(link)
                else:
                    summarized_text = self._process_article(link)
                summary_part = f"{link}: \n{summarized_text}\n"
                total_summary += summary_part
        except Exception as ex:
            logging.critical(ex, exc_info=True)  # log exception info at CRITICAL log level
            messenger.mark_in_progress_fail(message)
            return
        if messenger.is_group_message(message):
            messenger.send_message_to_group(message, total_summary)
        else:
            messenger.send_message_to_individual(message, total_summary)
        messenger.mark_in_progress_done(message)


class ImagePromptPipeline(PipelineInterface):
    """Pipe to turn prompts into images. """
    IMAGE_COMMAND = "#image"

    def __init__(self, image_api: texttoimage.ImagePromptInterface):
        self._image_api = image_api

    def matches(self, messenger: MessengerInterface, message: dict):
        message_text = messenger.get_message_text(message)
        return message_text.startswith(self.IMAGE_COMMAND)

    def process(self, messenger: MessengerInterface, message: dict):
        message_text = messenger.get_message_text(message)
        if message_text.startswith(self.IMAGE_COMMAND):
            messenger.mark_in_progress_0(message)
            try:
                prompt = message_text[len(self.IMAGE_COMMAND)+1:]
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


class TextToSpeechPipeline(PipelineInterface):
    """Pipe to generate a voice messages based on input text. """
    TTS_COMMAND = "#tts"

    def __init__(self):
        self._tts = None

    def _get_tts(self):
        # lazy loading
        if self._tts is None:
            self._tts = TTS("tts_models/de/thorsten/tacotron2-DDC")
        return self._tts

    def _text_to_vorbis_audio(self, text: str):
        tts = self._get_tts()
        with tempfile.TemporaryDirectory() as tmp:
            input_file = os.path.join(tmp, 'input.wav')
            tts.tts_to_file(text=text, file_path=input_file)
            output_file = os.path.join(tmp, 'output.opus')

            subprocess.run(["opusenc", input_file, output_file], check=True)
            file = open(output_file,mode='rb')
            ogg_data = file.read()
            file.close()
        return ogg_data

    def matches(self, messenger: MessengerInterface, message: dict):
        message_text = messenger.get_message_text(message)
        return message_text.startswith(self.TTS_COMMAND)

    def process(self, messenger: MessengerInterface, message: dict):
        message_text = messenger.get_message_text(message)
        if message_text.startswith(self.TTS_COMMAND):
            messenger.mark_in_progress_0(message)
            text = message_text[len(self.TTS_COMMAND)+1:]
            audio_data = self._text_to_vorbis_audio(text)

            if messenger.is_group_message(message):
                messenger.send_audio_to_group(message, audio_data)
            else:
                messenger.send_audio_to_individual(message, audio_data)

            messenger.mark_in_progress_done(message)

class TinderPipelinePipelineInterface(PipelineInterface):
    """A pipeline to write answers to tinder messages. """
    TINDER_COMMAND = "#tinder"

    def __init__(self, question_bot: QuestionBotInterface) -> None:
        super().__init__()
        self._question_bot = question_bot

    def matches(self, messenger: MessengerInterface, message: dict):
        message_text = messenger.get_message_text(message)
        if message_text.startswith(self.TINDER_COMMAND):
            return True
        return False

    def process(self, messenger: MessengerInterface, message: dict):
        message_text = messenger.get_message_text(message)
        messenger.mark_in_progress_0(message)
        tinder_message = message_text[len(self.TINDER_COMMAND)+1:]
        prompt = f"Schreibe eine kurze, lockere, lustige Anwort auf folgende Nachricht \
            von einem Mädchen: \n{tinder_message}"
        answer = self._question_bot.answer(prompt)
        if answer is None:
            messenger.mark_in_progress_fail(message)
            return

        response_text = answer['text']
        if messenger.is_group_message(message):
            messenger.send_message_to_group(message, response_text)
        else:
            messenger.send_message_to_individual(message, response_text)

        messenger.mark_in_progress_done(message)
