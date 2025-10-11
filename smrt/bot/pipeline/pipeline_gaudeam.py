"""Implementations of a pipeline for processing data from Gaudeam. """
import logging
import typing
import datetime
from smrt.bot.pipeline import PipelineInterface, PipelineHelper
from smrt.bot.messenger import MessengerInterface, MessengerManager
from smrt.bot import scheduled
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

                
    def process(self, messenger: MessengerInterface, message: dict):
        (command, _, text) = PipelineHelper.extract_command_full(messenger.get_message_text(message))
        if command == self.BDAY_COMMAND:
            messenger.mark_in_progress_0(message)
            try:
                bdays = GaudeamUtils.get_bdays_today(self._gaudeam)
                if len(bdays) == 0:
                    messenger.send_message(messenger.get_chat_id(message), "No birthdays today.")
                    messenger.mark_in_progress_done(message)
                    return
                
                text = GaudeamUtils.format_bday_message(bdays)
                
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
                
                
    def process(self, messenger: MessengerInterface, message: dict):
        (command, _, text) = PipelineHelper.extract_command_full(messenger.get_message_text(message))
        if command == self.DATE_COMMAND:
            messenger.mark_in_progress_0(message)
            try:
                days = 14
                events = GaudeamUtils.get_events(self._gaudeam, days)
                if len(events) == 0:
                    messenger.send_message(messenger.get_chat_id(message), f"No upcoming events in the next {days} days.")
                    messenger.mark_in_progress_done(message)
                    return

                text = GaudeamUtils.format_events_message(events)
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

class GaudeamUtils:
    @staticmethod
    def format_bday_message(bday_members: list[dict]) -> str:
        if len(bday_members) == 0:
            return "No birthdays today."
        
        text = "Birthdays today:"
        for member in bday_members:
            first_name = member["first_name"]
            last_name = member["last_name"]
            age = member["age"]
            
            text = text + f"\n - {first_name} {last_name} ({age})"
        text += "\n\nHappy Birthday! 🎉🎂"
        return text
    
    @staticmethod
    def get_bdays_today(gaudeam: Gaudeam) -> list[dict]:
        # todays date in format dd.mm
        today_date = datetime.datetime.now().strftime("%d.%m")
        logging.debug(f"Today's date: {today_date}")
        
        bday_members = []

        for member in gaudeam.members():
            birth_date = member["birthdate"]
            if birth_date and birth_date.startswith(today_date):
                bday_members.append(member)
        return bday_members
    
    @staticmethod
    def get_events(gaudeam: Gaudeam, days: int) -> list[dict]:
        # todays date in format dd.mm
        today_date = datetime.datetime.now()
        end_date = today_date + datetime.timedelta(days=days)
        logging.debug(f"Fetching events from {today_date} to {end_date}")
        events = gaudeam.calendar(today_date.date(), end_date.date())
        events = sorted(events, key=lambda x: datetime.datetime.strptime(x["start"], "%a, %d %b %Y %H:%M:%S %z"))
        return events

    @staticmethod
    def format_events_message(events: list[dict]) -> str:
        if len(events) == 0:
            return "No upcoming events."
        
        text = "Upcoming events:"
        for event in events:
            title = event["title"]
            start = event["start"] # format: "Thu, 02 Oct 2025 18:00:00 +0000"
            url = event["url"]
            
            # take start date and convert to dd.mm.yyyy in Europe/Berlin timezone
            start_date = datetime.datetime.strptime(start, "%a, %d %b %Y %H:%M:%S %z")
            start_date = start_date.astimezone(datetime.timezone(datetime.timedelta(hours=2))) # Europe/Berlin timezone
            start_str = start_date.strftime("%d.%m.%Y")
            
            text = text + f"\n - {start_str}: {title} ({url})"
        return text
class GaudeamBdayScheduledTask(scheduled.AbstractScheduledTask):
    """Scheduled task to send birthday notifications. """

    def __init__(self, messenger_manager: MessengerManager, chat_ids: list[str], gaudeam_session: str):
        super().__init__(messenger_manager, chat_ids)
        self._gaudeam = Gaudeam(gaudeam_session)

    def run(self):
        try:
            bdays = GaudeamUtils.get_bdays_today(self._gaudeam)
            if len(bdays) == 0:
                logging.info("No birthdays today.")
                return
            
            text = GaudeamUtils.format_bday_message(bdays)
            
            for chat_id in self.get_chat_ids():
                try:
                    messenger = self.get_messenger_manager().get_messenger_by_chatid(chat_id)
                    messenger.send_message(chat_id, text)
                except Exception as ex:
                    logging.error(f"Failed to send birthday message to {chat_id} via: {ex}", exc_info=True)
        except Exception as ex:
            logging.error(f"Failed Gaudeam Scheduled Bday messages: {ex}", exc_info=True)

class GaudeamEventsScheduledTask(scheduled.AbstractScheduledTask):
    """Scheduled task to send event notifications. """

    def __init__(self, messenger_manager: MessengerManager, chat_ids: list[str], gaudeam_session: str):
        super().__init__(messenger_manager, chat_ids)
        self._gaudeam = Gaudeam(gaudeam_session)

    def run(self):
        try: 
            events = GaudeamUtils.get_events(self._gaudeam, 14)
            if len(events) == 0:
                logging.info("No events upcoming.")
                return
            
            text = GaudeamUtils.format_events_message(events)
            
            for chat_id in self.get_chat_ids():
                try:
                    messenger = self.get_messenger_manager().get_messenger_by_chatid(chat_id)
                    messenger.send_message(chat_id, text)
                except Exception as ex:
                    logging.error(f"Failed to send events message to {chat_id}: {ex}", exc_info=True)
        except Exception as ex:
            logging.error(f"Failed Gaudeam Scheduled Event messages: {ex}", exc_info=True)