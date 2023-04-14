# load necessary components
from trafilatura import fetch_url, extract
import summary
import questionbot
from decouple import config
# download a web page
url = 'https://www.tagesschau.de/inland/doepfner-sms-101.html'
downloaded = fetch_url(url)
downloaded is None  # assuming the download was successful
False

# extract information from HTML
result = extract(downloaded)
print(result)
# newlines preserved, TXT output ...
questionBot = questionbot.QuestionBotChatGPTOpenAI(cookie = config('CHATGPT_COOKIE'))
summarizer = summary.QuestionBotSummary(questionBot)

summarizedText = summarizer.summarize(result, 'de')['text']

print("====SUMMARY:====")
print(summarizedText)