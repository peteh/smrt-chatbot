from decouple import config

def storage_path():
    return config("STORAGE_PATH", "/storage/")

def is_debug():
    return config("DEBUG", False)