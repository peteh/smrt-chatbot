import requests


class Whatsapp:
    def __init__(self, server, session, apiKey: str):
        self._server = server
        self._session = session
        self._apiKey = apiKey
    
    def startSession(self):
        url = "%s/api/%s/start-session" % (self._server, self._session)
        data = {
        }
        headers = {"Authorization": "Bearer %s" % (self._apiKey)}
        response = requests.post(url, json=data, headers=headers)
        print(response.json())

    def sendMessage(self, recipient: str, text: str):
        url = "%s/api/%s/send-message" % (self._server, self._session)
        print(url)
        print(self._apiKey)
        data = {
            "phone": recipient,
            "message": text,
            "isGroup": False
        }
        headers = {"Authorization": "Bearer %s" % (self._apiKey)}

        response = requests.post(url, json=data, headers=headers)
        print(response.json())
    
    def sendGroupMessage(self, chatId: str, text: str):
        url = "%s/api/%s/send-message" % (self._server, self._session)
        print(url)
        print(self._apiKey)
        data = {
            "phone": chatId,
            "message": text,
            "isGroup": True
        }
        headers = {"Authorization": "Bearer %s" % (self._apiKey)}

        response = requests.post(url, json=data, headers=headers)
        print(response.json())

    def react(self, messageId, reactionText):
        url = "%s/api/%s/react-message" % (self._server, self._session)
        data = {
            "msgId": messageId,
            "reaction": reactionText
        }
        headers = {"Authorization": "Bearer %s" % (self._apiKey)}

        response = requests.post(url, json=data, headers=headers)

    def reactHourglassHalf(self, messageId):
        self.react(messageId, "\u231b")
        
    def reactHourglassFull(self, messageId):
        self.react(messageId, "\u23f3")

    def reactDone(self, messageId):
        self.react(messageId, "\u2714\ufe0f")