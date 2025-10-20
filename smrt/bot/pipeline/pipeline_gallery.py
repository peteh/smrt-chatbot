"""Implementations of a pipeline for processing text and voice for homeassistant. """
import logging
import typing
import hashlib
import uuid
import io
import os
import base64
from PIL import Image
from smrt.db import GalleryDatabase
import smrt.utils.utils as utils

from smrt.bot.messenger import MessengerInterface

from .pipeline import PipelineHelper, AbstractPipeline
class GalleryPipeline(AbstractPipeline):
    """Pipe to store images in a gallery from group chats. """
    GALLERY_COMMAND = "gallery"

    def __init__(self, gallery_db: GalleryDatabase, base_url: str, chat_id_whitelist: typing.List[str] = None, chat_id_blacklist: typing.List[str] = None):
        super().__init__(chat_id_whitelist, chat_id_blacklist)
        self._commands = [self.GALLERY_COMMAND]
        self._gallery_db = gallery_db
        self._base_url = base_url

    def matches(self, messenger: MessengerInterface, message: dict):
        # not a group message, no need to process
        if not messenger.is_group_message(message):
            return False
        
        # we have an image that we might need to process
        if messenger.has_image_data(message):
            return True
        
        # gallery command
        command = PipelineHelper.extract_command(messenger.get_message_text(message))
        return command in self._commands

    def process_image_store(self, image_data) -> str:
        """Processes the image for thumb and storage

        Args:
            image_data (_type_): Byte data of the image

        Returns:
            str: _description_
        """
        file_uuid = str(uuid.uuid4())

        image_filename = utils.storage_path() + f"/gallery/{file_uuid}.blob"
        thumb_filename = utils.storage_path() + f"/gallery/{file_uuid}_thumb.png"
        # write binary to file: 
        with open(image_filename, "wb") as f:
            f.write(image_data)
        # create thumbnail
        img = Image.open(image_filename)
        # Create a thumbnail (max size 128x128, keeps aspect ratio)
        img.thumbnail((128, 128))

        # Save thumbnail
        img.save(thumb_filename, format = "png")
        logging.debug(f"Thumbnail saved as {thumb_filename}")
        return file_uuid
                
    def process(self, messenger: MessengerInterface, message: dict):
        # we have an image that we might need to process
        if messenger.has_image_data(message):
            try:
                chat_id = messenger.get_chat_id(message)
                gallery_db = GalleryDatabase()
                if not gallery_db.is_enabled(chat_id):
                    # gallery not enabled for this group
                    return
                
                messenger.mark_in_progress_0(message)
                # TODO: only insert if no duplicate in db
                mime_type, image_data = messenger.download_media(message)
                
                if mime_type not in ["image/png", "image/jpeg", "image/jpg"]:
                    messenger.mark_skipped(message)
                    return
                
                # Load image from binary data
                img = Image.open(io.BytesIO(image_data))

                # Get width and height
                width, height = img.size
                
                if width < 1024 or height < 1024:
                    messenger.mark_skipped(message)
                    return
                
                # Compute MD5 hash and skip duplicates in the same group
                sha256_hash = hashlib.sha256(image_data).hexdigest()
                
                if gallery_db.has_image(chat_id, sha256_hash):
                    messenger.mark_skipped(message)
                    return

                file_uuid = self.process_image_store(image_data)
                self._gallery_db.add_image(chat_id, messenger.get_sender_name(message), mime_type ,file_uuid, sha256_hash)
                
                messenger.mark_in_progress_done(message)
                    
            except Exception as ex:
                logging.critical(ex, exc_info=True)  # log exception info at CRITICAL log level
                messenger.mark_in_progress_fail(message)
                return
            return
        
        try:
            # gallery command
            command, _, params = PipelineHelper.extract_command_full(messenger.get_message_text(message))
            if command == self.GALLERY_COMMAND:
                messenger.mark_in_progress_0(message)
                gallery_db = GalleryDatabase()
                if params is None or len(params) == 0:
                    enabled = gallery_db.is_enabled(messenger.get_chat_id(message))
                    encoded_chat_id = base64.b64encode(messenger.get_chat_id(message).encode('utf-8')).decode('utf-8')
                    messenger.reply_message(message, f"Gallery is {'enabled' if enabled else 'disabled'} for this group\nGallery link: {self._base_url}/gallery/{encoded_chat_id}")
                    messenger.mark_in_progress_done(message)
                    return
                elif params.lower() == "enable" or params.lower() == "on":
                    gallery_db.set_enabled(messenger.get_chat_id(message), True)
                    messenger.reply_message(message, "Gallery enabled for this group.")
                    messenger.mark_in_progress_done(message)
                    return
                elif params.lower() == "disable" or params.lower() == "off":
                    gallery_db.set_enabled(messenger.get_chat_id(message), False)
                    messenger.reply_message(message, "Gallery disabled for this group.")
                    messenger.mark_in_progress_done(message)
                    return  
                else:
                    messenger.reply_message(message, "Unknown parameter. Use #gallery on/off to enable or disable the gallery, or just #gallery to get the link.")
                    messenger.mark_in_progress_fail(message)
                    return
        except Exception as ex:
            logging.critical(ex, exc_info=True)  # log exception info at CRITICAL log level
            messenger.mark_in_progress_fail(message)
            return
    def get_help_text(self) -> str:
        # TODO: automatically tell which models we have
        return \
f"""*Gallery Creation*
_#{self.GALLERY_COMMAND} on/off_ Enables or disables the storage of images sent to the group in a gallery.
_#{self.GALLERY_COMMAND}_ Shows if gallery is on or off and provides a link to the gallery."""


class GalleryDeletePipeline(AbstractPipeline):
    """Pipe to delete images from the gallery. """
    GALLERY_DELETE_COMMAND = "gallerydelete"

    def __init__(self, gallery_db: GalleryDatabase, chat_id_whitelist: typing.List[str] = None, chat_id_blacklist: typing.List[str] = None):
        super().__init__(chat_id_whitelist, chat_id_blacklist)
        self._commands = [self.GALLERY_DELETE_COMMAND]
        self._gallery_db = gallery_db

    def matches(self, messenger: MessengerInterface, message: dict):
        # gallery delete command
        command = PipelineHelper.extract_command(messenger.get_message_text(message))
        return command in self._commands
    def _delete_image(self, chat_id: str, image_uuid: str):
        os.remove(utils.storage_path() + f"/gallery/{image_uuid}.blob")
        os.remove(utils.storage_path() + f"/gallery/{image_uuid}_thumb.png")
        self._gallery_db.delete_image(chat_id, image_uuid)
        
    def process(self, messenger: MessengerInterface, message: dict):
        try:
            # gallery delete command
            command = PipelineHelper.extract_command(messenger.get_message_text(message))
            if command == self.GALLERY_DELETE_COMMAND:
                messenger.mark_in_progress_0(message)
                chat_id = messenger.get_chat_id(message)
                
                # TODO add confirmation step
                images = self._gallery_db.get_images(chat_id)
                count = 0
                for image in images:
                    self._delete_image(chat_id, image["image_uuid"])
                    count += 1
                messenger.reply_message(message, f"{count} gallery images deleted for this group.")
                messenger.mark_in_progress_done(message)
                return
        except Exception as ex:
            logging.critical(ex, exc_info=True)  # log exception info at CRITICAL log level
            messenger.mark_in_progress_fail(message)
            return

    def get_help_text(self) -> str:
        return \
f"""*Gallery Deletation*
_#{self.GALLERY_DELETE_COMMAND}_ Deletes all images in the current gallery."""