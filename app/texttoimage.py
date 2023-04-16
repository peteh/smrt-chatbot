import requests
import time
import json
from abc import ABC, abstractmethod

class ImagePromptInterface(ABC):

    @abstractmethod
    def process(self, prompt):
        pass

class ReplicateAPI(ABC):
    def __init__(self, model, modelVersion) -> None:
        self._model = model
        self._modelVersion = modelVersion
    
    def _getModelUrl(self):
        return 'https://replicate.com/%s' \
        % (self._model)
    
    def _generatePredictUrl(self):
        # POST https://replicate.com/api/models/stability-ai/stable-diffusion/versions/db21e45d3f7023abc2a46ee38a23973f6dce16bb082a930b0c49861f96d1e5bf/predictions
        return 'https://replicate.com/api/models/%s/versions/%s/predictions' \
        % (self._model, self._modelVersion)
    
    def _generatePredictUrlForUuid(self, uuid):
        return 'https://replicate.com/api/models/%s/versions/%s/predictions/%s' \
        % (self._model, self._modelVersion, uuid)
    
    @abstractmethod
    def _generatePrompt(self, prompt: str) -> dict:
        pass
    
    def process(self, prompt):
        s = requests.Session()
        
        s.headers.update({'Referer': self._getModelUrl()})

        # TODO: extract to constructor or something
        s.headers.update({'X-CSRFToken': "9D5vvVyFmxiydLtV7qSM6DDYTwIDl7u0"})
        s.cookies.set("csrftoken", "9D5vvVyFmxiydLtV7qSM6DDYTwIDl7u0", domain="replicate.com")
        s.cookies.set("replicate_anonymous_id", "d140b681-5aee-4741-8ea0-fea46aae20ea", domain="replicate.com")
        s.cookies.set("sessionid", "50bub2y2fbf9c6yx0pj1wl2kk9wz6dot", domain="replicate.com")
        
        r = s.get(self._getModelUrl())

        data = self._generatePrompt(prompt)
        s.headers.update({'Referer': self._generatePredictUrl()})
        r = s.post(self._generatePredictUrl(), json = data)
        jsonResponse = r.json()
        
        if 'uuid' not in jsonResponse:
            s.close()
            print("No uuid in server response")
            print(json.dumps(jsonResponse, indent = 4))
            return None
        
        uuid = jsonResponse['uuid']
        predictUrlForUuid = self._generatePredictUrlForUuid(uuid)

        for i in range(0, 10):
            r = s.get(predictUrlForUuid)
            jsonResponse = r.json()
            status = jsonResponse['prediction']['status']
            print(status)
            if status == 'succeeded':
                #open text file
                #text_file = open("response.json", "w")
                #text_file.write(json.dumps(jsonResponse, indent = 4))
                #text_file.close()
                r = requests.get(jsonResponse['prediction']['output_files'][0], allow_redirects=True)
                #imageFile = open("image.png", "wb")
                #imageFile.write(r.content)
                #imageFile.close()
                return ("image.png", r.content)
                break

            #print(json.dumps(r.json(), indent = 4))
            time.sleep(2)
        return (None, None)

class StableDiffusionAPI(ReplicateAPI):

    def __init__(self):
        super().__init__('stability-ai/stable-diffusion', 'db21e45d3f7023abc2a46ee38a23973f6dce16bb082a930b0c49861f96d1e5bf')

    def _generatePrompt(self, prompt: str) -> dict:
        return {
                "inputs": {
                    "guidance_scale": 7.5,
                    "image_dimensions": "512x512",
                    "num_inference_steps": 100,
                    "num_outputs": 1,
                    "prompt": prompt,
                    "scheduler": "K_EULER"
                }
            }

class Kandinsky2API(ReplicateAPI):

    def __init__(self):
        super().__init__('ai-forever/kandinsky-2', '65a15f6e3c538ee4adf5142411455308926714f7d3f5c940d9f7bc519e0e5c1a')

    def _generatePrompt(self, prompt: str) -> dict:
        return {
                "inputs": {
                    "guidance_scale": 4,
                    "num_inference_steps": 100,
                    "prior_cf_scale": 4,
                    "prior_steps": "5",
                    "prompt": prompt,
                    "scheduler": "p_sampler"
                }
            }

import websocket
import json
import time
import base64
class StableDiffusionAIOrg(ImagePromptInterface):
    def __init__(self) -> None:
        self._negativePrompt = "ugly, tiling, poorly drawn hands, poorly drawn feet, poorly drawn face, out of frame, extra limbs, disfigured, deformed, body out of frame, blurry, bad anatomy, blurred, watermark, grainy, signature, cut off, draft"

    def process(self, prompt):
        apiUrl = "wss://api.stablediffusionai.org/v1/txt2img"
        ws = websocket.WebSocket()
        ws.settimeout(300)
        ws.connect(apiUrl)

        jsonPrompt = {"prompt":prompt,
                      "negative_prompt": self._negativePrompt,
                      "width":512,
                      "height":512}
        ws.send(json.dumps(jsonPrompt))

        response = json.loads(ws.recv())
        while response['success'] == 'ttl_remaining':
            ws.close()
            timeToWait = response['time']
            print("Wait time - waiting for %d seconds to retry" % (timeToWait))
            time.sleep(timeToWait)
            ws = websocket.WebSocket()
            ws.connect(apiUrl)
            ws.send(json.dumps(jsonPrompt))
            response = json.loads(ws.recv())

        if response['success'] != 'process':
            print("Unexpected error")
            print(response)
            ws.close()
            return None
        print("In progress")
        startTime = time.time()
        
        response = json.loads(ws.recv())
        if response['success'] != True:
            print("Unexpected error")
            print(response)
            ws.close()
            return None
        ws.close()
        endTime = time.time()
        processTime = endTime - startTime
        print("Processing took %.2fs" % (processTime))

        print("Successfully downloaded images")
        #f = open("response.json", "w")
        #f.write(json.dumps(response, indent = 4))
        #f.close()
        numImages = len(response['images'])
        images = []
        for i in range(numImages):
            imageName = "image%d.png" % (i+1)
            imageData = response['images'][i]
            base64encoded = imageData.split(',')[1].strip()
            binary = base64.b64decode(base64encoded)
            images.append((imageName, binary))
            #f = open(imageName, "wb")
            #f.write(binary)
            #f.close()
        return images
    

class StableHordeTextToImage(ImagePromptInterface):
    def __init__(self, apiKey) -> None:
        self._headers = {
            "apikey": apiKey
        }

    def _requestJob(self, prompt) -> str: 
        url = 'https://stablehorde.net/api/v2/generate/async'

        jsonRequest = {
            "censor_nsfw": False,
            "failed": False,
            "gathered": False,
            "index": 0,
            "jobId": "",
            "models": [
                "Anything Diffusion"
            ],
            "nsfw": True,
            "params": {
                "cfg_scale": 7,
                "clip_skip": 1,
                "denoising_strength": 0.75,
                "height": 512,
                "hires_fix": False,
                "karras": True,
                "n": 1,
                "post_processing": [],
                "sampler_name": "k_euler",
                "seed": "",
                "seed_variation": 1000,
                "steps": 30,
                "tiling": False,
                "width": 512
            },
            "prompt": prompt,
            "r2": True,
            "shared": False,
            "trusted_workers": False
        }

        r = requests.post(url, headers=self._headers, json=jsonRequest)
        responseJson = r.json()
        requestId = responseJson['id']
        return requestId
    
    def _waitForJobToFinish(self, requestId):
        # TODO: maybe timeout

        checkUrl = 'https://stablehorde.net/api/v2/generate/check/%s' % (requestId)
        while True:
            r = requests.get(checkUrl, headers=self._headers)
            responseJson = r.json()
            print(r.json())

            waitTime = responseJson['wait_time']
            if waitTime > 0:
                print("Sleeping for %d seconds to wait for processing" % (waitTime))
                time.sleep(waitTime)
            time.sleep(2)
            if(responseJson['done'] == True):
                if(responseJson['finished'] == 1):
                    return True
                return False
        return False
    
    def _downloadFiles(self, requestId):
        downloadUrl = 'https://stablehorde.net/api/v2/generate/status/%s' % (requestId)
        r = requests.get(downloadUrl, headers=self._headers)
        responseJson = r.json()
        images = []
        
        count = 0
        for imageStatus in responseJson['generations']:
            count += 1
            imageUrl = imageStatus['img']
            imageName = "image%d.webp" % (count)
            binary = requests.get(imageUrl).content
            images.append((imageName, binary))
            #f = open(imageName, "wb")
            #f.write(binary)
            #f.close()
        return images

    def process(self, prompt):
        requestId = self._requestJob(prompt)
        print("ID: %s" % (requestId))

        success = self._waitForJobToFinish(requestId)

        if not success:
            print("Failed to get images")
            return None
        return self._downloadFiles(requestId)
