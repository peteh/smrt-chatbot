from decouple import config

def storage_path():
    return config("STORAGE_PATH", "/storage/")