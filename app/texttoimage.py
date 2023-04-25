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
    def process(self, prompt) -> List[Tuple[str,str]]:
        """Processes prompts and turns them to images"""


DEFAULT_NEGATIVE_PROMPT = "blender, cropped, lowres, poorly drawn face, out of frame, poorly \
    drawn hands, blurry, bad art, blurred, text, watermark, disfigured, deformed, closed eyes"

class ReplicateAPI(ImagePromptInterface):
    def __init__(self, model, model_version) -> None:
        self._model = model
        self._model_version = model_version

    def _get_model_url(self):
        return 'https://replicate.com/%s' \
        % (self._model)

    def _generate_predict_url(self):
        return 'https://replicate.com/api/models/%s/versions/%s/predictions' \
        % (self._model, self._model_version)

    def _generate_predict_url_for_uuid(self, uuid):
        return 'https://replicate.com/api/models/%s/versions/%s/predictions/%s' \
        % (self._model, self._model_version, uuid)

    @abstractmethod
    def _generate_prompt(self, prompt: str) -> dict:
        pass

    def process(self, prompt):
        session = requests.Session()
        session.headers.update({'Referer': self._get_model_url()})

        # TODO: extract to constructor or something
        session.headers.update({'X-CSRFToken': "9D5vvVyFmxiydLtV7qSM6DDYTwIDl7u0"})
        session.cookies.set("csrftoken", "9D5vvVyFmxiydLtV7qSM6DDYTwIDl7u0", domain="replicate.com")
        session.cookies.set("replicate_anonymous_id", "d140b681-5aee-4741-8ea0-fea46aae20ea",
                            domain="replicate.com")
        session.cookies.set("sessionid", "50bub2y2fbf9c6yx0pj1wl2kk9wz6dot", domain="replicate.com")

        response = session.get(self._get_model_url())

        data = self._generate_prompt(prompt)
        session.headers.update({'Referer': self._generate_predict_url()})
        response = session.post(self._generate_predict_url(), json = data)
        json_response = response.json()

        if 'uuid' not in json_response:
            session.close()
            print("No uuid in server response")
            print(json.dumps(json_response, indent = 4))
            return None

        uuid = json_response['uuid']
        predict_url_for_uuid = self._generate_predict_url_for_uuid(uuid)

        for i in range(0, 10):
            response = session.get(predict_url_for_uuid)
            json_response = response.json()
            status = json_response['prediction']['status']
            print(status)
            if status == 'succeeded':
                #open text file
                #text_file = open("response.json", "w")
                #text_file.write(json.dumps(jsonResponse, indent = 4))
                #text_file.close()
                response = requests.get(json_response['prediction']['output_files'][0], allow_redirects=True)
                #imageFile = open("image.png", "wb")
                #imageFile.write(r.content)
                #imageFile.close()
                return ("image.png", response.content)

            #print(json.dumps(r.json(), indent = 4))
            time.sleep(2)
        return (None, None)

class StableDiffusionAPI(ReplicateAPI):

    def __init__(self):
        super().__init__('stability-ai/stable-diffusion',
                         'db21e45d3f7023abc2a46ee38a23973f6dce16bb082a930b0c49861f96d1e5bf')

    def _generate_prompt(self, prompt: str) -> dict:
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
        super().__init__('ai-forever/kandinsky-2',
                         '65a15f6e3c538ee4adf5142411455308926714f7d3f5c940d9f7bc519e0e5c1a')

    def _generate_prompt(self, prompt: str) -> dict:
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
            image_data = response['images'][i]
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

            wait_time = response_json['wait_time']
            if wait_time > 0:
                print(f"Sleeping for {wait_time} seconds to wait for processing")
                time.sleep(wait_time)
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

import BingImageCreator
class BingImageProcessor(ImagePromptInterface):
    """Prompt based image generator based on Microsoft Bing's creator"""
    def __init__(self, cookie_path = "cookie.json") -> None:
        try:
            with open(cookie_path, "r", encoding="utf-8") as f:
                cookies = json.load(f)
                for cookie in cookies:
                    if cookie['name'] == "_U":
                        self._cookie = cookie['value']
        except FileNotFoundError as ex:
            raise FileNotFoundError("Cookie file not found") from ex

    def process(self, prompt):
        try:
            image_gen = BingImageCreator.ImageGen(self._cookie)
            image_urls = image_gen.get_images(prompt)
            img_num = 0
            images = []
            for image_url in image_urls:
                img_num += 1
                response = requests.get(image_url, timeout=1200)
                images.append((f"image{img_num}.jpg" , response.content))
            if images is None or len(images) == 0:
                return images
            return images
        except Exception as ex:
            logging.critical(ex, exc_info=True)
        print("Failed to get an image")
        return None


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
