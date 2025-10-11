"""Implementations of a pipeline for processing data from Gaudeam. """
import logging
import typing
import datetime
from smrt.bot.pipeline import PipelineInterface, PipelineHelper
from smrt.bot.messenger import MessengerInterface
from smrt.libgaudeam import Gaudeam


class GaudeamBdayPipeline(PipelineInterface):
    """Pipe to handle ha commands in text. """
    BDAY_COMMAND = "gaubday"

    def __init__(self, gaudeam_session: str, chat_id_whitelist: typing.List[str]):
        self._chat_id_whitelist = chat_id_whitelist
        self._commands = [self.BDAY_COMMAND]
        self._gaudeam = Gaudeam(gaudeam_session)

    def matches(self, messenger: MessengerInterface, message: dict):
        if messenger.get_chat_id(message) not in self._chat_id_whitelist:
            return False
        message_text = messenger.get_message_text(message)
        if message_text is None:
            return False

        # we check if the message is a ha command
        command = PipelineHelper.extract_command(messenger.get_message_text(message))
        return command in self._commands

    def get_bdays_today(self) -> list[dict]:
        # todays date in format dd.mm
        today_date = datetime.datetime.now().strftime("%d.%m")
        logging.debug(f"Today's date: {today_date}")
        
        bday_members = []

        for member in self._gaudeam.members():
            birth_date = member["birthdate"]
            if birth_date and birth_date.startswith(today_date):
                bday_members.append(member)
        return bday_members
                
                
    def process(self, messenger: MessengerInterface, message: dict):
        (command, _, text) = PipelineHelper.extract_command_full(messenger.get_message_text(message))
        if command == self.BDAY_COMMAND:
            messenger.mark_in_progress_0(message)
            try:
                bdays = self.get_bdays_today()
                if len(bdays) == 0:
                    messenger.send_message(messenger.get_chat_id(message), "No birthdays today.")
                    messenger.mark_in_progress_done(message)
                    return
                
                text = "Birthdays today:"
                for member in bdays:
                    first_name = member["first_name"]
                    last_name = member["last_name"]
                    age = member["age"]
                    
                    text = text + f"\n - {first_name} {last_name} ({age})"
                messenger.send_message(messenger.get_chat_id(message), text)
                messenger.mark_in_progress_done(message)
            except Exception as ex:
                logging.critical(ex, exc_info=True)  # log exception info at CRITICAL log level
                messenger.mark_in_progress_fail(message)
                return
    def get_help_text(self) -> str:
        return \
"""*Gaudeam Birthdays*
_#gaubday_ Sends birthdays of today. """

class GaudeamCalendarPipeline(PipelineInterface):
    """Pipe to handle ha commands in text. """
    DATE_COMMAND = "gaudate"

    def __init__(self, gaudeam_session: str, chat_id_whitelist: typing.List[str]):
        self._chat_id_whitelist = chat_id_whitelist
        self._commands = [self.DATE_COMMAND]
        self._gaudeam = Gaudeam(gaudeam_session)

    def matches(self, messenger: MessengerInterface, message: dict):
        if messenger.get_chat_id(message) not in self._chat_id_whitelist:
            return False
        message_text = messenger.get_message_text(message)
        if message_text is None:
            return False

        # we check if the message is a ha command
        command = PipelineHelper.extract_command(messenger.get_message_text(message))
        return command in self._commands

    def get_events(self, days: int) -> list[dict]:
        # todays date in format dd.mm
        today_date = datetime.datetime.now()
        end_date = today_date + datetime.timedelta(days=days)
        logging.debug(f"Fetching events from {today_date} to {end_date}")
        events = self._gaudeam.calendar(today_date.date(), end_date.date())
        return events
                
                
    def process(self, messenger: MessengerInterface, message: dict):
        (command, _, text) = PipelineHelper.extract_command_full(messenger.get_message_text(message))
        if command == self.DATE_COMMAND:
            messenger.mark_in_progress_0(message)
            try:
                days = 14
                events = self.get_events(days)
                if len(events) == 0:
                    messenger.send_message(messenger.get_chat_id(message), f"No upcoming events in the next {days} days.")
                    messenger.mark_in_progress_done(message)
                    return
                
                text = "Upcoming events in the next few days:"
                # sort events by start date
                events = sorted(events, key=lambda x: datetime.datetime.strptime(x["start"], "%a, %d %b %Y %H:%M:%S %z"))
                for event in events:
                    title = event["title"]
                    start = event["start"] # format: "Thu, 02 Oct 2025 18:00:00 +0000"
                    url = event["url"]
                    
                    # take start date and convert to dd.mm.yyyy in Europe/Berlin timezone
                    start_date = datetime.datetime.strptime(start, "%a, %d %b %Y %H:%M:%S %z")
                    start_date = start_date.astimezone(datetime.timezone(datetime.timedelta(hours=2))) # Europe/Berlin timezone
                    start_str = start_date.strftime("%d.%m.%Y")
                    
                    text = text + f"\n - {start_str}: {title} ({url})"
                messenger.send_message(messenger.get_chat_id(message), text)
                messenger.mark_in_progress_done(message)
            except Exception as ex:
                logging.critical(ex, exc_info=True)  # log exception info at CRITICAL log level
                messenger.mark_in_progress_fail(message)
                return
    def get_help_text(self) -> str:
        return \
"""*Gaudeam Event Dates*
_#gaudate_ Sends a list of events coming up. """