"""A database implementation to store and retrieve messages. """
import time
import os
from typing import List
import sqlite3

class Database:
    """Database to store and retrieve messages. """
    def __init__(self, data_file):
        data_file_exists = False
        if os.path.exists(data_file):
            data_file_exists = True
        self._con = sqlite3.connect(data_file, check_same_thread = False)
        self._con.row_factory = sqlite3.Row   # Here's the magic!
        if not data_file_exists:
            self._create_tables()

    def _create_tables(self):
        cur = self._con.cursor()
        cur.execute("CREATE TABLE groups (groupId, sender, message, time)")

    def add_group_message(self, group_id: str, sender: str, message: str) -> None:
        """Adds a group message to the database

        Args:
            group_id (str): The group id from which the message is
            sender (str): The sender of the message
            message (str): The actual message
        """
        cur = self._con.cursor()
        cur.execute("INSERT INTO groups (groupId, sender, message, time) VALUES (?, ?, ?, ?)",
                    (group_id,
                    sender,
                    message, time.time()))
        self._con.commit()

    def get_group_messages(self, group_id: str, count: int) -> List[dict]:
        """Returns a list of the count newest group messages from a given group. 

        Args:
            group_id (str): _description_
            count (group): _description_

        Returns:
            _type_: List of messages from the group
        """
        return self._con.execute("SELECT groupId, sender, message FROM groups \
                                 WHERE groupId = ? ORDER BY `time` LIMIT ?",
                                 (group_id, count))
