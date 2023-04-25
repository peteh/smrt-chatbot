import db
import time
import os

db = db.Database('testdata.sqlite')
db.createTables()
db.add_group_message("abc", "Pete", "lalala1")
time.sleep(1)
db.add_group_message("abc", "Pete1", "lalala2")
time.sleep(1)
db.add_group_message("abc", "Pete3", "lalala3")
time.sleep(1)
db.get_group_messages("abc", 10)
os.remove('testdata.sqlite')