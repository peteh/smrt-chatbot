import time
import logging

import requests
from .scheduled import AbstractScheduledTask
class CCCScheduledTask(AbstractScheduledTask):
    
    def __init__(self, messenger_manager, chat_ids):
        super().__init__(messenger_manager, chat_ids)
        logging.info("Initialized CCC Scheduled Task")
        
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/128.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        self._session = requests.Session()
        self._session.headers.update(headers)

    def run(self):
        while True:
            try:
                r = self._session.get("https://tickets.events.ccc.de/39c3/secondhand/?item=&sort=price_asc")

                if "You are now in our queue!" in r.text:
                    logging.debug("CCC: In queue, waiting...")
                    # need to refresh queue quickly < 1min
                    time.sleep(30)
                    continue
                if "No tickets available at the moment." in r.text:
                    logging.debug("CCC: No tickets available.")
                    #for chat_id in self.get_chat_ids():
                    #    messenger = self.get_messenger_manager().get_messenger_by_chatid(chat_id)
                    #    messenger.send_message(chat_id, "No Tickets available! Check https://tickets.events.ccc.de/39c3/secondhand/")
                    # no tickets, next try
                    time.sleep(30)
                    continue

                # Got tickets page
                logging.info("CCC: Found tickets on page!")
                for chat_id in self.get_chat_ids():
                    messenger = self.get_messenger_manager().get_messenger_by_chatid(chat_id)
                    messenger.send_message(chat_id, "Tickets available! Check https://tickets.events.ccc.de/39c3/secondhand/")
                    time.sleep(3*60)

            except Exception as e:
                logging.error(f"Error in CCCScheduledTask: {e}")
                time.sleep(60)
