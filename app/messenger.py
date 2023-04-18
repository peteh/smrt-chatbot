import requests
from abc import ABC, abstractmethod
import base64

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
    def markInProgressFail(self, message: dict):
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
    def deleteMessage(self, message: dict):
        pass

    @abstractmethod
    def hasAudioData(self, message: dict):
        pass

    @abstractmethod
    def isAskingBot(self, message: dict):
        pass

    @abstractmethod
    def getMessageText(self, message: dict) -> str:
        pass
    
    @abstractmethod
    def imageToGroup(self, groupMessage, fileName, binaryData, caption = ""):
        pass

    @abstractmethod
    def imageToIndividual(self, message, fileName, binaryData, caption = ""):
        pass

    @abstractmethod
    def audioToGroup(self, groupMessage, binaryData):
        pass

    @abstractmethod  
    def audioToIndividual(self, message, binaryData):
        pass

    @abstractmethod
    def downloadMedia(self, message):
        pass

class Whatsapp(MessengerInterface):
    REACT_HOURGLASS_HALF = "\u231b"
    REACT_HOURGLASS_FULL = "\u23f3"
    REACT_CHECKMARK = "\u2714\ufe0f"
    REACT_FAIL = "\u274c"

    def __init__(self, server, session, apiKey: str):
        self._server = server
        self._session = session
        self._apiKey = apiKey
        self._headers = {"Authorization": "Bearer %s" % (self._apiKey)}
    
    def _startSession(self):
        url = "%s/api/%s/start-session" % (self._server, self._session)
        data = {
            #'web-hook': 'http://smrt:9000/incoming'
        }
        response = requests.post(url, json=data, headers=self._headers)
        print(response.json())

    def _sendMessage(self, recipient: str, isGroup, text: str):
        url = "%s/api/%s/send-message" % (self._server, self._session)
        print(url)
        print(self._apiKey)
        data = {
            "phone": recipient,
            "message": text,
            "isGroup": isGroup
        }
        response = requests.post(url, json=data, headers=self._headers)
        print(response.json())

    def _react(self, messageId, reactionText):
        url = "%s/api/%s/react-message" % (self._server, self._session)
        data = {
            "msgId": messageId,
            "reaction": reactionText
        }
        response = requests.post(url, json=data, headers=self._headers)

    def markInProgress0(self, message: dict):
        self._react(message['id'], self.REACT_HOURGLASS_FULL)
    
    def markInProgress50(self, message: dict):
        self._react(message['id'], self.REACT_HOURGLASS_HALF)
    
    def markInProgressDone(self, message: dict):
        self._react(message['id'], self.REACT_CHECKMARK)
    
    def markInProgressFail(self, message: dict):
        self._react(message['id'], self.REACT_FAIL)

    def isGroupMessage(self, message: dict):
        return 'isGroupMsg' in message and message['isGroupMsg'] == True
    
    def messageToGroup(self, groupMessage: dict, text: str):
        self._sendMessage(groupMessage['chatId'], True, text)
    
    def messageToIndividual(self, message: dict, text: str):
        self._sendMessage(message['sender']['id'], False, text)
    
    def deleteMessage(self, message: dict):
        url = "%s/api/%s/delete-message" % (self._server, self._session)
        isGroup = self.isGroupMessage(message)
        recpipient = message['chatId'] if isGroup else message['sender']['id'] 
        data = {
            "phone": recpipient,
            "messageId": message['id'],
            "isGroup": isGroup
        }
        response = requests.post(url, json=data, headers=self._headers)
        print(response.json())
    
    def _sendImage(self, recipient: str, isGroup: bool, fileName: str, binaryData, caption: str):
        url = "%s/api/%s/send-image" % (self._server, self._session)
        base64data = base64.b64encode(binaryData).decode('utf-8')
        if fileName.endswith('.webp'):
            dataType="image/webp"
        else:
            dataType="image/png"
            
        data = {
            "phone": recipient,
            "base64": "data:%s;base64,%s" % (dataType, base64data),
            "filename": fileName,
            "message": caption,
            "isGroup": isGroup, 
            
        }
        response = requests.post(url, json=data, headers=self._headers)

    def imageToGroup(self, groupMessage, fileName, binaryData, caption = ""):
        self._sendImage(groupMessage['chatId'], True, fileName, binaryData, caption)
        
    def imageToIndividual(self, message, fileName, binaryData, caption = ""):
        self._sendImage(message['sender']['id'], False, fileName, binaryData, caption)
    
    def audioToGroup(self, groupMessage, binaryData):
        self._sendAudio(groupMessage['chatId'], True, binaryData)
        
    def audioToIndividual(self, message, binaryData):
        self._sendAudio(message['sender']['id'], False, binaryData)

    def _sendAudio(self, recipient: str, isGroup: bool, binaryData):
        url = "%s/api/%s/send-voice-base64" % (self._server, self._session)
        base64data = base64.b64encode(binaryData).decode('utf-8')
        
        data = {
            "phone": recipient,
            "base64Ptt": "data:audio/ogg;base64,%s" % base64data,
            "isGroup": isGroup, 
        }
        headers = {"Authorization": "Bearer %s" % (self._apiKey)}
        response = requests.post(url, json=data, headers=headers)
    
    def hasAudioData(self, message: dict):
        return 'mimetype' in message and message['mimetype'] == "audio/ogg; codecs=opus"
    
    def isAskingBot(self, message: dict):
        # TODO: extract this somehow
        return 'mentionedJidList' in message \
            and len(message['mentionedJidList']) == 1 \
            and message['mentionedJidList'] == '4917658696957@c.us'

    def getMessageText(self, message: dict):
        return message['content']

    
    def downloadMedia(self, message):
        msgId = message['id']
        url = "%s/api/%s/get-media-by-message/%s" % (self._server, self._session, msgId)
        response = requests.get(url, headers=self._headers)

        jsonResponse = response.json()
        data = jsonResponse['base64']        
        decoded = base64.b64decode(data)
        mimeType = jsonResponse['mimetype']

        return (mimeType, decoded)