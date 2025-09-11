"""Implementations of a pipeline for processing text and voice for homeassistant. """
import logging
import typing
import database
import time

from pipeline import PipelineInterface, PipelineHelper
from messenger import MessengerInterface


class GalleryDatabase:
    """Database to store images from group chats for a gallery. """

    def __init__(self):
        self._db = database.Database("gallery.db")
        self._create_tables()

    def _create_tables(self):
        cur = self._db.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS gallery (
                chat_id TEXT,
                sender TEXT,
                image_hash TEXT,
                time REAL,
                UNIQUE(chat_id, image_hash)
            )
            """)

        cur.execute("""
        CREATE INDEX IF NOT EXISTS gallery_chat_index ON gallery(chat_id)
        """)
        
        # create configuration table for group -> enabled/disabled
        cur.execute("""
            CREATE TABLE IF NOT EXISTS gallery_config (
                chat_id TEXT PRIMARY KEY,
                enabled INTEGER
            )
            """)
        self._db.commit()
    
    def is_enabled(self, chat_id: str) -> bool:
        """Returns if the gallery is enabled for a given chat_id

        Args:
            chat_id (str): The chat id from the messenger of the group

        Returns:
            bool: True if enabled, False if disabled or not set
        """
        cur = self._db.cursor()
        cur.execute("SELECT enabled FROM gallery_config WHERE chat_id = ? LIMIT 1", (chat_id,))
        row = cur.fetchone()
        if row is None:
            return False
        return row["enabled"] == 1
    
    def set_enabled(self, chat_id: str, enabled: bool) -> None:
        """Sets the gallery enabled or disabled for a given chat_id

        Args:
            chat_id (str): The chat id from the messenger of the group
            enabled (bool): True to enable, False to disable
        """
        cur = self._db.cursor()
        cur.execute("INSERT OR REPLACE INTO gallery_config (chat_id, enabled) VALUES (?, ?)",
                    (chat_id, 1 if enabled else 0))
        self._db.commit()

    def add_image(self, chat_id: str, sender: str, image_hash: str) -> None:
        """Adds an image to the gallery database

        Args:
            chat_id (str): The chat id from which the image is
            sender (str): The sender of the image
            image_hash (str): The hash of the image
        """
        cur = self._db.cursor()
        cur.execute("INSERT OR IGNORE INTO gallery (chat_id, sender, image_hash, time) VALUES (?, ?, ?, ?)",
                    (chat_id,
                    sender,
                    image_hash, 
                    time.time()))
        self._db.commit()

    def get_images(self, chat_id: str, count: int) -> typing.List[dict]:
        """Returns a list of the count newest images from a given chat. 

        Args:
            chat_id (str): The chat id from the messenger of the group
            count (group): Max number of images to get
        _type_: List of images from the chat
        """
        return_list = []
        for row in self._db.execute("SELECT chat_id, sender, image_hash FROM gallery \
                                  WHERE chat_id = ? ORDER BY `time` DESC LIMIT ?",
                                  (chat_id, count)):
            entry = {
                "chat_id": row["chat_id"],
                "sender": row["sender"],
                "image_hash": row["image_hash"]
            }
            return_list.append(entry)
        return return_list
class GalleryPipeline(PipelineInterface):
    """Pipe to store images in a gallery from group chats. """
    GALLERY_COMMAND = "gallery"

    def __init__(self, base_url: str):

        self._commands = [self.GALLERY_COMMAND]
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


    def process(self, messenger: MessengerInterface, message: dict):
        # we have an image that we might need to process
        if messenger.has_image_data(message):
                
            messenger.mark_in_progress_0(message)
            try:
                chat_id = messenger.get_chat_id(message)
                # TODO: only insert if no duplicate in db
                mime_type, image_data = messenger.download_media(message)
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
                    messenger.reply_message(message, f"Gallery is {'enabled' if enabled else 'disabled'} for this group\nGallery link: {self._base_url}/gallery")
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
"""*Gallery creation*
_#gallery on/off_ Enables or disables the storage of images sent to the group in a gallery.
_#gallery_ Shows if gallery is on or off and provides a link to the gallery."""
