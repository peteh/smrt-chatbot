"""Implemenations of different pipelines to process messages. """
import time
import logging
import re
from typing import List

import tempfile
import os

from abc import ABC, abstractmethod

from messenger import MessengerInterface





class PipelineInterface(ABC):
    """Generic pipeline interface to process messages. """

    @abstractmethod
    def matches(self, messenger: MessengerInterface, message: dict) -> bool:
        """Should return true if the message should be processed by the pipeline. """

    @abstractmethod
    def process(self, messenger: MessengerInterface, message: dict) -> None:
        """Processes a message by the pipeline. """

    @abstractmethod
    def get_help_text(self) -> str:
        """Returns the help text for the pipeline. 

        Returns:
            str: help text of the pipeline
        """

class PipelineHelper():
    """Helper functions for pipelines"""

    @staticmethod
    def extract_command(data: str):
        """Extracts commands from a text, returns empty string if there 
        is no command inside"""
        left_over = data.strip()
        if not left_over.startswith("#"):
            return ""
        length = 0
        for i in range(1, len(left_over)):
            if left_over[i].isalnum() or left_over[i] == "_":
                length += 1
            else:
                break
        if length == 0:
            return ""
        command = left_over[1:1 + length]
        return command

    @staticmethod
    def extract_command_full(data: str) -> tuple[str, str, str] | None:
        """Extracts commands from a text"""
        left_over = data.strip()
        if not left_over.startswith("#"):
            return None
        length = 0
        for i in range(1, len(left_over)):
            if left_over[i].isalnum() or left_over[i] == "_":
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



class MarkSeenPipeline(PipelineInterface):
    """A pipe that marks all incomings messages as seen. """
    def __init__(self) -> None:
        pass

    def matches(self, messenger: MessengerInterface, message: dict):
        # match all messages to acknowledge
        return True

    def process(self, messenger: MessengerInterface, message: dict):
        messenger.mark_seen(message)

    def get_help_text(self) -> str:
        return ""

class ChatIdPipeline(PipelineInterface):
    """A pipeline that responds to chatid command with the unique identifier of the chat. """
    CHATID_COMMAND = "chatid"

    def __init__(self) -> None:
        super().__init__()

    def matches(self, messenger: MessengerInterface, message: dict):
        command = PipelineHelper.extract_command(messenger.get_message_text(message))
        return self.CHATID_COMMAND in command

    def process(self, messenger: MessengerInterface, message: dict):
        messenger.get_chat_id(message)

        response_text = messenger.get_chat_id(message)
        messenger.reply_message(message, response_text)

        messenger.mark_in_progress_done(message)

    def get_help_text(self) -> str:
        return \
"""*ChatId Help*
_#chatid_ Returns the identifier of the current chatid. """


class Helpipeline(PipelineInterface):
    """A pipeline to print help messages. """
    HELP_COMMAND = "help"

    def __init__(self) -> None:
        super().__init__()
        self._pipelines = []
    
    def set_pipelines(self, pipelines: List[PipelineInterface]):
        self._pipelines = pipelines

    def matches(self, messenger: MessengerInterface, message: dict):
        command = PipelineHelper.extract_command(messenger.get_message_text(message))
        return self.HELP_COMMAND in command

    def process(self, messenger: MessengerInterface, message: dict):
        messenger.mark_in_progress_0(message)

        response_text = "My name is Echo, these are the things I can do: "
        for pipe in self._pipelines:
            help_text = pipe.get_help_text()
            if help_text is not None and  len(help_text) > 0:
                response_text = f"{response_text}\n{help_text}"
        messenger.reply_message(message, response_text)
        messenger.mark_in_progress_done(message)

    def get_help_text(self) -> str:
        return \
"""*Help*
_#help_ Shows this help text"""
