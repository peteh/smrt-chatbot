"""Implementations of a pipeline for processing data from Gaudeam. """
import datetime
import json
import logging
import typing

from igitur import GaudeamCalendar, GaudeamEvent, GaudeamMember, GaudeamMembers

from smrt.bot.messenger import MessengerInterface, MessengerManager
from smrt.bot.messenger.whatsapp import WhatsappMessenger
from smrt.bot.pipeline import AbstractPipeline, PipelineHelper, scheduled


class GaudeamBdayPipeline(AbstractPipeline):
    """Pipe to handle ha commands in text. """
    BDAY_COMMAND = "gaubday"

    def __init__(self, gaudeam: GaudeamMembers, chat_id_whitelist: list[str]|None = None, chat_id_blacklist: list[str]|None = None):
        # can only be whitelisted chat ids
        super().__init__(chat_id_whitelist, chat_id_blacklist)
        self._commands = [self.BDAY_COMMAND]
        self._gaudeam = gaudeam

    def matches(self, messenger: MessengerInterface, message: dict):
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
f"""*Gaudeam Birthdays*
_#{self.BDAY_COMMAND}_ Sends birthdays of today. """

class GaudeamMemberCache: 
    """Cache for Gaudeam members. """
    def __init__(self, gaudeam: GaudeamMembers):
        self._gaudeam = gaudeam
        self._members = gaudeam.get_members()
        self._member_map = self._build_hashmap(self._members)
        
    
    def _build_hashmap(self, members: list[GaudeamMember]) -> dict[str, GaudeamMember]:
        # build the map but fail if the entry already exists, because that would mean we have duplicate phone numbers
        member_map = {}
        for member in members:
            phone_number = member.get_phone()
            if phone_number is None or phone_number.strip() == "":
                logging.warning(f"Member {member.get_first_name()} {member.get_last_name()} has no phone number, skipping.")
                continue
            normalized_phonenumber = self._normalize_phonenumber(phone_number)
            if normalized_phonenumber in member_map:
                logging.error(f"Duplicate phone number found: {normalized_phonenumber} for members {member_map[normalized_phonenumber].get_first_name()} {member_map[normalized_phonenumber].get_last_name()} and {member.get_first_name()} {member.get_last_name()}.")
                continue
            member_map[normalized_phonenumber] = member
        return member_map

    def _normalize_phonenumber(self, phonenumber: str) -> str:
        """Normalizes a phone number to the +49 format without dashes or whitespace.

        Args:
            phonenumber (str): The phone number to normalize.

        Returns:
            str: The normalized phone number.
        """
        # strip whitespaces and dashes
        phonenumber = phonenumber.replace(" ", "").replace("-", "")
        # normalize phonenumber to +49 format
        if phonenumber.startswith("+"):
            return phonenumber
        elif phonenumber.startswith("0"):
            return "+49" + phonenumber[1:]
        else:
            return "+49" + phonenumber

    def get_member_by_phonenumber(self, phone_number: str) -> GaudeamMember|None:
        """Gets a member by phone number. 

        Args:
            phone_number (str): _description_

        Returns:
            GaudeamMember|None: _description_
        """
        normalized_phonenumber = self._normalize_phonenumber(phone_number)
        return self._member_map.get(normalized_phonenumber)


class GaudeamMemberPipeline(AbstractPipeline):
    """Pipe to handle ha commands in text. """
    MEMBERS_COMMAND = "gaumembers"

    def __init__(self, gaudeam: GaudeamMembers, chat_id_whitelist: list[str]|None = None, chat_id_blacklist: list[str]|None = None):
        # can only be whitelisted chat ids
        super().__init__(chat_id_whitelist, chat_id_blacklist)
        self._commands = [self.MEMBERS_COMMAND]
        self._gaudeam = gaudeam

    def matches(self, messenger: MessengerInterface, message: dict):
        message_text = messenger.get_message_text(message)
        if message_text is None:
            return False

        # we check if the message is a command for this pipeline
        command = PipelineHelper.extract_command(messenger.get_message_text(message))
        if command not in self._commands:
            return False
        
        # check if we are in whatsapp messenger
        if not isinstance(messenger, WhatsappMessenger):
            logging.warning(f"GaudeamMemberPipeline only supports WhatsappMessenger, but got {type(messenger)}")
            return False
        
        # we check if we are in a group chat
        if not messenger.is_group_message(message):
            return False

        # we can accept the message
        return True

    def process(self, messenger: MessengerInterface, message: dict):
        (command, _, text) = PipelineHelper.extract_command_full(messenger.get_message_text(message))
        if command == self.MEMBERS_COMMAND:
            messenger.mark_in_progress_0(message)
            try:
                cache = GaudeamMemberCache(self._gaudeam)
                
                #members = self._gaudeam.get_members()
                # cast to WhatsappMessenger to access the get_group_members method
                wa_messenger = typing.cast(WhatsappMessenger, messenger)
                
                # does not get the phone numbers of the members, only the ids and names
                #print(wa_messenger.get_group_members(wa_messenger.get_chat_id(message)))

                # does not get the phone numbers of the members, only the ids and names
                #print(wa_messenger.get_group_info(wa_messenger.get_chat_id(message)))

                wa_group_metadata = wa_messenger.get_group_metadata(wa_messenger.get_chat_id(message))
                print(json.dumps(wa_group_metadata, indent=2))
                
                member_lids = wa_messenger.get_group_member_ids(wa_messenger.get_chat_id(message))
                message_text = "Gaudeam Members in this group:\n"
                message_lids = []
                for member in member_lids:
                    member_lid = member["_serialized"]
                    message_lids.append(member_lid)
                    wa_contact = wa_messenger.get_contact_by_pn_lid(member_lid)
                    phone_number = wa_contact["phoneNumber"]["id"]
                    normalized_phone_number = f"+{phone_number}"

                    cache_member = cache.get_member_by_phonenumber(normalized_phone_number)
                    member_tag = f"@{member_lid.replace('@c.us', '').replace('@g.us', '').replace('@lid', '')}"
                    if cache_member is None:
                        message_text += f"{wa_messenger.REACT_FAIL} {normalized_phone_number} ({member_tag}): Not found\n"
                    else:
                        member_id = cache_member.get_property("id")
                        member_resigned = cache_member.get_property("resigned")
                        vcard_link = f"{self._gaudeam._session.url()}/member/{member_id}.vcf"
                        
                        reaction = wa_messenger.REACT_CHECKMARK if not member_resigned else wa_messenger.REACT_EXCLAMATION
                        
                        message_text += f"{reaction} {normalized_phone_number} ({member_tag}): \n"
                        message_text += f"* {cache_member.get_first_name()} {cache_member.get_last_name()}\n"
                        if member_resigned:
                            message_text += f"* Not active anymore! \n"
                        message_text += f"* {vcard_link}\n"

                wa_messenger.send_message(messenger.get_chat_id(message), message_text, message_lids)
                wa_messenger.mark_in_progress_done(message)
            except Exception as ex:
                logging.critical(ex, exc_info=True)  # log exception info at CRITICAL log level
                messenger.mark_in_progress_fail(message)
                return
    def get_help_text(self) -> str:
        return \
f"""*Gaudeam Birthdays*
_#{self.MEMBERS_COMMAND}_ Sends birthdays of today. """

class GaudeamCalendarPipeline(AbstractPipeline):
    """Pipe to handle ha commands in text. """
    EVENTS_COMMAND = "gauevents"

    def __init__(self, gaudeam: GaudeamCalendar, chat_id_whitelist: list[str]|None = None, chat_id_blacklist: list[str]|None = None):
        super().__init__(chat_id_whitelist, chat_id_blacklist)
        self._commands = [self.EVENTS_COMMAND]
        self._gaudeam = gaudeam

    def matches(self, messenger: MessengerInterface, message: dict):
        message_text = messenger.get_message_text(message)
        if message_text is None:
            return False

        # we check if the message is a ha command
        command = PipelineHelper.extract_command(messenger.get_message_text(message))
        return command in self._commands

    def process(self, messenger: MessengerInterface, message: dict):
        (command, _, text) = PipelineHelper.extract_command_full(messenger.get_message_text(message))
        if command == self.EVENTS_COMMAND:
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
f"""*Gaudeam Event Dates*
_#{self.EVENTS_COMMAND}_ Sends a list of events coming up. """

class GaudeamUtils:
    @staticmethod
    def format_bday_message(bday_members: list[GaudeamMember]) -> str:
        if len(bday_members) == 0:
            return "No birthdays today."

        text = "Birthdays today:"
        for member in bday_members:
            first_name = member.get_first_name()
            last_name = member.get_last_name()
            age = member.get_age()
            text = text + f"\n - {first_name} {last_name} ({age})"
        text += "\n\nHappy Birthday! 🎉🎂"
        return text

    @staticmethod
    def get_bdays_today(gaudeam: GaudeamMembers) -> list[GaudeamMember]:
        # todays date in format dd.mm
        today_date = datetime.datetime.now().strftime("%d.%m")
        logging.debug(f"Today's date: {today_date}")

        bday_members = []

        for member in gaudeam.get_members():
            birth_date = member.get_birthdate()
            if birth_date and birth_date.startswith(today_date):
                bday_members.append(member)
        return bday_members

    @staticmethod
    def get_events(gaudeam: GaudeamCalendar, days: int) -> list[GaudeamEvent]:
        # todays date in format dd.mm
        today_date = datetime.datetime.now()
        end_date = today_date + datetime.timedelta(days=days)
        logging.debug(f"Fetching events from {today_date} to {end_date}")
        events = gaudeam.global_calendar(today_date.date(), end_date.date())
        return events

    @staticmethod
    def format_events_message(events: list[GaudeamEvent]) -> str:
        if len(events) == 0:
            return "No upcoming events."

        text = "Upcoming events:"
        for event in events:
            title = event.get_title()
            start_date = event.get_start_datetime()
            url = event.get_event_url()

            # take start date and convert to dd.mm.yyyy in Europe/Berlin timezone
            # TODO: check timezone mess
            start_date = start_date.astimezone(datetime.timezone(datetime.timedelta(hours=2))) # Europe/Berlin timezone
            start_str = start_date.strftime("%d.%m.%Y")

            text = text + f"\n - {start_str}: {title} ({url})"
        return text

class GaudeamBdayScheduledTask(scheduled.AbstractScheduledTask):
    """Scheduled task to send birthday notifications. """

    def __init__(self, messenger_manager: MessengerManager, chat_ids: list[str], gaudeam_members: GaudeamMembers):
        super().__init__(messenger_manager, chat_ids)
        self._gaudeam_members = gaudeam_members

    def run(self):
        try:
            bdays = GaudeamUtils.get_bdays_today(self._gaudeam_members)
            if len(bdays) == 0:
                logging.info("No birthdays today.")
                return

            text = GaudeamUtils.format_bday_message(bdays)

            for chat_id in self.get_chat_ids():
                try:
                    messenger = self.get_messenger_manager().get_messenger_by_chatid(chat_id)
                    if messenger is None:
                        logging.error(f"Failed to send birthday message to {chat_id}: Messenger not found.")
                        continue
                    messenger.send_message(chat_id, text)
                except Exception as ex:
                    logging.error(f"Failed to send birthday message to {chat_id} via: {ex}", exc_info=True)
        except Exception as ex:
            logging.error(f"Failed Gaudeam Scheduled Bday messages: {ex}", exc_info=True)

class GaudeamEventsScheduledTask(scheduled.AbstractScheduledTask):
    """Scheduled task to send event notifications. """

    def __init__(self, messenger_manager: MessengerManager, chat_ids: list[str], gaudeam_calendar: GaudeamCalendar):
        super().__init__(messenger_manager, chat_ids)
        self._gaudeam_calendar = gaudeam_calendar
    def run(self):
        try:
            # get day of week as an integer
            week_day = datetime.datetime.now().weekday()

            if week_day == 0: # 0 = Monday
                # Monday, send events for the next 14 days
                days_ahead = 14
            else:
                # only send events of the current day if existing
                days_ahead = 1

            events = GaudeamUtils.get_events(self._gaudeam_calendar, days_ahead)
            if len(events) == 0:
                logging.info("No events upcoming.")
                return

            text = GaudeamUtils.format_events_message(events)

            for chat_id in self.get_chat_ids():
                try:
                    messenger = self.get_messenger_manager().get_messenger_by_chatid(chat_id)
                    if messenger is None:
                        logging.error(f"Failed to send events message to {chat_id}: Messenger not found.")
                        continue
                    messenger.send_message(chat_id, text)
                except Exception as ex:
                    logging.error(f"Failed to send events message to {chat_id}: {ex}", exc_info=True)
        except Exception as ex:
            logging.error(f"Failed Gaudeam Scheduled Event messages: {ex}", exc_info=True)
