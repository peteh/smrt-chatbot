from abc import ABC, abstractmethod
from summary import SummaryInterface
from transcript import TranscriptInterface
from messenger import MessengerInterface
from questionbot import QuestionBotInterface

from db import Database

import time
import base64

class PipelineInterface(ABC):
    @abstractmethod
    def matches(self, messenger: MessengerInterface, message: dict):
        pass

    @abstractmethod 
    def process(self, messenger: MessengerInterface, message: dict):
        pass


class VoiceMessagePipeline(PipelineInterface):
    def __init__(self, transcriber: TranscriptInterface, summarizer: SummaryInterface, minWordsForSummary: int):
        self._transcriber = transcriber
        self._summarizer = summarizer
        self._minWordsForSummary = minWordsForSummary
        

    def matches(self, messenger: MessengerInterface, message: dict):
        return messenger.hasAudioData(message)
    
    def process(self, messenger: MessengerInterface, message: dict):
        print("Processing in Voice Pipeline")
        # TODO: extract data from class
        data = message['body']
        debug = {}
        #whatsapp.sendMessage(message['from'], "Processing...")
        messenger.markInProgress0(message)
        
        decoded = base64.b64decode(data)
        with open('out.ogg', 'wb') as output_file:
            output_file.write(decoded)

        start = time.time()
        transcript = self._transcriber.transcribe(decoded)
        end = time.time()
        debug['transcript_time'] = end - start
        
        transcriptText = transcript['text']
        words = transcript['words']
        language = transcript['language']
        if messenger.isGroupMessage(message):
            messenger.messageToGroup(message, "Transcribed: \n%s" % (transcriptText))
        else:
            messenger.messageToIndividual(message, "Transcribed: \n%s" % (transcriptText))
        
        debug['transcript_language'] = language
        debug['transcript_language_probability'] = transcript['language_probability']
        debug['transcript_words'] = transcript['words']
        debug['transcript_cost'] = transcript['cost']
        if words > self._minWordsForSummary:
            messenger.markInProgress50(message)
            #whatsapp.sendMessage(message['from'], "Writing summary...")

            start = time.time()
            summary = self._summarizer.summarize(transcriptText, language)
            end = time.time()
            debug['summary_time'] = end - start

            summaryText = summary['text']
            debug['summary_cost'] = summary['cost']
            if messenger.isGroupMessage(message):
                messenger.messageToGroup(message, "Summary: \n%s" % (summaryText))
            else:
                messenger.messageToIndividual(message, "Summary: \n%s" % (summaryText))
        messenger.markInProgressDone(message)
        debugText = "Debug: \n"
        for debugKey, debugValue in debug.items():
            debugText += debugKey + ": " + str(debugValue) + "\n"
        debugText = debugText.strip()
        if messenger.isGroupMessage(message):
            messenger.messageToGroup(message, debugText)
        else:
            messenger.messageToIndividual(message, debugText)


class GroupMessageQuestionPipeline(PipelineInterface):
    def __init__(self, db: Database, summarizer: SummaryInterface, questionBot: QuestionBotInterface, ):
        self._db = db
        self._summarizer = summarizer
        self._questionBot = questionBot

    def matches(self, messenger: MessengerInterface, message: dict):
        # TODO: abstract chat type
        return messenger.isGroupMessage(message) and message['type']=='chat'

    def _getChatText(self, identifier, maxMessageCount):
        chatText = ""
        rows = self._db.getGroupMessages(identifier, maxMessageCount)
        actualMessageCount = 0
        for row in rows:
            chatText += "%s: %s\n" % (row['sender'], row['message'])
            actualMessageCount += 1
        return (chatText, actualMessageCount)
    
    def process(self, messenger: MessengerInterface, message: dict):
        pushName = message['sender']['pushname']
        messageText = message['content']
        # TODO: filter out own messages probably
        QUESTION_COMMAND = "#question"
        if messageText.startswith(QUESTION_COMMAND):
            messenger.markInProgress0(message)
            question = messageText[len(QUESTION_COMMAND)+1:]
            print("Question: %s" % (question))
            # TODO: make number configurable
            chatText, actualMessageCount = self._getChatText(message['chatId'], 100)
            print(chatText)
            prompt = "Der folgende Text beinhaltet eine Konversation mehrere Individuen: \n%s\n\n Beantworte folgende Frage zu dieser Konversation: %s" % (chatText, question)
            answer = self._questionBot.answer(prompt)
            answerText = answer['text']
            print("Question: %s" % (answerText))
            messenger.messageToGroup(message, answerText)
            messenger.markInProgressDone(message)

        if messageText.startswith("#summary"):
            debug = {}
            messenger.markInProgress0(message)
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
            messenger.messageToGroup(message, summaryText)
            messenger.markInProgressDone(message)
            debugText = "Debug: \n"
            for debugKey, debugValue in debug.items():
                debugText += debugKey + ": " + str(debugValue) + "\n"
            debugText = debugText.strip()
            messenger.messageToGroup(message, debugText)
        else:
            self._db.addGroupMessage(message['chatId'], pushName, messageText)