import time
import logging

import requests
import random
import json
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
    
    def get_products(self, session: requests.Session):
        r = session.get("https://www.netcup.com/de/deals/black-friday")
        if "unschlagbare Rabatte. Sei dabei und sichere dir dein Schnäppchen!" not in r.text:
            logging.debug("Netcup Black Friday page not ready, waiting...")
            raise RuntimeError("Netcup Black Friday page not ready")
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
                logging.debug(f"Netcup Black Friday products found: {len(new_products)}")

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
                
                if r.status_code != 200:
                    logging.debug(f"CCC: Unexpected status code {r.status_code}, waiting...")
                    time.sleep(60)
                    continue

                if "Ticket marketplace is not currently active" in r.text:
                    logging.debug("CCC: Ticket marketplace not active, waiting...")
                    time.sleep(5*60)
                    continue

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


class KleinanzeigenScheduledTask(AbstractSniperTask):

    def __init__(self, keyword: str, messenger_manager, chat_ids):
        super().__init__(messenger_manager, chat_ids)
        self._keyword = keyword
        logging.info(f"Initialized Kleinzeigen Scheduled Task with keyword: '{self._keyword}'")

    def parse_listing(self, article):
        BASE_URL = "https://www.kleinanzeigen.de"
        data = {}

        # ad ID
        data["ad_id"] = article.get("data-adid")

        # href
        href = article.get("data-href")
        if href:
            data["url"] = BASE_URL + href
        else:
            data["url"] = None

        # title
        title_el = article.select_one(".aditem-main--middle h2 a")
        data["title"] = title_el.get_text(strip=True) if title_el else None

        # price
        price_el = article.select_one(".aditem-main--middle--price-shipping--price")
        data["price"] = price_el.get_text(strip=True) if price_el else None

        # location
        loc_el = article.select_one(".aditem-main--top--left")
        data["location"] = loc_el.get_text(strip=True) if loc_el else None

        # timestamp / posting date
        ts_el = article.select_one(".aditem-main--top--right")
        data["timestamp"] = ts_el.get_text(strip=True) if ts_el else None

        # description
        desc_el = article.select_one(".aditem-main--middle--description")
        data["description"] = desc_el.get_text(" ", strip=True) if desc_el else None

        # shipping (optional)
        shipping_el = article.select_one(".simpletag")
        data["shipping"] = shipping_el.get_text(strip=True) if shipping_el else None

        # parse JSON-LD for high-res image
        script_el = article.select_one("script[type='application/ld+json']")
        if script_el:
            try:
                ld = json.loads(script_el.string)
                data["image"] = ld.get("contentUrl")
            except Exception:
                data["image"] = None
        else:
            data["image"] = None

        return data

    def get_articles(self, session: requests.Session):
        keyword_encoded = requests.utils.quote(self._keyword)
        r = session.get(f"https://www.kleinanzeigen.de/s-anzeige:angebote/{keyword_encoded}/k0")
        if r.status_code != 200:
            logging.debug(f"CCC: Unexpected status code {r.status_code}, waiting...")
            raise RuntimeError("Kleinanzeigen page not reachable")
        results = {}
        soup = BeautifulSoup(r.text, "html.parser")
        for article_soup in soup.select("article.aditem"):
            article = self.parse_listing(article_soup)
            article_id = article.get("ad_id")
            if article_id:
                results[article_id] = article
        return results

    def run(self):
        counter = 0
        session = self.new_session()
        old_articles = self.get_articles(session)
        while True:
            try:
                counter += 1
                if counter % 40 == 0:
                    session = self.new_session()

                new_articles = self.get_articles(session)
                logging.debug(f"Kleinanzeigen articles found: {len(new_articles)}")
                for article_id, article in new_articles.items():
                    if article_id not in old_articles:
                        logging.info(f"Kleinanzeigen New article found: {article['title']} - {article['url']}")
                        for chat_id in self.get_chat_ids():
                            messenger = self.get_messenger_manager().get_messenger_by_chatid(chat_id)
                            message = f"Kleinanzeigen new article:\n{article['title']}\nPrice: {article['price']}\nLocation: {article['location']}\n{article['url']}"
                            messenger.send_message(chat_id, message)
                old_articles = new_articles.copy()
                time.sleep(random.randint(45, 90))

            except Exception as e:
                logging.error(f"Error in CCCScheduledTask: {e}")
                time.sleep(5*60)

