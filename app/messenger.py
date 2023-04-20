"""Messenger implementations for various messengers like Whatsapp. """
from abc import ABC, abstractmethod
import base64
import requests

class MessengerInterface(ABC):
    """Interface for messengers to communicate with the underlying framework. """

    @abstractmethod
    def mark_in_progress_0(self, message: dict):
        """Marks a message that it is currently in processing. """

    @abstractmethod
    def mark_in_progress_50(self, message: dict):
        """Marks a message that it is currently 50% processed. """

    @abstractmethod
    def mark_in_progress_done(self, message: dict):
        """Marks a message that it's processing has been finished. """

    @abstractmethod
    def mark_in_progress_fail(self, message: dict):
        """Marks a message that the processing of said message failed. """

    @abstractmethod
    def is_group_message(self, message: dict):
        """Checks if a message is a group message"""

    @abstractmethod
    def message_to_group(self, group_message: dict, text: str):
        """Sends a message to the group of the original message. """

    @abstractmethod
    def message_to_individual(self, message: dict, text: str):
        """Sends a message to the sender the given message. """

    @abstractmethod
    def delete_message(self, message: dict):
        """Deletes a message from the server"""

    @abstractmethod
    def hasAudioData(self, message: dict):
        pass

    @abstractmethod
    def is_asking_bot(self, message: dict):
        pass

    @abstractmethod
    def get_message_text(self, message: dict) -> str:
        pass
    
    @abstractmethod
    def imageToGroup(self, group_message, fileName, binaryData, caption = ""):
        pass

    @abstractmethod
    def imageToIndividual(self, message, fileName, binaryData, caption = ""):
        pass

    @abstractmethod
    def audioToGroup(self, group_message, binaryData):
        pass

    @abstractmethod  
    def audioToIndividual(self, message, binaryData):
        pass

    @abstractmethod
    def downloadMedia(self, message):
        pass

class Whatsapp(MessengerInterface):
    """Messenger implemenation based on wpp-server whatsapp"""
    REACT_HOURGLASS_HALF = "\u231b"
    REACT_HOURGLASS_FULL = "\u23f3"
    REACT_CHECKMARK = "\u2714\ufe0f"
    REACT_FAIL = "\u274c"

    def __init__(self, server: str, session: str, api_key: str):
        self._server = server
        self._session = session
        self._api_key = api_key
        self._headers = {"Authorization": "Bearer %s" % (self._api_key)}

    def start_session(self):
        """Starts a session at wpp-connect server"""
        url = "%s/api/%s/start-session" % (self._server, self._session)
        data = {
            #'web-hook': 'http://smrt:9000/incoming'
        }
        response = requests.post(url, json=data, headers=self._headers)
        print(response.json())

    def _send_message(self, recipient: str, is_group, text: str):
        url = "%s/api/%s/send-message" % (self._server, self._session)
        print(url)
        print(self._api_key)
        data = {
            "phone": recipient,
            "message": text,
            "isGroup": is_group
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

    def mark_in_progress_0(self, message: dict):
        self._react(message['id'], self.REACT_HOURGLASS_FULL)

    def mark_in_progress_50(self, message: dict):
        self._react(message['id'], self.REACT_HOURGLASS_HALF)

    def mark_in_progress_done(self, message: dict):
        self._react(message['id'], self.REACT_CHECKMARK)

    def mark_in_progress_fail(self, message: dict):
        self._react(message['id'], self.REACT_FAIL)

    def is_group_message(self, message: dict):
        return 'isGroupMsg' in message and message['isGroupMsg'] is True

    def message_to_group(self, group_message: dict, text: str):
        self._send_message(group_message['chatId'], True, text)

    def message_to_individual(self, message: dict, text: str):
        self._send_message(message['sender']['id'], False, text)

    def delete_message(self, message: dict):
        url = "%s/api/%s/delete-message" % (self._server, self._session)
        is_group = self.is_group_message(message)
        recpipient = message['chatId'] if is_group else message['sender']['id'] 
        data = {
            "phone": recpipient,
            "messageId": message['id'],
            "isGroup": is_group
        }
        response = requests.post(url, json=data, headers=self._headers)
        print(response.json())

    def _sendImage(self, recipient: str, is_group: bool, file_name: str, binary_data, caption: str):
        url = "%s/api/%s/send-image" % (self._server, self._session)
        base64data = base64.b64encode(binary_data).decode('utf-8')
        if file_name.endswith('.webp'):
            data_type="image/webp"
        else:
            data_type="image/png"

        data = {
            "phone": recipient,
            "base64": "data:%s;base64,%s" % (data_type, base64data),
            "filename": file_name,
            "message": caption,
            "isGroup": is_group, 
        }
        response = requests.post(url, json=data, headers=self._headers)

    def imageToGroup(self, group_message, fileName, binaryData, caption = ""):
        self._sendImage(group_message['chatId'], True, fileName, binaryData, caption)

    def imageToIndividual(self, message, fileName, binaryData, caption = ""):
        self._sendImage(message['sender']['id'], False, fileName, binaryData, caption)

    def audioToGroup(self, group_message, binaryData):
        self._sendAudio(group_message['chatId'], True, binaryData)

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
        headers = {"Authorization": "Bearer %s" % (self._api_key)}
        response = requests.post(url, json=data, headers=headers)

    def hasAudioData(self, message: dict):
        return 'mimetype' in message and message['mimetype'] == "audio/ogg; codecs=opus"

    def is_asking_bot(self, message: dict):
        # TODO: extract this somehow
        return 'mentionedJidList' in message \
            and len(message['mentionedJidList']) == 1 \
            and message['mentionedJidList'] == '4917658696957@c.us'

    def get_message_text(self, message: dict):
        return message['content']


    def downloadMedia(self, message):
        msg_id = message['id']
        url = "%s/api/%s/get-media-by-message/%s" % (self._server, self._session, msg_id)
        response = requests.get(url, headers=self._headers)

        jsonResponse = response.json()
        data = jsonResponse['base64']        
        decoded = base64.b64decode(data)
        mimeType = jsonResponse['mimetype']

        return (mimeType, decoded)