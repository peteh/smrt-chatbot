from abc import ABC, abstractmethod
from summary import SummaryInterface
from transcript import TranscriptInterface
from messenger import MessengerInterface
from questionbot import QuestionBotInterface
import texttoimage
import logging

# article summary pipeline
import re
import trafilatura

from db import Database

import time

class PipelineInterface(ABC):
    @abstractmethod
    def matches(self, messenger: MessengerInterface, message: dict):
        pass

    @abstractmethod 
    def process(self, messenger: MessengerInterface, message: dict):
        pass

class GrammarPipeline(PipelineInterface):
    GRAMMAR_COMMAND = "#grammar"
    GRAMMATIK_COMMAND = "#grammatik"

    def __init__(self, questionBot: QuestionBotInterface) -> None:
        super().__init__()
        self._questionBot = questionBot
    
    def matches(self, messenger: MessengerInterface, message: dict):
        return messenger.get_message_text(message).startswith(self.GRAMMAR_COMMAND) \
            or messenger.get_message_text(message).startswith(self.GRAMMATIK_COMMAND)
    
    def process(self, messenger: MessengerInterface, message: dict):
        messageText = messenger.get_message_text(message)
        if messageText.startswith(self.GRAMMAR_COMMAND):
            text = messageText[len(self.GRAMMAR_COMMAND)+1:]
            prompt = "Enhance the quality of the text below. Grammar, punctuation, spelling, \
        word choice and style should be examined in detail. Additionally, the style and \
        tone must be improved to ensure the writing is polished, error-free, and \
        easy to read: \n%s" % (text)
            
        elif messageText.startswith(self.GRAMMATIK_COMMAND):
            text = messageText[len(self.GRAMMATIK_COMMAND)+1:]
            prompt = "Verbessere die Qualität des folgenden Textes. Grammatik, Interpunktion, Rechtschreibung, \
        Wortwahl und Stil soll besonders beachtet werden. Außerdem soll Stil und Ton so verbessert werden, \
        dass einen eleganter, fehlerfreier und einfach zu lesender Text entsteht: \n%s" % (text)
        else:
            # skip
            return
        
        messenger.mark_in_progress_0(message)
        answer = self._questionBot.answer(prompt)
        if answer is None:
            messenger.mark_in_progress_fail(message)
            return
        answerText = answer['text']
        if messenger.is_group_message(message):
            messenger.message_to_group(message, answerText)
        else:
            messenger.message_to_individual(message, answerText)
        messenger.mark_in_progress_done(message)
        

        

class VoiceMessagePipeline(PipelineInterface):
    def __init__(self, transcriber: TranscriptInterface, summarizer: SummaryInterface, minWordsForSummary: int):
        self._transcriber = transcriber
        self._summarizer = summarizer
        self._minWordsForSummary = minWordsForSummary
        self._storeFiles = False
        

    def matches(self, messenger: MessengerInterface, message: dict):
        return messenger.hasAudioData(message)
    
    def process(self, messenger: MessengerInterface, message: dict):
        print("Processing in Voice Pipeline")
        debug = {}
        messenger.mark_in_progress_0(message)
        
        mimeType, decoded = messenger.downloadMedia(message)
        if self._storeFiles:
            with open('out.opus', 'wb') as output_file:
                output_file.write(decoded)

        start = time.time()
        transcript = self._transcriber.transcribe(decoded)
        end = time.time()
        debug['transcript_time'] = end - start
        
        transcriptText = transcript['text']
        words = transcript['words']
        language = transcript['language']
        if messenger.is_group_message(message):
            messenger.message_to_group(message, "Transcribed: \n%s" % (transcriptText))
        else:
            messenger.message_to_individual(message, "Transcribed: \n%s" % (transcriptText))
        
        debug['transcript_language'] = language
        debug['transcript_language_probability'] = transcript['language_probability']
        debug['transcript_words'] = transcript['words']
        debug['transcript_cost'] = transcript['cost']
        if words > self._minWordsForSummary:
            messenger.mark_in_progress_50(message)

            start = time.time()
            summary = self._summarizer.summarize(transcriptText, language)
            end = time.time()
            debug['summary_time'] = end - start

            summaryText = summary['text']
            debug['summary_cost'] = summary['cost']
            if messenger.is_group_message(message):
                messenger.message_to_group(message, "Summary: \n%s" % (summaryText))
            else:
                messenger.message_to_individual(message, "Summary: \n%s" % (summaryText))
        messenger.mark_in_progress_done(message)
        debugText = "Debug: \n"
        for debugKey, debugValue in debug.items():
            debugText += debugKey + ": " + str(debugValue) + "\n"
        debugText = debugText.strip()
        if messenger.is_group_message(message):
            messenger.message_to_group(message, debugText)
        else:
            messenger.message_to_individual(message, debugText)


# TODO split into message storage pipeline and command pipeline
class GroupMessageQuestionPipeline(PipelineInterface):
    QUESTION_COMMAND = "#question"
    SUMMARY_COMMAND = "#summary"
    
    def __init__(self, db: Database, summarizer: SummaryInterface, questionBot: QuestionBotInterface, ):
        self._db = db
        self._summarizer = summarizer
        self._questionBot = questionBot

    def matches(self, messenger: MessengerInterface, message: dict):
        # TODO: abstract chat type
        return messenger.is_group_message(message) and message['type']=='chat'

    def _getChatText(self, identifier, maxMessageCount):
        chatText = ""
        rows = self._db.getGroupMessages(identifier, maxMessageCount)
        actualMessageCount = 0
        for row in rows:
            chatText += "%s: %s\n" % (row['sender'], row['message'])
            actualMessageCount += 1
        return (chatText, actualMessageCount)
    
    def process(self, messenger: MessengerInterface, message: dict):
        # TODO: abstract this
        pushName = message['sender']['pushname']
        messageText = message['content']

        
        if messageText.startswith(self.QUESTION_COMMAND):
            messenger.mark_in_progress_0(message)
            question = messageText[len(self.QUESTION_COMMAND)+1:]
            print("Question: %s" % (question))
            # TODO: make number configurable
            chatText, actualMessageCount = self._getChatText(message['chatId'], 100)
            print(chatText)
            prompt = "Der folgende Text beinhaltet eine Konversation mehrere Individuen: \n%s\n\n Beantworte folgende Frage zu dieser Konversation: %s" % (chatText, question)
            answer = self._questionBot.answer(prompt)
            answerText = answer['text']
            print("Answer: %s" % (answerText))
            messenger.message_to_group(message, answerText)
            messenger.mark_in_progress_done(message)

        if messageText.startswith(self.SUMMARY_COMMAND):
            debug = {}
            messenger.mark_in_progress_0(message)
            # TODO: put to configuration
            maxMessageCount = 20
            command = messageText.split(" ")
            if len(command) > 1:
                maxMessageCount = int(command[1])

            chatText, actualMessageCount = self._getChatText(message['chatId'], maxMessageCount)

            start = time.time()
            summary = self._summarizer.summarize(chatText, 'de')
            end = time.time()

            debug['summmary_input'] = chatText
            debug['summmary_maxMessages'] = maxMessageCount
            debug['summmary_actualMessages'] = actualMessageCount
            debug['summary_time'] = end - start
            debug['summary_cost'] = summary['cost']

            summaryText = "Summary (last %d messages)\n%s" % (actualMessageCount, summary['text'])
            messenger.message_to_group(message, summaryText)
            messenger.mark_in_progress_done(message)
            debugText = "Debug: \n"
            for debugKey, debugValue in debug.items():
                debugText += debugKey + ": " + str(debugValue) + "\n"
            debugText = debugText.strip()
            messenger.message_to_group(message, debugText)
        else:
            # TODO: filter messages with command
            self._db.addGroupMessage(message['chatId'], pushName, messageText)
            

import youtubeextract
class ArticleSummaryPipeline(PipelineInterface):
    MAX_TRANSCRIPT_LENGTH = 20000

    def __init__(self, summarizer: SummaryInterface):
        self._summarizer = summarizer
        self._linkRegex = re.compile('((https?):((//)|(\\\\))+([\w\d:#@%/;$()~_?\+-=\\\.&](#!)?)*)', re.DOTALL)
        self._language = "en"

    def _extractUrl(self, text: str):
        links = []
        for extract in re.findall(self._linkRegex, text):
            links.append(extract[0])
        return links

    def matches(self, messenger: MessengerInterface, message: dict):
        messageText = messenger.get_message_text(message)
        links = self._extractUrl(messageText)
        return len(links) > 0
    
    def _processArticle(self, link: str):
        config = trafilatura.settings.use_config()
        config.set("DEFAULT", "EXTRACTION_TIMEOUT", "0")

        downloaded = trafilatura.fetch_url(link)
        if downloaded is None: 
            print("Failed to retrieve article, skipping")
            return ""

        # extract information from HTML
        extractedText = trafilatura.extract(downloaded, config=config)
        summarizedText = self._summarizer.summarize(extractedText, self._language)['text']
        print("==EXTRACTED==")
        print(extractedText)
        print("==SUMMARY==")
        print(summarizedText)
        return summarizedText
    
    
    
    def _processYoutube(self, link):
        processor = youtubeextract.YoutubeExtract(link)
        text = processor.getScript()
        print("Length of youtube transcript: %d" % (len(text)))
        # reducing to the last 10k letters to limit input for summary
        # TODO: maybe do in parts...
        if len(text) > self.MAX_TRANSCRIPT_LENGTH:
            print("Transcript exceeding %d letters, reducing..." % (self.MAX_TRANSCRIPT_LENGTH))
        text = text[-self.MAX_TRANSCRIPT_LENGTH:]
        summarizedText = self._summarizer.summarize(text, self._language)['text']
        return summarizedText

    def process(self, messenger: MessengerInterface, message: dict):
        messageText = messenger.get_message_text(message)
        messenger.mark_in_progress_0(message)
        links = self._extractUrl(messageText)
        totalSummary = ""
        
        try:
            for link in links:
                if youtubeextract.YoutubeExtract.isYoutubeLink(link):
                    summarizedText = self._processYoutube(link)
                else:
                    summarizedText = self._processArticle(link)
                summaryPart = "%s: \n%s\n" % (link, summarizedText)
                totalSummary += summaryPart
        except Exception as e:
                logging.critical(e, exc_info=True)  # log exception info at CRITICAL log level
                messenger.mark_in_progress_fail(message)
                return
        if messenger.is_group_message(message):
            messenger.message_to_group(message, totalSummary)
        else:
            messenger.message_to_individual(message, totalSummary)
        messenger.mark_in_progress_done(message)


class ImagePromptPipeline(PipelineInterface):
    IMAGE_COMMAND = "#image"

    def __init__(self, imageAPI: texttoimage.ImagePromptInterface):
        self._imageAPI = imageAPI

    def matches(self, messenger: MessengerInterface, message: dict):
        messageText = messenger.get_message_text(message)
        return messageText.startswith(self.IMAGE_COMMAND)
    
    def process(self, messenger: MessengerInterface, message: dict):
        messageText = messenger.get_message_text(message)
        if messageText.startswith(self.IMAGE_COMMAND):
            messenger.mark_in_progress_0(message)
            try:
                prompt = messageText[len(self.IMAGE_COMMAND)+1:]
                images = self._imageAPI.process(prompt)
                if images is None:
                    messenger.mark_in_progress_fail(message)
                    return

                for image in images:
                    fileName, binary = image
                    if messenger.is_group_message(message):
                        messenger.imageToGroup(message, fileName, binary, prompt)
                    else:
                        messenger.imageToIndividual(message, fileName, binary, prompt)
            except Exception as e:
                logging.critical(e, exc_info=True)  # log exception info at CRITICAL log level
                messenger.mark_in_progress_fail(message)
                return

            messenger.mark_in_progress_done(message)


from TTS.api import TTS
import tempfile
import os
import subprocess
class TextToSpeechPipeline(PipelineInterface):

    TTS_COMMAND = "#tts"

    def __init__(self):
        self._tts = None

    def _getTTS(self):
        # lazy loading
        if self._tts is None:
            self._tts = TTS("tts_models/de/thorsten/tacotron2-DDC")
        return self._tts

    def _textToVorbisAudio(self, text: str):
        tts = self._getTTS()
        with tempfile.TemporaryDirectory() as tmp:
            inputFile = os.path.join(tmp, 'input.wav')
            tts.tts_to_file(text=text, file_path=inputFile)
            outputFile = os.path.join(tmp, 'output.opus')
            
            subprocess.run(["opusenc", inputFile, outputFile]) 
            file = open(outputFile,mode='rb')
            oggData = file.read()
            file.close()
        return oggData
    
    def matches(self, messenger: MessengerInterface, message: dict):
        messageText = messenger.get_message_text(message)
        return messageText.startswith(self.TTS_COMMAND)
    
    def process(self, messenger: MessengerInterface, message: dict):
        messageText = messenger.get_message_text(message)
        if messageText.startswith(self.TTS_COMMAND):
            messenger.mark_in_progress_0(message)
            text = messageText[len(self.TTS_COMMAND)+1:]
            audioData = self._textToVorbisAudio(text)
            
            if messenger.is_group_message(message):
                messenger.audioToGroup(message, audioData)
            else:
                messenger.audioToIndividual(message, audioData)

            messenger.mark_in_progress_done(message)