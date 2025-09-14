"""Implementations of a pipeline for processing text and voice for homeassistant. """
import logging
import typing
import hashlib
import time
import uuid
import io
import threading
from PIL import Image
import database


from pipeline import PipelineInterface, PipelineHelper
from messenger import MessengerInterface


class GalleryDatabase:
    """Database to store images from group chats for a gallery. """

    def __init__(self):
        self._db = database.Database("gallery.db")
        self._lock = threading.Lock()  # Mutex for all DB operations
        self._create_tables()

    def _create_tables(self):
        with self._lock:
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
        with self._lock:
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
        with self._lock:
            cur = self._db.cursor()
            cur.execute("INSERT OR REPLACE INTO gallery_config (chat_id, enabled) VALUES (?, ?)",
                        (chat_id, 1 if enabled else 0))
            self._db.commit()

    def add_image(self, chat_id: str, sender: str, image_uuid: str) -> None:
        """Adds an image to the gallery database

        Args:
            chat_id (str): The chat id from which the image is
            sender (str): The sender of the image
            image_hash (str): The hash of the image
        """
        with self._lock:
            cur = self._db.cursor()
            cur.execute("INSERT OR IGNORE INTO gallery (chat_id, sender, image_hash, time) VALUES (?, ?, ?, ?)",
                        (chat_id,
                        sender,
                        image_uuid, 
                        time.time()))
            self._db.commit()

    def get_images(self, chat_id : str, count: int) -> typing.List[dict]:
        """Returns a list of the count newest images from a given chat. 

        Args:
            chat_id (str): The chat id from the messenger of the group
            count (group): Max number of images to get
        _type_: List of images from the chat
        """
        with self._lock:
            return_list = []
            
            for row in self._db.cursor().execute("SELECT chat_id, sender, image_hash FROM gallery \
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

    def __init__(self, gallery_db: GalleryDatabase, base_url: str):

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

    def process_image_thumb(self, image_data) -> str:
        """Processes the image for thumb and storage

        Args:
            image_data (_type_): Byte data of the image

        Returns:
            str: _description_
        """
        file_uuid = uuid.uuid4() 
        # TODO: proper storage handling
        image_filename = f"gallery/{file_uuid}.blob"
        thumb_filename = f"gallery/{file_uuid}_thumb.blob"
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
                # TODO: check if high quality image
                # TODO: only insert if no duplicate in db
                mime_type, image_data = messenger.download_media(message)
                
                if mime_type not in ["image/png", "image/jpeg", "image/jpg"]:
                    # TODO marked as skipped
                    messenger.mark_skipped(message)
                    return
                
                # Compute MD5 hash
                md5_hash = hashlib.md5(image_data).hexdigest()
        
                # Load image from binary data
                img = Image.open(io.BytesIO(image_data))

                # Get width and height
                width, height = img.size
                
                if width < 1024 or height < 1024:
                    messenger.mark_skipped(message)
                    return
                
                file_uuid = self.process_image_thumb(image_data)
                self._gallery_db.add_image(chat_id, messenger.get_sender_name(message), file_uuid)
                
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
