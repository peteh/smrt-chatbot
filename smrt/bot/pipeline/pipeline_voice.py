import logging
import tempfile
from typing import List
from pathlib import Path

from smrt.bot.tools.summary import SummaryInterface
from smrt.bot.messenger import MessengerInterface
from smrt.bot.pipeline import AbstractPipeline
from smrt.libtranscript import TranscriptInterface, TranscriptUtils


class VoiceMessagePipeline(AbstractPipeline):
    """A pipe that converts audio messages to text and summarizes them."""

    def __init__(
        self,
        transcriber: TranscriptInterface,
        summarizer: SummaryInterface,
        min_words_for_summary: int,
        chat_id_whitelist: List[str] | None = None,
        chat_id_blacklist: List[str] | None = None,
        transcribe_group_chats: bool = True,
        transcribe_private_chats: bool = True,
    ) -> None:
        super().__init__(chat_id_whitelist, chat_id_blacklist)
        self._transcriber = transcriber
        self._summarizer = summarizer
        self._min_words_for_summary = min_words_for_summary
        self._store_files = False
        self._transcribe_group_chats = transcribe_group_chats
        self._transcribe_private_chats = transcribe_private_chats
        logging.info("VoiceMessagePipeline initialized")
        logging.info(f"  transcribe_group_chats: {self._transcribe_group_chats}")
        logging.info(f"  transcribe_private_chats: {self._transcribe_private_chats}")

    def matches(self, messenger: MessengerInterface, message: dict):
        if not messenger.has_audio_data(message):
            return False
        is_group = messenger.is_group_message(message)
        if is_group and not self._transcribe_group_chats:
            return False
        if not is_group and not self._transcribe_private_chats:
            return False
        return True

    def process(self, messenger: MessengerInterface, message: dict):
        try:
            logging.info("Processing in Voice Pipeline")
            messenger.mark_in_progress_0(message)

            (_, decoded) = messenger.download_media(message)
            # TODO: implement download to file instead of to memory
            with tempfile.TemporaryDirectory() as tmpdir:
                # download file as binary and let ffmpeg figure out what it is
                input_file_path = Path(tmpdir) / "input.bin"
                with open(input_file_path, "wb") as input_file:
                    input_file.write(decoded)

                # Generate pcm wav from it
                wav_file_path = Path(tmpdir) / "output.wav"
                TranscriptUtils.to_pcm(input_file_path, wav_file_path)

                with open(wav_file_path, "rb") as f:
                    wav_file_data = f.read()  # returns bytes

            transcript = self._transcriber.transcribe(wav_file_data)

            transcript_text = transcript.text
            words = transcript.num_words
            language = transcript.language

            response_message = f"Transcribed: \n{transcript_text}"
            messenger.reply_message(message, response_message)

            if words > self._min_words_for_summary and self._summarizer is not None:
                messenger.mark_in_progress_50(message)

                summary = self._summarizer.summarize(transcript_text, language)

                summary_text = summary["text"]
                messenger.reply_message(message, f"Summary: \n{summary_text}")

            messenger.mark_in_progress_done(message)
        except Exception as ex:
            logging.critical(ex, exc_info=True)
            messenger.mark_in_progress_fail(message)
            return

    def get_help_text(self) -> str:
        return """*Voice Message Transcription*
Forward voice messages to the bot to transcribe them. """
