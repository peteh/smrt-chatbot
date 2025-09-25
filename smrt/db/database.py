"""A database implementation to store and retrieve messages. """
import time
import os
import typing
import sqlite3
import threading
import smrt.utils.utils as utils

class Database:
    """Database to store and retrieve messages. """
    def __init__(self, database_name):
        file_path = utils.storage_path() + database_name + ".sqlite"
        self._con = sqlite3.connect(file_path, check_same_thread = False)
        self._con.row_factory = sqlite3.Row   # Here's the magic!

    def cursor(self):
        return self._con.cursor()
    
    def commit(self):
        self._con.commit()
    
    def close(self):
        self._con.close()

class MessageDatabase():
    
    def __init__(self, db: Database):
        self._db = db
    
    def _create_tables(self):
        cur = self._db.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                group_id,
                sender,
                message,
                time
            )
            """)

        cur.execute("""
        CREATE INDEX IF NOT EXISTS group_index ON groups(group_id)
        """)

    def add_group_message(self, group_id: str, sender: str, message: str) -> None:
        """Adds a group message to the database

        Args:
            group_id (str): The group id from which the message is
            sender (str): The sender of the message
            message (str): The actual message
        """
        cur = self._db.cursor()
        cur.execute("INSERT INTO groups (group_id, sender, message, time) VALUES (?, ?, ?, ?)",
                    (group_id,
                    sender,
                    message, time.time()))
        self._db.commit()

    def get_group_messages(self, group_id: str, count: int) -> typing.List[dict]:
        """Returns a list of the count newest group messages from a given group. 

        Args:
            group_id (str): The group id from the messenger of the group
            count (group): Max number of messages to get

        Returns:
            _type_: List of messages from the group
        """
        return_list = []
        for row in self._db.execute("SELECT group_id, sender, message FROM groups \
                                 WHERE group_id = ? ORDER BY `time` DESC LIMIT ?",
                                 (group_id, count)):
            entry = {
                "group_id": row['group_id'],
                "sender": row['sender'],
                "message": row['message']
            }
            return_list.append(entry)
        return_list.reverse()
        return return_list

class GalleryDatabase:
    """Database to store images from group chats for a gallery. """

    def __init__(self):
        self._db = Database("gallery.db")
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

    def get_images(self, chat_id : str, count: int) -> typing.List[dict]:
        """Returns a list of the count newest images from a given chat. 

        Args:
            chat_id (str): The chat id from the messenger of the group
            count (group): Max number of images to get
        _type_: List of images from the chat
        """
        with self._lock:
            return_list = []
            
            for row in self._db.cursor().execute("SELECT chat_id, sender, image_uuid FROM gallery \
                                    WHERE chat_id = ? ORDER BY `time` DESC LIMIT ?",
                                    (chat_id, count)):
                entry = {
                    "chat_id": row["chat_id"],
                    "sender": row["sender"],
                    "image_hash": row["image_hash"]
                }
                return_list.append(entry)
            return return_list
