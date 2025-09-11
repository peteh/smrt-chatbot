"""A database implementation to store and retrieve messages. """
import time
import os
from typing import List
import sqlite3
import utils

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

    def get_group_messages(self, group_id: str, count: int) -> List[dict]:
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
