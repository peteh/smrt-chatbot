
from smrt.bot import messenger

class ScheduledTaskInterface:

    def run(self):
        raise NotImplementedError()

class AbstractScheduledTask(ScheduledTaskInterface):

    def __init__(self, messenger_manager: messenger.MessengerManager, chat_ids: list[str]):
        self._chat_ids = chat_ids
        self._messenger_manager = messenger_manager
    
    def get_messenger_manager(self) -> messenger.MessengerManager:
        return self._messenger_manager
    
    def get_chat_ids(self) -> list[str]:
        return self._chat_ids
    
    def run(self):
        raise NotImplementedError()