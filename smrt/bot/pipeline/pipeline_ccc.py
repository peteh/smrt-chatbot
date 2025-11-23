import time
import logging

import requests
from .scheduled import AbstractScheduledTask
session = requests.Session()

class CCCScheduledTask(AbstractScheduledTask):
    
    def __init__(self, messenger_manager, chat_ids):
        super().__init__(messenger_manager, chat_ids)
        logging.info("Initialized CCC Scheduled Task")

    def run(self):
        session = requests.Session()

        while True:
            try:
                r = session.get("https://tickets.events.ccc.de/39c3/secondhand/?item=&sort=price_asc")
                print(r.status_code)

                if "You are now in our queue!" in r.text:
                    logging.debug("In queue, waiting...")
                    # need to refresh queue quickly < 1min
                    time.sleep(30)
                    continue
                if "No tickets available at the moment." in r.text:
                    logging.debug("No tickets available.")
                    
                    # no tickets, next try
                    time.sleep(3*60)
                    continue

                # Got tickets page
                logging.info("Found tickets on page!")
                for chat_id in self.get_chat_ids():
                    messenger = self.get_messenger_manager().get_messenger_by_chatid(chat_id)
                    messenger.send_message(chat_id, "Tickets available! Check https://tickets.events.ccc.de/39c3/secondhand/")
                    time.sleep(3*60)

            except Exception as e:
                logging.error(f"Error in CCCScheduledTask: {e}")
                time.sleep(60)
