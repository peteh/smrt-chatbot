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
        CONFIG_MIN_WORDS_FOR_SUMMARY=int(config("MIN_WORDS_FOR_SUMMARY"))
        database = db.Database("data")
        questionbot_mixtral = questionbot.QuestionBotDolphinMixtral()
        questionbot_solar = questionbot.QuestionBotSolar()
        questionbot_phi = questionbot.QuestionBotPhi()
        questionbot_image = questionbot.QuestionBotOllama("llava")
        questionbot_Openai = questionbot.QuestionBotOpenAIAPI(config("OPENAI_APIKEY"))
        questionbot_bing = questionbot.QuestionBotBingGPT()
        bots = [
                # TODO: add bot again
                #questionbot_ollama, 
                questionbot_bing,
                questionbot_Openai
                ]
        question_bot = questionbot.FallbackQuestionbot(bots)

        summarizer = summary.QuestionBotSummary(bots)

        transcriber = transcript.FasterWhisperTranscript(denoise=False)
        voice_pipeline = pipeline.VoiceMessagePipeline(transcriber,
                                                    summarizer,
                                                    CONFIG_MIN_WORDS_FOR_SUMMARY)
        talk_pipeline = pipeline.TalkPipeline(questionbot_phi)

        gpt_pipeline = pipeline.GptPipeline(question_bot, questionbot_Openai, questionbot_bing)

        group_message_pipeline = pipeline.GroupMessageQuestionPipeline(database, summarizer, question_bot)
        article_summary_pipeline = pipeline.ArticleSummaryPipeline(summarizer)

        processors = [texttoimage.BingImageProcessor(),
                        texttoimage.DiffusersTextToImage(), 
                        texttoimage.StableHordeTextToImage(config("STABLEHORDE_APIKEY"))]
        imagegen_api = texttoimage.FallbackTextToImageProcessor(processors)
        imagegen_pipeline = pipeline.ImageGenerationPipeline(imagegen_api)
        
        image_prompt_pipeline = pipeline.ImagePromptPipeline(questionbot_image)
        

        tts_pipeline = pipeline_tts.TextToSpeechPipeline()
        grammar_pipeline = pipeline.GrammarPipeline(question_bot)
        tinder_pipeline = pipeline.TinderPipelinePipelineInterface(question_bot)

        self._pipelines = [voice_pipeline,
                    group_message_pipeline,
                    article_summary_pipeline,
                    imagegen_pipeline,
                    tts_pipeline,
                    grammar_pipeline,
                    tinder_pipeline,
                    gpt_pipeline,
                    image_prompt_pipeline,
                    talk_pipeline]

        help_pipeline = pipeline.Helpipeline(self._pipelines)
        self._pipelines.append(help_pipeline)

    def process_pipe(self, pipe: pipeline.PipelineInterface, messenger_instance: messenger.MessengerInterface, message: dict):
        pipe.process(messenger_instance, message)
        
    def process(self, messenger_instance: messenger.MessengerInterface, message: dict):
        # filter own messages from the bot
        if messenger_instance.is_self_message(message):
            logging.debug(f"Skipped self message: {message}")
            return
        
        for pipe in self._pipelines:
            if pipe.matches(messenger_instance, message):
                print(f"{type(pipe).__name__} matches, processing")
                thread = threading.Thread(target=self.process_pipe, args=(pipe, messenger_instance, message))
                thread.start()
            # delete message from phone after processing
            #whatsapp.deleteMessage(message)
