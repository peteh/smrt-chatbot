from smrt.bot.pipeline import PipelineHelper, AbstractPipeline
from smrt.db.database import MessageDatabase
from smrt.bot.tools.question_bot import QuestionBotInterface
from smrt.bot.messenger import MessengerInterface


class MessageRecordPipeline(AbstractPipeline):
    """Allows to record and retrieve messages in a conversation. """

    def __init__(self, message_db: MessageDatabase):
        super().__init__(None, None)
        self._message_db = message_db

    def matches(self, messenger: MessengerInterface, message: dict):
        messenger_text = messenger.get_message_text(message)
        return messenger_text is not None and messenger_text != ""

    def process(self, messenger: MessengerInterface, message: dict):
        sender_name = messenger.get_sender_name(message)
        message_text = messenger.get_message_text(message)
        chat_id = messenger.get_chat_id(message)
        self._message_db.add_message(chat_id, sender_name, message_text)

class GroupMessageQuestionPipeline(AbstractPipeline):
    """Allows to summarize and ask questions in a group conversation. """
    QUESTION_COMMAND = "question"

    def __init__(self, message_db: MessageDatabase,
                 question_bot: QuestionBotInterface):
        super().__init__(None, None)
        self._message_db = message_db
        self._question_bot = question_bot

    def matches(self, messenger: MessengerInterface, message: dict):
        message_text = messenger.get_message_text(message)
        command, _, text = PipelineHelper.extract_command_full(message_text)
        if command in [self.QUESTION_COMMAND]:
            return True
        return messenger.is_bot_mentioned(message)

    def _get_chat_text(self, identifier, max_message_count):
        chat_text = ""
        rows = self._message_db.get_messages(identifier, max_message_count)
        actual_message_count = 0
        for row in rows:
            chat_text += f"{row['sender']}: {row['message']}\n"
            actual_message_count += 1
        return (chat_text, actual_message_count)

    def _process_question_command(self, messenger: MessengerInterface, message: dict):
        message_text = messenger.get_message_text(message)
        messenger.mark_in_progress_0(message)
        question = message_text[len(self.QUESTION_COMMAND)+1:]
        print(f"Question: {question}")
        # TODO: make number configurable
        chat_id = messenger.get_chat_id(message)
        (chat_text, _) = self._get_chat_text(chat_id, 100)
        print(chat_text)
        prompt = \
f"Der folgende Text beinhaltet eine Konversation mehrere Individuen, \
beantworte folgende Frage zu dieser Konversation: {question}\n\nText:\n{chat_text}"
        answer = self._question_bot.answer(prompt)
        answer_text = answer['text']
        print(f"Answer: {answer_text}")
        messenger.send_message_to_group(message, answer_text)
        messenger.mark_in_progress_done(message)

    def _process_summary_command(self, messenger: MessengerInterface, message: dict):
        debug = {}
        message_text = messenger.get_message_text(message)
        chat_id = messenger.get_chat_id(message)
        messenger.mark_in_progress_0(message)
        # TODO: put to configuration
        max_message_count = 20
        command = message_text.split(" ")
        if len(command) > 1:
            max_message_count = int(command[1])

        (chat_text, actual_message_count) = self._get_chat_text(chat_id,
                                                                max_message_count)

        start = time.time()
        summary = self._summarizer.summarize(chat_text, 'de')
        end = time.time()

        debug['summmary_input'] = chat_text
        debug['summmary_maxMessages'] = max_message_count
        debug['summmary_actualMessages'] = actual_message_count
        debug['summary_time'] = end - start
        debug['summary_cost'] = summary['cost']

        summary_text = f"Summary (last {actual_message_count} messages)\n{summary['text']}"
        messenger.send_message_to_group(message, summary_text)
        messenger.mark_in_progress_done(message)
        if utils.is_debug():
            debug_text = "Debug: \n"
            for debug_key, debug_value in debug.items():
                debug_text += debug_key + ": " + str(debug_value) + "\n"
            debug_text = debug_text.strip()
            messenger.send_message_to_group(message, debug_text)

    def process(self, messenger: MessengerInterface, message: dict):
        # TODO: abstract this
        push_name = messenger.get_sender_name(message)
        message_text = messenger.get_message_text(message)
        # TODO: force messenger to make it unique or do we add meta information to make it unique here
        # e.g. numbers are not unique as identifiers in different messengers
        chat_id = messenger.get_chat_id(message)

        if message_text.startswith(self.QUESTION_COMMAND):
            self._process_question_command(messenger, message)

        elif message_text.startswith(self.SUMMARY_COMMAND):
            self._process_summary_command(messenger, message)
        else:
            # TODO: filter messages with command
            self._database.add_group_message(chat_id, push_name, message_text)

    def get_help_text(self) -> str:
        return \
"""*Group Summary*
_#summary [num]_ Summarizes the last _num_ messages
_#question Question?_ answers questions to the last messages in the group"""