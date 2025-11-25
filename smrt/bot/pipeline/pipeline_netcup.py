import time
import logging

import requests
from bs4 import BeautifulSoup
from .scheduled import AbstractScheduledTask

class NetcupScheduledTask(AbstractScheduledTask):

    def __init__(self, messenger_manager, chat_ids):
        super().__init__(messenger_manager, chat_ids)
        logging.info("Initialized Netcup Scheduled Task")

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
        self._old_products = {}

    def run(self):
        while True:
            try:
                r = self._session.get("https://www.netcup.com/de/deals/black-friday")

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

                # Figure out what's removed
                for product, link in self._old_products.items():
                    if product not in new_products:
                        logging.debug(f"Netcup Product removed: {product} - {link}")
                        for chat_id in self.get_chat_ids():
                            messenger = self.get_messenger_manager().get_messenger_by_chatid(chat_id)
                            messenger.send_message(chat_id, f"Netcup Black Friday product removed: {product}")

                # Figure out what's new
                for product, link in new_products.items():
                    if product not in self._old_products:
                        logging.debug(f"Netcup New product found: {product} - {link}")
                        for chat_id in self.get_chat_ids():
                            messenger = self.get_messenger_manager().get_messenger_by_chatid(chat_id)
                            messenger.send_message(chat_id, f"Netcup Black Friday new product: {product} - {link}")
                self._old_products = new_products.copy()
                # wait for a bit before checking again
                time.sleep(30)
            except Exception as e:
                logging.error(f"Error in Netcup Black Friday: {e}")
                time.sleep(60)
