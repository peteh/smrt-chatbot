
import time
import os
import unittest
import smrt.db.database as database
import smrt.utils.utils as utils

class DatabaseTests(unittest.TestCase):
    """Test cases for db class"""

    def test_listing_when_more_data_inserted_then_read_newest(self):
        """Tests if the db resturns the correct messages"""
        # arrange
        db = database.Database('testdata')
        msgDB = database.MessageDatabase(db)
        # act
        msgDB.add_group_message("abc", "Pete1", "lalala1")
        time.sleep(1)
        msgDB.add_group_message("abc", "Pete2", "lalala2")
        time.sleep(1)
        msgDB.add_group_message("abc", "Pete3", "lalala3")
        time.sleep(1)
        rows = msgDB.get_group_messages("abc", 2)

        # assert
        self.assertEqual(rows[0]["sender"], "Pete2")
        self.assertEqual(rows[1]["sender"], "Pete3")
        # cleanup
        os.remove(utils.storage_path() + "testdata.sqlite")
