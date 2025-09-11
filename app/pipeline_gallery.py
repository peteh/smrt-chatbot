"""Implementations of a pipeline for processing text and voice for homeassistant. """
import logging
import typing

from pipeline import PipelineInterface, PipelineHelper
from messenger import MessengerInterface


class GalleryPipeline(PipelineInterface):
    """Pipe to store images in a gallery from group chats. """
    GALLERY_COMMAND = "gallery"

    def __init__(self):

        self._commands = [self.GALLERY_COMMAND]

    def matches(self, messenger: MessengerInterface, message: dict):
        if not messenger.is_group_message(message):
            return False
        
        # we have an image that we might need to process
        if messenger.has_image_data(message):
            return True
        
        # gallery command
        command = PipelineHelper.extract_command(messenger.get_message_text(message))
        return command in self._commands


    def process(self, messenger: MessengerInterface, message: dict):

        # we have an image that we might need to process
        if messenger.has_image_data(message):
                
            messenger.mark_in_progress_0(message)
            try:
                chat_id = messenger.get_chat_id(message)
                # TODO: only insert if no duplicate in db
                image_data = messenger.download_media(message)
                messenger.mark_in_progress_done(message)
                    
            except Exception as ex:
                logging.critical(ex, exc_info=True)  # log exception info at CRITICAL log level
                messenger.mark_in_progress_fail(message)
                return
            return
        
        try:
            # gallery command
            text = messenger.get_message_text(message)
            command, _, params = PipelineHelper.extract_command_full(messenger.get_message_text(message))
            if command == self.GALLERY_COMMAND and params is None or len(params) == 0:
                
                # TODO: generate link for gallery
                messenger.reply_message(message, "Gallery link: https://example.com/gallery")
                messenger.mark_in_progress_fail(message)
                return
            
                
        except Exception as ex:
            logging.critical(ex, exc_info=True)  # log exception info at CRITICAL log level
            messenger.mark_in_progress_fail(message)
            return
    def get_help_text(self) -> str:
        # TODO: automatically tell which models we have
        return \
"""*Gallery creation*
_#gallery enable/disable_ Enables the storage of images sent to the group in a gallery.
_#gallery_ Shows if gallery is on or off and provides a link to the gallery."""
