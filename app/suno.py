import time
import requests

class SunoApi():
    
    def __init__(self) -> None:
        self._base_url = 'http://localhost:3000'
    


    def custom_generate_audio(self, payload):
        url = f"{self._base_url}/api/custom_generate"
        response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'})
        return response.json()


    def extend_audio(self, payload):
        url = f"{self._base_url}/api/extend_audio"
        response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'})
        return response.json()

    def generate_audio_by_prompt(self, prompt: str, make_instrumental: bool = False, wait_audio: bool = False):
        url = f"{self._base_url}/api/generate"
        payload = {
                "prompt": prompt,
                "make_instrumental": make_instrumental,
                "wait_audio": wait_audio
            }
        response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'})
        return response.json()


    def get_audio_information(self, audio_ids):
        url = f"{self._base_url}/api/get?ids={audio_ids}"
        response = requests.get(url)
        return response.json()


    def get_quota_information(self):
        url = f"{self._base_url}/api/get_limit"
        response = requests.get(url)
        return response.json()

    def get_clip(self, clip_id):
        url = f"{self._base_url}/api/clip?id={clip_id}"
        response = requests.get(url)
        return response.json()

    def generate_whole_song(self, clip_id):
        payload = {"clip_id": clip_id}
        url = f"{self._base_url}/api/concat"
        response = requests.post(url, json=payload)
        return response.json()


if __name__ == '__main__':
    api = SunoApi()
    print(api.get_quota_information())
    exit()
    
    data = api.generate_audio_by_prompt({
        "prompt": "A popular heavy metal song about war, sung by a deep-voiced male singer, slowly and melodiously. The lyrics depict the sorrow of people after the war.",
        "make_instrumental": False,
        "wait_audio": False
    })

    ids = f"{data[0]['id']},{data[1]['id']}"
    print(f"ids: {ids}")

    for _ in range(60):
        data = api.get_audio_information(ids)
        if data[0]["status"] == 'streaming':
            print(f"{data[0]['id']} ==> {data[0]['audio_url']}")
            print(f"{data[1]['id']} ==> {data[1]['audio_url']}")
            break
        # sleep 5s
        time.sleep(5)
