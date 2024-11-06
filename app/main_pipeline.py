import logging
import threading

import summary
import transcript
import messenger
from decouple import config
import db
import pipeline
import pipeline_tts
import texttoimage
import questionbot

class MainPipeline():
    def __init__(self):
        
        questionbot_mistral_nemo = questionbot.QuestionBotMistralNemo()
        
        self._help_pipeline = pipeline.Helpipeline()
        #self._talk_pipeline = pipeline.TalkPipeline(questionbot_mistral_nemo)
        self._self_pipelines = []
        self._pipelines = [#self._talk_pipeline,
                    self._help_pipeline]
        #self._talk_pipeline.set_pipelines(self._pipelines)
        self._help_pipeline.set_pipelines(self._pipelines)
        

    def add_pipeline(self, pipe: pipeline.PipelineInterface):
        self._pipelines.append(pipe)
        #self._talk_pipeline.set_pipelines(self._pipelines)
        self._help_pipeline.set_pipelines(self._pipelines)
    
    def add_self_pipeline(self, pipe: pipeline.PipelineInterface):
        self._self_pipelines.append(pipe)

    def process_pipe(self, pipe: pipeline.PipelineInterface, messenger_instance: messenger.MessengerInterface, message: dict):
        pipe.process(messenger_instance, message)
        
    def process(self, messenger_instance: messenger.MessengerInterface, message: dict):
        if messenger_instance.is_self_message(message):
            for pipe in self._self_pipelines:
                if pipe.matches(messenger_instance, message):
                    print(f"Self Pipe {type(pipe).__name__} matches, processing")
                    thread = threading.Thread(target=self.process_pipe, args=(pipe, messenger_instance, message))
                    thread.start()
            return
        
        for pipe in self._pipelines:
            if pipe.matches(messenger_instance, message):
                print(f"Remote Pipe {type(pipe).__name__} matches, processing")
                thread = threading.Thread(target=self.process_pipe, args=(pipe, messenger_instance, message))
                thread.start()
            # delete message from phone after processing
            #whatsapp.deleteMessage(message)

