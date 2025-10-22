"""Implemenations of different pipelines to process messages. """
import time
import logging
import re
from typing import List

import tempfile
import os

from abc import ABC, abstractmethod

from smrt.bot.messenger import MessengerInterface, WhatsappMessenger

class PipelineInterface(ABC):
    """Generic pipeline interface to process messages. """

    def allowed_in_chat_id(self, messenger: MessengerInterface, message: dict) -> bool:
        """Should allow true if the pipeline is in general allowed in this specific chat

        Args:
            messenger (MessengerInterface): Messenger instance to check in
            message (dict): The incoming message

        Returns:
            bool: true if the message is allowed in this chat
        """
        raise NotImplementedError()

    @abstractmethod
    def matches(self, messenger: MessengerInterface, message: dict) -> bool:
        """Should return true if the message should be processed by the pipeline. """
        raise NotImplementedError()

    @abstractmethod
    def process(self, messenger: MessengerInterface, message: dict) -> None:
        """Processes a message by the pipeline. """
        raise NotImplementedError()

    @abstractmethod
    def get_help_text(self) -> str:
        """Returns the help text for the pipeline. 

        Returns:
            str: help text of the pipeline
        """
        raise NotImplementedError()

class AbstractPipeline(PipelineInterface):
    """Abstract pipeline with default implementations. """

    def __init__(self, chat_id_whitelist: List[str]|None = None, chat_id_blacklist: List[str]|None = None) -> None:
        self._chat_id_whitelist = chat_id_whitelist
        self._chat_id_blacklist = chat_id_blacklist

        if self._chat_id_whitelist is not None and self._chat_id_blacklist is not None:
            raise ValueError("Both chat_id_whitelist and chat_id_blacklist are set, this is not supported.")

    def allowed_in_chat_id(self, messenger: MessengerInterface, message: dict) -> bool:
        # neither blacklist not whitelist is set, allow all
        if self._chat_id_whitelist is None and self._chat_id_blacklist is None:
            return True
        # if only whitelist is set, only allow those
        if self._chat_id_whitelist is not None:
            chat_id = messenger.get_chat_id(message)
            if chat_id not in self._chat_id_whitelist:
                return False
        # if only blacklist is set, disallow those
        if self._chat_id_blacklist is not None:
            chat_id = messenger.get_chat_id(message)
            if chat_id in self._chat_id_blacklist:
                return False
        
        # all checks passed, allow
        return True

    @abstractmethod
    def process(self, messenger: MessengerInterface, message: dict) -> None:
        raise NotImplementedError()

    @abstractmethod
    def get_help_text(self) -> str:
        raise NotImplementedError()

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



class MarkSeenPipeline(AbstractPipeline):
    """A pipe that marks all incomings messages as seen. """
    def __init__(self) -> None:
        # allow in all chats
        super().__init__(None, None)

    def matches(self, messenger: MessengerInterface, message: dict):
        # match all messages to acknowledge
        return True

    def process(self, messenger: MessengerInterface, message: dict):
        messenger.mark_seen(message)

    def get_help_text(self) -> str:
        return ""

class ChatIdPipeline(AbstractPipeline):
    """A pipeline that responds to chatid command with the unique identifier of the chat. """
    CHATID_COMMAND = "chatid"

    def __init__(self) -> None:
        # allow in all chats
        super().__init__(None, None)

    def matches(self, messenger: MessengerInterface, message: dict):
        command = PipelineHelper.extract_command(messenger.get_message_text(message))
        return self.CHATID_COMMAND in command

    def process(self, messenger: MessengerInterface, message: dict):
        response_text = messenger.get_chat_id(message)
        messenger.reply_message(message, response_text)

        messenger.mark_in_progress_done(message)

    def get_help_text(self) -> str:
        return \
f"""*ChatId Help*
_#{self.CHATID_COMMAND}_ Returns the identifier of the current chat. """

class WhatsappLidPipeline(AbstractPipeline):
    """A pipeline that responds to chatid command with the unique identifier of the chat. """
    WALID_COMMAND = "walid"

    def __init__(self) -> None:
        # allow in all chats
        super().__init__(None, None)

    def matches(self, messenger: MessengerInterface, message: dict):
        command = PipelineHelper.extract_command(messenger.get_message_text(message))
        return self.WALID_COMMAND in command

    def process(self, messenger: MessengerInterface, message: dict):
        chat_id = messenger.get_chat_id(message)
        if not chat_id.startswith("whatsapp:") or not isinstance(messenger, WhatsappMessenger):
            messenger.reply_message(message, f"The #{self.WALID_COMMAND} command is only available in WhatsApp chats.")
            messenger.mark_in_progress_fail(message)
            return

        lids = messenger.get_lids(message)
        lid_text = ", ".join(lids)
        response_text = f"Lids: {lid_text}"
        messenger.reply_message(message, response_text)
        messenger.mark_in_progress_done(message)

    def get_help_text(self) -> str:
        return \
f"""*LidId Help*
_#{self.WALID_COMMAND}_ Returns the lids of tagged contacts in the message. """


class HelpPipeline(AbstractPipeline):
    """A pipeline to print help messages. """
    HELP_COMMAND = "help"

    def __init__(self) -> None:
        # allow in all chats
        super().__init__(None, None)
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
            # only include help for pipelines allowed in this chat
            if pipe.allowed_in_chat_id(messenger, message):
                help_text = pipe.get_help_text()
                if help_text is not None and  len(help_text) > 0:
                    response_text = f"{response_text}\n{help_text}"
        messenger.reply_message(message, response_text)
        messenger.mark_in_progress_done(message)

    def get_help_text(self) -> str:
        return \
f"""*Help*
_#{self.HELP_COMMAND}_ Shows this help text"""
