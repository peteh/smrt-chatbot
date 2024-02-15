import time
from datetime import datetime
import threading
import logging
import json
import requests
import messenger

logging.basicConfig(level=logging.INFO)

class SenateStockNotification():
    DELAY_S = 30
    RUN_EVERY_S = 60*60 # once per hour
    MIN_VALUE_FOR_REPORTING = 50000

    # TODO: dirty hack to respond to messages
    response_wa_msg = {'chatId': '491726060318-1611969093@g.us'}


    def __init__(self, messenger : messenger.MessengerInterface) -> None:
        # TODO: init this properly
        self._last_created_at = self.get_second_newest()
        self._messenger = messenger
        self._thread = threading.Thread(target=self.run)

    def get_newest(self):
        data = self.get_data()
        newest = datetime(year=1000, month=1, day=1)
        for transaction in data:
            transaction_created_at = self._to_time(transaction["created_at"])

            if transaction_created_at > newest:
                newest = transaction_created_at

        return newest

    def get_second_newest(self):
        data = self.get_data()
        newest = datetime(year=1000, month=1, day=1)
        second_newest = datetime(year=1000, month=1, day=1)
        for transaction in data:
            transaction_created_at = self._to_time(transaction["created_at"])

            if transaction_created_at > newest:
                second_newest = newest
                newest = transaction_created_at
            elif transaction_created_at > second_newest:
                second_newest = transaction_created_at

        return second_newest

    def get_data(self):
        url = "https://phx.unusualwhales.com/api/senate_stocks"
        #url = "https://phx.unusualwhales.com/api/senate_stocks_search_full?search=PELOSI"
        headers = {
            #"Accept-Encoding": "gzip, deflate, br",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
            #"Authorization": "Bearer J2NHFYPcKbRGk8SnMnKM_2grvqFWVGuW5-RcX69DRZ2ZfXi40IgwH-RalEr11CIL",
            "Content-Type": "application/json",
            "Referer": "https://unusualwhales.com/"
        }

        r = requests.get(url, headers = headers, timeout=120)
        #with open("data.json", "w") as fp:
        #    fp.write(json.dumps(r.json(), indent=4))
        return r.json()["senate_stocks"]

    def _to_time(self, date_string: str):
        # Convert string to datetime object
        datetime_object = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S.%fZ")
        return datetime_object

    def get_transaction_value(self, transaction_amount: str) -> tuple[float, float]:
        # $1,000 - $15,000
        tr_value = transaction_amount.replace("$", "").replace(",", "").split(" - ")
        
        value_from = float(tr_value[0])
        value_to = float(tr_value[1])
        return (value_from, value_to)
        
        
    def task(self):
        data = self.get_data()
        newest = self._last_created_at
        for transaction in data:
            transaction_created_at = self._to_time(transaction["created_at"])
            if transaction_created_at > self._last_created_at:
                newest = transaction_created_at
                logging.debug(transaction)
                from_value, to_value = self.get_transaction_value(transaction['amounts'])
                if from_value >= self.MIN_VALUE_FOR_REPORTING:
                    transaction_txt = f"{transaction['transaction_date']}: {transaction['reporter']} {transaction['txn_type']} {transaction['symbol']} for {transaction['amounts']}"
                    info_msg = f"SENATE STOCK TRADING:\n{transaction_txt}\nNotes: {transaction['notes']}\nreported: {transaction['filed_at_date']}"
                    self._messenger.send_message_to_group(self.response_wa_msg, info_msg)
        self._last_created_at = newest

    def run(self):
        time.sleep(self.DELAY_S)
        while True:
            try:
                logging.info("Downloading latest senate stock data")
                self.task()
            except Exception as ex:
                logging.critical(ex, exc_info=True)
            time.sleep(self.RUN_EVERY_S)

    def run_async(self):
        self._thread.start() 
