import requests
import time
from decouple import config

class StableHordeTextToImage:
    def __init__(self) -> None:
        self._headers = {
            "apikey": config('STABLEHORDE_APIKEY')
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
            f = open(imageName, "wb")
            f.write(binary)
            f.close()

    def process(self, prompt):
        requestId = self._requestJob(prompt)
        print("ID: %s" % (requestId))

        success = self._waitForJobToFinish(requestId)

        if not success:
            print("Failed to get images")
            return None
        return self._downloadFiles(requestId)

stableHorde = StableHordeTextToImage()
stableHorde.process("Underwear party")