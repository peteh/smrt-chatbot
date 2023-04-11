import requests
from abc import ABC, abstractmethod

class MessengerInterface(ABC):

    @abstractmethod
    def markInProgress0(self, message: dict):
        pass
    
    @abstractmethod
    def markInProgress50(self, message: dict):
        pass
    
    @abstractmethod
    def markInProgressDone(self, message: dict):
        pass
    
    @abstractmethod
    def isGroupMessage(self, message: dict):
        pass
    
    @abstractmethod
    def messageToGroup(self, message: dict, text: str):
        pass

    @abstractmethod
    def messageToIndividual(self, message: dict, text: str):
        pass

    @abstractmethod
    def hasAudioData(self, message: dict):
        pass

    @abstractmethod
    def isAskingBot(self, message: dict):
        pass

class Whatsapp(MessengerInterface):
    REACT_HOURGLASS_HALF = "\u231b"
    REACT_HOURGLASS_FULL = "\u23f3"
    REACT_CHECKMARK = "\u2714\ufe0f"

    def __init__(self, server, session, apiKey: str):
        self._server = server
        self._session = session
        self._apiKey = apiKey
    
    def _startSession(self):
        url = "%s/api/%s/start-session" % (self._server, self._session)
        data = {
            #'web-hook': 'http://smrt:9000/incoming'
        }
        headers = {"Authorization": "Bearer %s" % (self._apiKey)}
        response = requests.post(url, json=data, headers=headers)
        print(response.json())

    def _sendMessage(self, recipient: str, text: str):
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
    
    def _sendGroupMessage(self, chatId: str, text: str):
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

    def _react(self, messageId, reactionText):
        url = "%s/api/%s/react-message" % (self._server, self._session)
        data = {
            "msgId": messageId,
            "reaction": reactionText
        }
        headers = {"Authorization": "Bearer %s" % (self._apiKey)}

        response = requests.post(url, json=data, headers=headers)

    def markInProgress0(self, message: dict):
        self._react(message['id'], self.REACT_HOURGLASS_FULL)
    
    def markInProgress50(self, message: dict):
        self._react(message['id'], self.REACT_HOURGLASS_HALF)
    
    def markInProgressDone(self, message: dict):
        self._react(message['id'], self.REACT_CHECKMARK)

    def isGroupMessage(self, message: dict):
        return 'isGroupMsg' in message and message['isGroupMsg'] == True
    
    def messageToGroup(self, groupMessage: dict, text: str):
        self._sendGroupMessage(groupMessage['chatId'], text)
    
    def messageToIndividual(self, message: dict, text: str):
        self._sendMessage(message['sender']['id'], text)
    
    def hasAudioData(self, message: dict):
        return 'mimetype' in message and message['mimetype'] == "audio/ogg; codecs=opus"
    
    def isAskingBot(self, message: dict):
        # TODO: extract this somehow
        return 'mentionedJidList' in message \
            and len(message['mentionedJidList']) == 1 \
            and message['mentionedJidList'] == '4917658696957@c.us'