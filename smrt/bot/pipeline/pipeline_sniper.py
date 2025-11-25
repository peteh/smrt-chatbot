import time
import logging

import requests
from bs4 import BeautifulSoup
from .scheduled import AbstractScheduledTask

class AbstractSniperTask(AbstractScheduledTask):
    def __init__(self, messenger_manager, chat_ids, language="en-US"):
        super().__init__(messenger_manager, chat_ids)

        self._headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64; rv:144.0) Gecko/20100101 Firefox/144.0"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": f"{language},en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }

    def new_session(self):
        session = requests.Session()
        session.headers.update(self._headers)
        return session

class NetcupScheduledTask(AbstractSniperTask):

    def __init__(self, messenger_manager, chat_ids):
        super().__init__(messenger_manager, chat_ids, "de-DE")
        logging.info("Initialized Netcup Scheduled Task")

    def new_session(self):
        session = requests.Session()
        session.headers.update(self._headers)
        return session
    
    def get_products(self, session: requests.Session):
        r = session.get("https://www.netcup.com/de/deals/black-friday")
        if "unschlagbare Rabatte. Sei dabei und sichere dir dein Schnäppchen!" not in r.text:
            logging.debug("Netcup Black Friday page not ready, waiting...")
            raise Exception("Netcup Black Friday page not ready")
        new_products = {}
        soup = BeautifulSoup(r.text, "html.parser")
        # Select all elements with the class "deal-card-container"
        cards = soup.select(".deal-card-container")
        for card in cards:
            #print(card)           # the full element
            h3 = card.find("h3")
            product = h3.get_text(strip=True)
            a = card.find("a", href=True)
            product_link = f"https://www.netcup.com/{a['href']}"
            new_products[product] = product_link
        return new_products

    def run(self):
        counter = 0
        session = self.new_session()
        # initialize old products with current state
        old_products = self.get_products(session)

        while True:
            try:
                counter += 1
                if counter % 40 == 0:
                    session = self.new_session()

                # grab current products
                new_products = self.get_products(session)

                # Figure out what's removed
                for product, link in old_products.items():
                    if product not in new_products:
                        logging.debug(f"Netcup Product removed: {product} - {link}")
                        for chat_id in self.get_chat_ids():
                            messenger = self.get_messenger_manager().get_messenger_by_chatid(chat_id)
                            messenger.send_message(chat_id, f"Netcup Black Friday product removed: {product}")

                # Figure out what's new
                for product, link in new_products.items():
                    if product not in old_products:
                        logging.debug(f"Netcup New product found: {product} - {link}")
                        for chat_id in self.get_chat_ids():
                            messenger = self.get_messenger_manager().get_messenger_by_chatid(chat_id)
                            messenger.send_message(chat_id, f"Netcup Black Friday new product: {product} - {link}")
                old_products = new_products.copy()
                # wait for a bit before checking again
                time.sleep(30)
            except Exception as e:
                logging.error(f"Error in Netcup Black Friday: {e}")
                time.sleep(5*60)


class CCCScheduledTask(AbstractSniperTask):

    def __init__(self, messenger_manager, chat_ids):
        super().__init__(messenger_manager, chat_ids)
        logging.info("Initialized CCC Scheduled Task")

    def run(self):
        counter = 0
        session = self.new_session()
        while True:
            try:
                counter += 1
                if counter % 40 == 0:
                    session = self.new_session()
                r = session.get("https://tickets.events.ccc.de/39c3/secondhand/?item=&sort=price_asc")

                if "You are now in our queue!" in r.text:
                    logging.debug("CCC: In queue, waiting...")
                    # need to refresh queue quickly < 1min
                    time.sleep(30)
                    continue
                if "No tickets available at the moment." in r.text \
                    or "Derzeit sind keine Tickets verfügbar. Schau später noch mal vorbei!" in r.text:
                    logging.debug("CCC: No tickets available.")
                    #for chat_id in self.get_chat_ids():
                    #    messenger = self.get_messenger_manager().get_messenger_by_chatid(chat_id)
                    #    messenger.send_message(chat_id, "No Tickets available! Check https://tickets.events.ccc.de/39c3/secondhand/")
                    # no tickets, next try
                    time.sleep(30)
                    continue

                # Got tickets page
                logging.info("CCC: Found tickets on page!")
                logging.debug(r.text)
                for chat_id in self.get_chat_ids():
                    messenger = self.get_messenger_manager().get_messenger_by_chatid(chat_id)
                    messenger.send_message(chat_id, "Tickets available! Check https://tickets.events.ccc.de/39c3/secondhand/")
                    time.sleep(3*60)

            except Exception as e:
                logging.error(f"Error in CCCScheduledTask: {e}")
                time.sleep(5*60)
