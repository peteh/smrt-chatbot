"""Main application"""
import logging
from decouple import config
import smrt_bot
import smrt_private
logging.basicConfig(level=logging.DEBUG)
root = logging.getLogger()
root.setLevel(logging.DEBUG)

# private or bot (default)
launch = config("LAUNCH", "bot")

if launch == "bot":
    logging.info("Launching BOT")
    smrt_bot.run()
elif launch == "private":
    logging.info("Launching PRIVATE")
    smrt_private.run()
