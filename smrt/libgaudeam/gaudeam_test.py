import logging
import yaml
import json
from pathlib import Path
from datetime import datetime, timedelta
from igitur import GaudeamSession, GaudeamCalendar
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

config_file = open("config.yml", "r", encoding="utf-8")
configuration = yaml.safe_load(config_file)
config_file.close()

email = configuration["gaudeam"][0]["user_email"]
password = configuration["gaudeam"][0]["user_password"]
session = GaudeamSession.with_user_auth(email, password)

calendar = GaudeamCalendar(session)

today = datetime.now()
past = today - timedelta(days=365)

events = calendar.global_calendar(past, today)
base_path = Path("/home/pete/Downloads/test_images/")
for event in events:
    date_str = event.get_start_datetime().strftime("%Y-%m-%d")
    folder_name = f"{date_str} {event.get_title()}"
    event_path = base_path / folder_name
    event.download_media(event_path)
