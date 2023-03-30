import requests

class Whatsapp:
    def __init__(self, apiKey: str):
        self._apiKey = apiKey
    
    def sendMessage(self, recipient: str, text: str):
        url = 'http://localhost:21465/api/smrt/send-message'
        data = {
                "phone": recipient,
                "message": text,
                "isGroup": False
                }
        headers = {"Authorization": "Bearer %s" % (self._apiKey)}

        response = requests.post(url, json=data, headers=headers)
        #print(response.json())