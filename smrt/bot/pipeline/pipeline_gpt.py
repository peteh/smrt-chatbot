import logging
import json
from smrt.bot.pipeline import PipelineHelper, AbstractPipeline
from smrt.db.database import MessageDatabase
from smrt.bot.tools.question_bot import QuestionBotInterface
from smrt.bot.messenger import MessengerInterface


class MessageQuestionPipeline(AbstractPipeline):
    """Allows to summarize and ask questions in a group conversation. """
    QUESTION_COMMAND = "question"

    def __init__(self, message_db: MessageDatabase,
                 question_bot: QuestionBotInterface,
                 max_history_messages: int = 20,
                 chat_id_whitelist: list|None = None,
                 chat_id_blacklist: list|None = None):
        super().__init__(chat_id_whitelist, chat_id_blacklist)
        self._message_db = message_db
        self._question_bot = question_bot
        self._max_history_messages = max_history_messages

    def matches(self, messenger: MessengerInterface, message: dict):
        message_text = messenger.get_message_text(message)

        if message_text is not None and message_text != "":
            return True
        return False

    def _get_chat(self, chat_id, count) -> list[dict]:
        messages = []
        rows = self._message_db.get_messages(chat_id, count)
        for row in rows:
            messages.append({"sender": row['sender'], "message": row['message']})
        return messages

    def _process_question_command(self, messenger: MessengerInterface, message: dict):
        message_text = messenger.get_message_text(message)
        if message_text.startswith(f"#{self.QUESTION_COMMAND}"):
            _, _, text = PipelineHelper.extract_command_full(message_text)
            message_text = text

        messenger.mark_in_progress_0(message)
        logging.debug(f"Question: {message_text}")
        chat_id = messenger.get_chat_id(message)
        messages = self._get_chat(chat_id, self._max_history_messages)
        json_struct = {
            "messages": messages[:-1], # all but last message
            "question": messages[-1]['message'] # last message is the question
        }
        json_str = json.dumps(json_struct, indent=2)

        # TODO: make prompt based on language
        prompt = f"""
You are an 'Echo' - an analytical AI assistant specialized in understanding conversations.
I will give you a list of chat messages in the following format:

[
  {{"sender": "<Name>", "message": "<Message text>"}},
  {{"sender": "<Name>", "message": "<Message text>"}}
]

I will also give you a specific question about the conversation.
Your task:
1. Analyze the chat messages carefully.
2. Answer the question as accurately as possible.
3. If the question is rather a command, e.g. tell a joke, do so.
4. If the answer is not directly stated, use logical inference, general world knowledge, and conversational context.
5. If it truly cannot be determined, respond: "Not clearly identifiable."
6. Output only the final answer in the language of the messages, with no extra explanation.

Input: 
{json_str}
"""
        logging.debug(f"Prompt: {prompt}")
        answer = self._question_bot.answer(prompt)
        answer_text = answer['text']
        logging.debug(f"Answer: {answer_text}")
        messenger.reply_message(message, answer_text)
        messenger.mark_in_progress_done(message)

    def process(self, messenger: MessengerInterface, message: dict):
        message_text = messenger.get_message_text(message)

        # store in db
        sender_name = messenger.get_sender_name(message)
        message_text = messenger.get_message_text(message)
        chat_id = messenger.get_chat_id(message)
        self._message_db.add_message(chat_id, sender_name, message_text)

        # do we need to handle a bot command? 
        # Pass: Bot mentioned without command or #question
        # Skip: all other messages that are commands
        if message_text.startswith(f"#{self.QUESTION_COMMAND}") \
            or (messenger.is_bot_mentioned(message) and not message_text.startswith("#")):
            self._process_question_command(messenger, message)

    def get_help_text(self) -> str:
        return \
f"""*Ask the bot*
_#{self.QUESTION_COMMAND} Question?_ answers questions to the last messages in the group"""
