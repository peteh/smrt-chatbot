import websocket
import json
import time
import base64
websocket.enableTrace(True)

def process(prompt):
    apiUrl = "wss://stabilityai-stable-diffusion-1.hf.space/queue/join"
    ws = websocket.WebSocket()
    ws.connect(apiUrl)
    jsonPrompt = json.dumps({"session_hash":"18blh4fflxx","fn_index":3})
    ws.send(jsonPrompt)
    data = {
        "fn_index": 3,
        "data": [
            prompt
        ],
        "session_hash": "18blh4fflxh"
    }
    response = json.loads(ws.recv())
    print(response)
    return
    while response['success'] == 'ttl_remaining':
        ws.close()
        timeToWait = response['time']
        print("Waiting for %d seconds to retry" % (timeToWait))
        time.sleep(timeToWait)
        ws = websocket.WebSocket()
        ws.connect(apiUrl)
        ws.send(jsonPrompt)
        response = json.loads(ws.recv())

    if response['success'] != 'process':
        print("Unexpected error")
        print(response)
        ws.close()
        return None
    print("In progress")
    response = json.loads(ws.recv())
    if response['success'] != True:
        print("Unexpected error")
        print(response)
        ws.close()
        return None
    ws.close()

    print("Successfully downloaded images")
    f = open("response.json", "w")
    f.write(json.dumps(response, indent = 4))
    f.close()
    numImages = len(response['images'])
    images = []
    for i in range(numImages):
        imageName = "image%d.png" % (i+1)
        imageData = response['images'][i]
        base64encoded = imageData.split(',')[1].strip()
        binary = base64.b64decode(base64encoded)
        images.append((imageName, binary))
        f = open(imageName, "wb")
        f.write(binary)
        f.close()
    return images

process("Funny party")