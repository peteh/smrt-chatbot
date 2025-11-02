import logging
import yaml
import json
from pathlib import Path
from datetime import datetime, timedelta
from gaudeam import GaudeamDriveFolder, GaudeamSession, GaudeamCalendar, GaudeamResizedImageUploader, GaudeamEvent, GaudeamMedia
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

config_file = open("config.yml", "r", encoding="utf-8")
configuration = yaml.safe_load(config_file)
config_file.close()


#session = GaudeamSession.with_user_auth(email, password)

subdomain = configuration["gaudeam"][0]["gaudeam_subdomain"]
session_cookie = configuration["gaudeam"][0]["gaudeam_session"]
session = GaudeamSession(session_cookie, subdomain)
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
