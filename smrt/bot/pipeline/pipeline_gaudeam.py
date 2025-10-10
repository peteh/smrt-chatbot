"""Implementations of a pipeline for processing data from Gaudeam. """
import logging
import typing
import datetime
from smrt.bot.pipeline import PipelineInterface, PipelineHelper
from smrt.bot.messenger import MessengerInterface
from smrt.libgaudeam import Gaudeam


class GaudeamPipeline(PipelineInterface):
    """Pipe to handle ha commands in text. """
    BDAY_COMMAND = "gaubday"

    def __init__(self, chat_id_whitelist: typing.List[str], gaudeam_session: str):
        self._chat_id_whitelist = chat_id_whitelist
        self._commands = [self.BDAY_COMMAND]
        #self._gaudeam = Gaudeam(gaudeam_session)
        self._gaudeam = Gaudeam("ILQ267KMHL8zp24alFYruFgrjLOKxXvcK9QxcMXPiMOnWuY312KIe%2FvKHWP8VpeXf9hI4sNMFU7LwLHwI%2BnnWHrtQLxbIXYhGnuTjQ9iT272KFmbKic8UmvPUo2eZBfspRrH6v2uIfoe005gqvSYyRCBi5CpciIw%2FEuL7ddk8oSj9m9hIA6F08V3gKxaplOG44ZtP4obIlA6y3X%2Fb7WPIVuSfJriCmn%2BJNh0LV3sLcQs3FkZTmsNoI9txkowq0hMARXGLYcUZXTLmFO%2FXJriuLZ99%2FjBgofoVT%2FQUx9qdz6iyRpd0bbkaqdeHPEdY9bWu8ijfojtmnE2B2EB3r5xGzTJ1HtaQFehEjQJf%2B5Wxk0yiaxX8c%2Bw%2BXsBFmbxihQaXArzHXH4RFweOoV%2BBVgbi4AKR0Z27HZMXx0hDbB1zzATBjSw7uQnrOEAh%2BRC9MabASFEpa3q6v47xHrpkxfsND0iPZisKP5nQ%2FPG7ReA1sS%2FlIj7IJwcz4iddx0i6d31LskjqpuI%2B0cgOe0cmJOkZZecGfXpc9zyZh1yLd%2FTg%2Fpwr2OZAMwkeg%3D%3D--NxmPa3MBR7gpA33O--NvT3FxNP7qWAmkvmDEOcig%3D%3D")

    def matches(self, messenger: MessengerInterface, message: dict):
        if messenger.get_chat_id(message) not in self._chat_id_whitelist():
            return False
        message_text = messenger.get_message_text(message)
        if message_text is None:
            return False

        # we check if the mesage is a ha command
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
