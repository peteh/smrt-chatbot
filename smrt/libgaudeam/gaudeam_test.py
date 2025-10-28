import logging
import yaml
from gaudeam import GaudeamDriveFolder, GaudeamSession
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

config_file = open("config.yml", "r", encoding="utf-8")
configuration = yaml.safe_load(config_file)
config_file.close()


#session = GaudeamSession.with_user_auth(email, password)

subdomain = configuration["gaudeam"][0]["gaudeam_subdomain"]
session_cookie = configuration["gaudeam"][0]["gaudeam_session"]
session = GaudeamSession(session_cookie, subdomain)

root_folder = "32814"

folder = GaudeamDriveFolder(session, root_folder)
folder.download("/home/pete/Downloads/gaudeam_test2/")