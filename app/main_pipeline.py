import summary
import transcript
import messenger
from decouple import config
import db
import pipeline
import texttoimage
import questionbot

class MainPipeline():
    def __init__(self):
        CONFIG_MIN_WORDS_FOR_SUMMARY=int(config("MIN_WORDS_FOR_SUMMARY"))
        database = db.Database("data")

        questionbot_bing = questionbot.QuestionBotBingGPT()
        questionbot_revchatgpt = questionbot.QuestionBotRevChatGPT(config("CHATGPT_COOKIE"))
        bots = [
                questionbot_revchatgpt,
                questionbot_bing,
                questionbot.QuestionBotOpenAIAPI(config("OPENAI_APIKEY"))
                ]
        question_bot = questionbot.FallbackQuestionbot(bots)

        summarizer = summary.QuestionBotSummary(question_bot)

        transcriber = transcript.FasterWhisperTranscript(denoise=False)
        voice_pipeline = pipeline.VoiceMessagePipeline(transcriber,
                                                    summarizer,
                                                    CONFIG_MIN_WORDS_FOR_SUMMARY)
        gpt_pipeline = pipeline.GptPipeline(question_bot, questionbot_revchatgpt, questionbot_bing)

        group_message_pipeline = pipeline.GroupMessageQuestionPipeline(database, summarizer, question_bot)
        article_summary_pipeline = pipeline.ArticleSummaryPipeline(summarizer)

        processors = [texttoimage.BingImageProcessor(),
                    texttoimage.StableDiffusionAIOrg(),
                    texttoimage.StableHordeTextToImage(config("STABLEHORDE_APIKEY"))]
        image_api = texttoimage.FallbackTextToImageProcessor(processors)
        image_pipeline = pipeline.ImagePromptPipeline(image_api)

        tts_pipeline = pipeline.TextToSpeechPipeline()
        grammar_pipeline = pipeline.GrammarPipeline(question_bot)
        tinder_pipeline = pipeline.TinderPipelinePipelineInterface(question_bot)

        self._pipelines = [voice_pipeline,
                    group_message_pipeline,
                    article_summary_pipeline,
                    image_pipeline,
                    tts_pipeline,
                    grammar_pipeline,
                    tinder_pipeline,
                    gpt_pipeline]

        help_pipeline = pipeline.Helpipeline(self._pipelines)
        self._pipelines.append(help_pipeline)

    def process(self, messenger_instance: messenger.MessengerInterface, message: dict):
        for pipe in self._pipelines:
            if pipe.matches(messenger_instance, message):
                print(f"{type(pipe).__name__} matches, processing")
                # TODO: allow multi thread processing
                pipe.process(messenger_instance, message)
            # delete message from phone after processing
            #whatsapp.deleteMessage(message)
