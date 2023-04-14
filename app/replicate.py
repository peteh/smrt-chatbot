import requests
import time
import json
from abc import ABC, abstractmethod

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
                    "num_inference_steps": 50,
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