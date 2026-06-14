"""Text to image implementations. """
import time
import json
import logging
from typing import List, Tuple
from abc import ABC, abstractmethod
import requests

class ImagePromptInterface(ABC):
    """Interface to turn prompts into a list of pictures. """
    @abstractmethod
    def process(self, prompt) -> List[Tuple[str,str]] | None:
        """Processes prompts and turns them to images"""


DEFAULT_NEGATIVE_PROMPT = "blender, cropped, lowres, poorly drawn face, out of frame, poorly \
    drawn hands, blurry, bad art, blurred, text, watermark, disfigured, deformed, closed eyes"

class OpenAIImagePrompt(ImagePromptInterface):
    """Implementation to get images from OpenAI API. """

    REQUEST_TIMEOUT = 1200

    def __init__(self, host:str, api_key:str, model:str) -> None:
        super().__init__()
        self._host = host
        self._api_key = api_key
        self._model = model

    def process(self, prompt):
        try:
            model = self._model if self._model is not None else ""
            headers={
                    "Authorization": f"Bearer {self._api_key}"
                } if self._api_key is not None else None
            response = requests.post(
                f"{self._host}/v1/images/generations",
                headers=headers,
                json={
                    "model": model,
                    "prompt": prompt,
                    "n": 1,
                    "size": "512x512"
                },
                timeout=self.REQUEST_TIMEOUT
            )
            response_json = response.json()
            images = []
            for i, image in enumerate(response_json['data']):
                image_binary = image['b64_json']
                image_name = f"image{i+1}.png"
                binary = base64.b64decode(image_binary)
                images.append((image_name, binary))
            return images
        except Exception as ex:
            logging.critical(ex, exc_info=True)  # log exception info at CRITICAL log level
        return None


import base64
import websockets.sync.client as wsclient
class StableDiffusionAIOrg(ImagePromptInterface):
    """Implementation to get interfaces from stabediffusionai.org. """
    WEBSOCKET_TIMEOUT = 600
    WEBSOCKET_MAXSIZE = 1024*1024*50

    def __init__(self) -> None:
        super().__init__()
        self._negative_prompt = DEFAULT_NEGATIVE_PROMPT
        self._store_files = False

    def set_store_files(self, store: bool):
        """Enables or disables storing of generated files

        Args:
            store (bool): True to enable storing of generated files
        """
        self._store_files = store

    def _decode_images(self, response: dict) -> List[Tuple[str, str]]:
        num_images = len(response['images'])
        images = []
        for i in range(num_images):
            image_name = f"image{i+1}.png"
            image_data = response['images'][i]['image']
            base64encoded = image_data.split(',')[1].strip()
            binary = base64.b64decode(base64encoded)
            images.append((image_name, binary))
            if self._store_files:
                with open(image_name, "wb") as file:
                    file.write(binary)
        return images

    def process(self, prompt):
        try:
            api_url = "wss://api.stablediffusionai.org/v1/txt2img"
            web_sock = wsclient.connect(api_url, max_size=self.WEBSOCKET_MAXSIZE)

            json_prompt = {"prompt":prompt,
                        "negative_prompt": self._negative_prompt,
                        "width":512,
                        "height":512}
            json_prompt_str = json.dumps(json_prompt)
            web_sock.send(json_prompt_str)

            response = json.loads(web_sock.recv())
            while response['success'] == 'ttl_remaining':
                web_sock.close()
                time_to_wait = response['time']
                print(f"Wait time - waiting for {time_to_wait} seconds to retry")
                time.sleep(time_to_wait)

                web_sock = wsclient.connect(api_url, max_size=self.WEBSOCKET_MAXSIZE)
                web_sock.send(json_prompt_str)
                response = json.loads(web_sock.recv())

            if response['success'] != 'process':
                print("Unexpected error")
                print(response)
                web_sock.close()
                return None
            print("In progress")
            start_time = time.time()

            response = json.loads(web_sock.recv())
            if not response['success']:
                print("Unexpected error")
                print(response)
                web_sock.close()
                return None
            web_sock.close()
            process_time = time.time() - start_time
            print(f"Processing took {process_time:.2f}s")

            print("Successfully downloaded images")
            #f = open("response.json", "w")
            #f.write(json.dumps(response, indent = 4))
            #f.close()
            return self._decode_images(response)
        except Exception as ex:
            logging.critical(ex, exc_info=True)  # log exception info at CRITICAL log level
        return None



class StableHordeTextToImage(ImagePromptInterface):
    """Image prompt generation using stablehorde.net API"""
    def __init__(self, api_key) -> None:
        super().__init__()
        self._headers = {
            "apikey": api_key
        }
        self._negativePrompt = DEFAULT_NEGATIVE_PROMPT

    def _request_job(self, prompt) -> str: 
        url = 'https://stablehorde.net/api/v2/generate/async'
        full_prompt = prompt if len(self._negativePrompt) == 0 \
            else f"{prompt} ### {self._negativePrompt}"
        json_request = {
            "censor_nsfw": False,
            "failed": False,
            "gathered": False,
            "index": 0,
            "jobId": "",
            "models": [
                "ICBINP",
                "Deliberate"
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
            "prompt": full_prompt,
            "r2": True,
            "shared": False,
            "trusted_workers": False
        }

        response = requests.post(url,
                          headers=self._headers,
                          json=json_request,
                          timeout=1200)
        response_json = response.json()
        request_id = response_json['id']
        return request_id

    def _wait_for_job_to_finish(self, request_id):
        # TODO: maybe timeout
        check_url = f'https://stablehorde.net/api/v2/generate/check/{request_id}'
        while True:
            response = requests.get(check_url,
                             headers=self._headers,
                             timeout=20)
            response_json = response.json()
            print(response_json)

            wait_time = response_json.get('wait_time', 0)
            if wait_time > 0:
                sleep_time = 10 if wait_time > 10 else wait_time
                print(f"Sleeping for {sleep_time} seconds to wait for processing")
                time.sleep(sleep_time)
            time.sleep(2)
            if response_json['done']:
                if response_json['finished'] == 1:
                    return True
                return False

    def _download_files(self, request_id):
        download_url = f'https://stablehorde.net/api/v2/generate/status/{request_id}'
        response = requests.get(download_url,
                                headers=self._headers,
                                timeout=1200)
        response_json = response.json()
        images = []

        count = 0
        for image_status in response_json['generations']:
            count += 1
            image_url = image_status['img']
            image_name = f"image{count}.webp"
            binary = requests.get(image_url,timeout=1200).content
            images.append((image_name, binary))
            #f = open(imageName, "wb")
            #f.write(binary)
            #f.close()
        return images

    def process(self, prompt):
        request_id = self._request_job(prompt)
        print(f"ID: {request_id}")

        success = self._wait_for_job_to_finish(request_id)

        if not success:
            print("Failed to get images")
            return None
        return self._download_files(request_id)

class FallbackTextToImageProcessor(ImagePromptInterface):
    """Image processor that tries a list of image processor until one succeeds. """
    def __init__(self, processors: List[ImagePromptInterface]) -> None:
        super().__init__()
        self._processors = processors

    def process(self, prompt):
        for processor in self._processors:
            try:
                images = processor.process(prompt)
                if images is not None:
                    return images
            except Exception as ex:
                logging.critical(ex, exc_info=True)
                continue
        print("Failed to get an image")
        return None
