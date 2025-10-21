"""A database implementation to store and retrieve messages. """
import time
import typing
import sqlite3
import threading
import uuid
from pathlib import Path

class Database:
    """Database to store and retrieve messages. """
    def __init__(self, storage_path: Path, database_name: str):
        file_path = storage_path / f"{database_name}.sqlite"
        self._con = sqlite3.connect(file_path, check_same_thread = False)
        self._con.row_factory = sqlite3.Row   # Here's the magic!

    def cursor(self):
        return self._con.cursor()

    def commit(self):
        self._con.commit()

    def close(self):
        self._con.close()

class MessageDatabase():
    
    def __init__(self, storage_path: Path):
        self._db = Database(storage_path, "message.db")
        self._lock = threading.Lock()  # Mutex for all DB operations
        self._create_tables()
    
    def _create_tables(self):
        with self._lock:
            cur = self._db.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    chat_id TEXT,
                    sender,
                    message,
                    time
                )
                """)

            cur.execute("""
            CREATE INDEX IF NOT EXISTS group_index ON messages(chat_id)
            """)

    def add_message(self, chat_id: str, sender: str, message: str) -> None:
        """Adds a group message to the database

        Args:
            chat_id (str): The chat id from which the message is
            sender (str): The sender of the message
            message (str): The actual message
        """
        with self._lock:
            cur = self._db.cursor()
            cur.execute("INSERT INTO messages (chat_id, sender, message, time) VALUES (?, ?, ?, ?)",
                        (chat_id,
                        sender,
                        message, time.time()))
            self._db.commit()

    def get_group_messages(self, chat_id: str, count: int) -> typing.List[dict]:
        """Returns a list of the count newest group messages from a given group. 

        Args:
            group_id (str): The group id from the messenger of the group
            count (group): Max number of messages to get

        Returns:
            _type_: List of messages from the group
        """
        with self._lock:
            cur = self._db.cursor()
            return_list = []
            for row in cur.execute("SELECT group_id, sender, message FROM groups \
                                    WHERE group_id = ? ORDER BY `time` DESC LIMIT ?",
                                    (chat_id, count)):
                entry = {
                    "chat_id": row['chat_id'],
                    "sender": row['sender'],
                    "message": row['message']
                }
                return_list.append(entry)
            return_list.reverse()
            return return_list

class GalleryDatabase:
    """Database to store images from group chats for a gallery. """

    def __init__(self, storage_path: Path):
        self._db = Database(storage_path, "gallery.db")
        self._storage_path = storage_path / "gallery"
        if not self._storage_path.exists():
            self._storage_path.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()  # Mutex for all DB operations
        self._create_tables()

    def _create_tables(self):
        with self._lock:
            cur = self._db.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS gallery (
                    chat_id TEXT,
                    sender TEXT,
                    mime_type VARCHAR(32),
                    image_uuid VARCHAR(36),
                    image_hash VARCHAR(64),
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
                    uuid VARCHAR(36),
                    enabled INTEGER
                )
                """)
            self._db.commit()

    def get_storage_path(self) -> Path:
        """Returns the storage path for gallery images

        Returns:
            Path: The storage path
        """
        return self._storage_path

    def get_gallery_uuid_from_chat_id(self, chat_id: str) -> str:
        """Returns the gallery uuid for a given chat_id

        Args:
            chat_id (str): The chat id from the messenger of the group  
        Returns:
            str: The gallery uuid
        """
        with self._lock:
            cur = self._db.cursor()
            cur.execute("SELECT uuid FROM gallery_config WHERE chat_id = ? LIMIT 1", (chat_id,))
            row = cur.fetchone()
            if row is None:
                return None
            return row["uuid"]
    
    def get_chat_id_from_gallery_uuid(self, gallery_uuid: str) -> str:
        """Returns the chat_id for a given gallery uuid

        Args:
            gallery_uuid (str): The gallery uuid
        Returns:
            str: The chat id from the messenger of the group
        """
        with self._lock:
            cur = self._db.cursor()
            cur.execute("SELECT chat_id FROM gallery_config WHERE uuid = ? LIMIT 1", (gallery_uuid,))
            row = cur.fetchone()
            if row is None:
                return None
            return row["chat_id"]
    
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
            cur.execute("SELECT uuid FROM gallery_config WHERE chat_id = ? LIMIT 1", (chat_id,))
            row = cur.fetchone()
            if row is None or row["uuid"] is None:
                uuid_val = str(uuid.uuid4())
            else:
                uuid_val = row["uuid"]
            cur.execute("INSERT OR REPLACE INTO gallery_config (chat_id, uuid, enabled) VALUES (?, ?, ?)",
                        (chat_id, uuid_val, 1 if enabled else 0))
            self._db.commit()


    def has_image(self, chat_id: str, image_hash: str) -> bool:
        """Checks if an image with the given hash already exists in the database for the given chat_id

        Args:
            chat_id (str): The chat id from which the image is
            image_hash (str): The hash of the image
        Returns:
            bool: True if the image exists, False otherwise
        """
        with self._lock:
            cur = self._db.cursor()
            cur.execute("SELECT 1 FROM gallery WHERE chat_id = ? AND image_hash = ? LIMIT 1",
                        (chat_id, image_hash))
            row = cur.fetchone()
            return row is not None

    def add_image(self, chat_id: str, sender: str, mime_type: str, image_uuid: str, image_hash: str) -> None:
        """Adds an image to the gallery database

        Args:
            chat_id (str): The chat id from which the image is
            sender (str): The sender of the image
            mime_type (str): The mime type of the image
            image_uuid (str): The uuid of the image
            image_hash (str): The hash of the image
        """
        with self._lock:
            cur = self._db.cursor()
            cur.execute("INSERT OR IGNORE INTO gallery (chat_id, sender, mime_type, image_uuid, image_hash, time) VALUES (?, ?, ?, ?, ?, ?)",
                        (chat_id,
                        sender,
                        mime_type,
                        image_uuid,
                        image_hash,
                        time.time()))
            self._db.commit()

    def get_images(self, chat_id : str) -> typing.List[dict]:
        """Returns a list of the count newest images from a given chat. 

        Args:
            chat_id (str): The chat id from the messenger of the group
            count (group): Max number of images to get
        _type_: List of images from the chat
        """
        with self._lock:
            return_list = []

            for row in self._db.cursor().execute("SELECT chat_id, sender, mime_type, image_uuid, image_hash, time FROM gallery \
                                    WHERE chat_id = ? ORDER BY `time` ASC",
                                    (chat_id, )):
                entry = {
                    "chat_id": row["chat_id"],
                    "sender": row["sender"],
                    "mime_type": row["mime_type"],
                    "image_uuid": row["image_uuid"],
                    "image_hash": row["image_hash"],
                    "time": row["time"]
                }
                return_list.append(entry)
        return return_list

    def get_image(self, chat_id: str, image_uuid: str) -> dict:
        """Returns a specific image entry from a given chat_id

        Args:
            chat_id (str): The chat id from which the image is to be retrieved
            image_uuid (str): The uuid of the image to be retrieved
        Returns:
            dict: The image entry or None if not found
        """
        with self._lock:
            cur = self._db.cursor()
            cur.execute("SELECT chat_id, sender, mime_type, image_uuid, image_hash, time FROM gallery \
                        WHERE chat_id = ? AND image_uuid = ? LIMIT 1",
                        (chat_id, image_uuid))
            row = cur.fetchone()
            if row is None:
                return None
            entry = {
                "chat_id": row["chat_id"],
                "sender": row["sender"],
                "mime_type": row["mime_type"],
                "image_uuid": row["image_uuid"],
                "image_hash": row["image_hash"],
                "time": row["time"]
            }
            return entry

    def delete_image(self, chat_id: str, image_uuid: str) -> None:
        """Deletes a specific image from a given chat_id

        Args:
            chat_id (str): The chat id from which the image is to be deleted
            image_uuid (str): The uuid of the image to be deleted
        """
        with self._lock:
            cur = self._db.cursor()
            cur.execute("DELETE FROM gallery WHERE chat_id = ? AND image_uuid = ?", (chat_id, image_uuid))
            self._db.commit()
