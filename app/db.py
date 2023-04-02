import sqlite3
import time
import os


class Database:
    def __init__(self, dataFile):
        dataFileExists = False
        if os.path.exists(dataFile):
            dataFileExists = True
        self._con = sqlite3.connect(dataFile, check_same_thread = False)
        self._con.row_factory = sqlite3.Row   # Here's the magic!
        if not dataFileExists:
            self._createTables()
    
    def _createTables(self):
        cur = self._con.cursor()
        cur.execute("CREATE TABLE groups (groupId, sender, message, time)")

    def addGroupMessage(self, groupId, sender, message):
        cur = self._con.cursor()
        cur.execute("INSERT INTO groups (groupId, sender, message, time) VALUES (?, ?, ?, ?)", 
                    (groupId, 
                    sender, 
                    message, time.time()))
        self._con.commit()
    
    def getGroupMessages(self, groupId, count):
        return self._con.execute("SELECT groupId, sender, message FROM groups WHERE groupId = ? ORDER BY `time` LIMIT ?", (groupId, count))


