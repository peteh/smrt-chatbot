import logging
import threading
from smrt.bot.messenger import MessengerInterface
from .pipeline import PipelineInterface, HelpPipeline

class MainPipeline():
    def __init__(self):
        self._help_pipeline = HelpPipeline()
        #self._talk_pipeline = pipeline.TalkPipeline(questionbot_mistral_nemo)
        self._self_pipelines = []
        self._pipelines = [#self._talk_pipeline,
                    self._help_pipeline]
        #self._talk_pipeline.set_pipelines(self._pipelines)
        self._help_pipeline.set_pipelines(self._pipelines)

    def add_pipeline(self, pipe: PipelineInterface):
        self._pipelines.append(pipe)
        #self._talk_pipeline.set_pipelines(self._pipelines)
        self._help_pipeline.set_pipelines(self._pipelines)

    def add_self_pipeline(self, pipe: PipelineInterface):
        self._self_pipelines.append(pipe)

    def process_pipe(self, pipe: PipelineInterface, messenger_instance: MessengerInterface, message: dict):
        pipe.process(messenger_instance, message)

    def process(self, messenger_instance: MessengerInterface, message: dict):
        if messenger_instance.is_self_message(message):
            for pipe in self._self_pipelines:
                if pipe.allowed_in_chat_id(messenger_instance, message) and pipe.matches(messenger_instance, message):
                    logging.debug(f"Self Pipe {type(pipe).__name__} matches, processing")
                    thread = threading.Thread(target=self.process_pipe, args=(pipe, messenger_instance, message))
                    thread.start()
            return
        
        for pipe in self._pipelines:
            if pipe.allowed_in_chat_id(messenger_instance, message) and pipe.matches(messenger_instance, message):
                logging.debug(f"Pipe {type(pipe).__name__} matches, processing")
                thread = threading.Thread(target=self.process_pipe, args=(pipe, messenger_instance, message))
                thread.start()
            # delete message from phone after processing
            #whatsapp.deleteMessage(message)

