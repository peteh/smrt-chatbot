import db
import time
import os

db = db.Database('testdata.sqlite')
db.createTables()
db.addGroupMessage("abc", "Pete", "lalala1")
time.sleep(1)
db.addGroupMessage("abc", "Pete1", "lalala2")
time.sleep(1)
db.addGroupMessage("abc", "Pete3", "lalala3")
time.sleep(1)
db.getGroupMessages("abc", 10)
os.remove('testdata.sqlite')