import logging
import tempfile
import os
import time
import requests

from pipeline import PipelineInterface, PipelineHelper
from suno import SunoApi
from messenger import MessengerInterface


class SunoPipeline(PipelineInterface):
    """Pipe to generate songs """
    SONG_COMMAND = "song"

    def __init__(self):
        self._suno_api = SunoApi()
    
    

    def matches(self, messenger: MessengerInterface, message: dict):
        command = PipelineHelper.extract_command(messenger.get_message_text(message))
        return command in [self.SONG_COMMAND]
        
    def _download(self, url: str, local_file: str):
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(local_file, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): 
                    # If you have chunk encoded response uncomment if
                    # and set chunk_size parameter to None.
                    #if chunk: 
                    f.write(chunk)
        return local_file

    def process(self, messenger: MessengerInterface, message: dict):
        (command, _, prompt) = PipelineHelper.extract_command_full(messenger.get_message_text(message))
        messenger.mark_in_progress_0(message)
        try:       
            data = self._suno_api.generate_audio_by_prompt(prompt)

            ids = f"{data[0]['id']},{data[1]['id']}"
            print(f"ids: {ids}")
            finished = False

            # we wait for a minute till the songs are finished
            for _ in range(60):
                data = self._suno_api.get_audio_information(ids)
                # wait till it's set to streaming
                if data[0]["status"] == 'streaming':
                    finished = True
                    break
                    
                # sleep 5s
                time.sleep(5)
            
            if not finished:
                messenger.reply_message(message, "Songs were not finished in time")
                raise ValueError("Files were not finished when trying to download")

            with tempfile.TemporaryDirectory() as tmp:
                print(f"{data[0]['id']} ==> {data[0]['audio_url']}")
                print(f"{data[1]['id']} ==> {data[1]['audio_url']}")
                output_file_1 = os.path.join(tmp, '1.mp3')
                output_file_2 = os.path.join(tmp, '2.mp3')
                self._download(data[0]['audio_url'], output_file_1)
                self._download(data[1]['audio_url'], output_file_2)
                if messenger.is_group_message(message):
                    messenger.send_audio_to_group(message, output_file_1)
                    messenger.send_audio_to_group(message, output_file_2)
                else:
                    messenger.send_audio_to_individual(message, output_file_1)
                    messenger.send_audio_to_individual(message, output_file_2)

                messenger.mark_in_progress_done(message)
        except Exception as ex:
            logging.critical(ex, exc_info=True)  # log exception info at CRITICAL log level
            messenger.mark_in_progress_fail(message)
            return
    def get_help_text(self) -> str:
        return \
"""*Songs*
_#song promot_ Generates a song based on the prompt, use style and content as descripte as possible"""
