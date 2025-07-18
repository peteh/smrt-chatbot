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
        return None

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

# from diffusers import StableDiffusionPipeline, DiffusionPipeline
# import torch
# import io
# class DiffusersTextToImage(ImagePromptInterface):
#     """Image prompt generation using stablehorde.net API"""
#     def __init__(self) -> None:
#         self._negativePrompt = DEFAULT_NEGATIVE_PROMPT

#     def process(self, prompt):
#         #model_id = "SG161222/Realistic_Vision_V6.0_B1_noVAE"
#         #pipe = StableDiffusionPipeline.from_pretrained(model_id, torch_dtype=torch.float16, safety_checker=None, use_safetensors=True)
#         pipe = StableDiffusionPipeline.from_pretrained("runwayml/stable-diffusion-v1-5", safety_checker=None) 
#         #pipe = DiffusionPipeline.from_pretrained("stabilityai/stable-diffusion-xl-base-1.0", use_safetensors=True, safety_checker=None)

#         img_num = 1
#         img_list = []
#         for image in pipe(f"{prompt} ### {self._negativePrompt}").images:
#             # Create a BytesIO object to store the PNG data
#             png_bytes_io = io.BytesIO()

#             # Save the Pillow image to the BytesIO object as PNG
#             image.save(png_bytes_io, format="PNG")
#             image.close()

#             # Get the PNG bytes from the BytesIO object
#             png_bytes = png_bytes_io.getvalue()
#             img_list.append((f"image{img_num}.png", png_bytes))
#             img_num += 1
#         return img_list

# import re_edge_gpt
# class BingImageProcessor(ImagePromptInterface):
#     """Prompt based image generator based on Microsoft Bing's creator"""
#     def __init__(self, cookie_path = "cookie.json") -> None:
#         self._cookie_path = cookie_path

#     def process(self, prompt):
#         try:
#             with open(self._cookie_path, "r", encoding="utf-8") as f:
#                 cookies = json.load(f)
#                 for cookie in cookies:
#                     if cookie['name'] == "_U":
#                         cookie_u = cookie['value']
#             image_gen = re_edge_gpt.ImageGen(auth_cookie=cookie_u)
#             image_urls = image_gen.get_images(prompt)
#             img_num = 0
#             images = []
#             for image_url in image_urls:
#                 logging.debug(f"Image url: {image_url}")
#                 print(f"Image url: {image_url}")
#                 img_num += 1
#                 response = requests.get(image_url, timeout=1200)
#                 # filter out these weird svg graphics
#                 if len(response.content) > 3400:
#                     images.append((f"image{img_num}.jpg" , response.content))
#             if images is None or len(images) == 0:
#                 logging.error("Did not receive images from Bing")
#                 return images
#             return images
#         except Exception as ex:
#             logging.critical(ex, exc_info=True)
#         print("Failed to get an image")
#         return None

class FlowGPTImageProcessor(ImagePromptInterface):
    MODEL_DALLE3 = "DALLE3"
    def __init__(self, model = MODEL_DALLE3) -> None:
        self._model = model
    
    def process(self, prompt) -> List[Tuple[str, str]]:
        url = "https://backend-k8s.flowgpt.com/image-generation-anonymous"

        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8,fr;q=0.7",
            "Content-Length": "84",
            "Content-Type": "application/json",
            "Origin": "https://flowgpt.com",
            "Referer": "https://flowgpt.com/",
            "Sec-Ch-Ua": '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        }

        payload = {
            "model": self._model,
            "prompt": prompt, # add your custom prompt
        }

        response = requests.post(url, headers=headers, json=payload)

        try:
            print(response.status_code)
            response_data = response.json()
            url_value = response_data.get("url", "No URL found in the response")
            # TODO write this better
            image_urls = [url_value]
            img_num = 0
            images = []
            for image_url in image_urls:
                logging.debug(f"Image url: {image_url}")
                print(f"Image url: {image_url}")
                img_num += 1
                response = requests.get(image_url, timeout=1200)
                # filter out these weird svg graphics
                if len(response.content) > 3400:
                    images.append((f"image{img_num}.png" , response.content))
            if images is None or len(images) == 0:
                logging.error("Did not receive images from FlowGPT")
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
