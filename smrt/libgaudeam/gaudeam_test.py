import logging
import yaml
import datetime
from gaudeam import GaudeamDriveFolder, GaudeamSession, GaudeamCalendar
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

config_file = open("config.yml", "r", encoding="utf-8")
configuration = yaml.safe_load(config_file)
config_file.close()


#session = GaudeamSession.with_user_auth(email, password)

subdomain = configuration["gaudeam"][0]["gaudeam_subdomain"]
session_cookie = configuration["gaudeam"][0]["gaudeam_session"]
session = GaudeamSession(session_cookie, subdomain)
gaudeam = GaudeamCalendar(session)

def get_events(gaudeam: GaudeamCalendar, days: int) -> list[dict]:
    # todays date in format dd.mm
    today_date = datetime.datetime.now()
    end_date = today_date + datetime.timedelta(days=days)
    logging.debug(f"Fetching events from {today_date} to {end_date}")
    events = gaudeam.global_calendar(today_date.date(), end_date.date(), filter_birthdays=True)
    events = sorted(events, key=lambda x: gaudeam.date_string_to_datetime(x["start"]))
    return events

for event in get_events(gaudeam, 5):
    print(event["title"])
    print(event["url"])
    formatted = gaudeam.date_string_to_datetime(event["start"]).strftime("%Y-%m-%d %H:%M")
    print(formatted)
    print("")