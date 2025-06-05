"""Main application"""
import logging
from decouple import config
import smrt_bot
logging.basicConfig(level=logging.DEBUG)
root = logging.getLogger()
root.setLevel(logging.DEBUG)

# private or bot (default)
launch = config("LAUNCH", "bot")
logging.info("Launching BOT")
smrt_bot.run()
