import logging
import yaml
import datetime
from gaudeam import GaudeamDriveFolder, GaudeamSession, GaudeamCalendar, GaudeamResizedImageUploader
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

config_file = open("config.yml", "r", encoding="utf-8")
configuration = yaml.safe_load(config_file)
config_file.close()


#session = GaudeamSession.with_user_auth(email, password)

subdomain = configuration["gaudeam"][0]["gaudeam_subdomain"]
session_cookie = configuration["gaudeam"][0]["gaudeam_session"]
session = GaudeamSession(session_cookie, subdomain)
gaudeam = GaudeamCalendar(session)

gaudeam_folder = GaudeamDriveFolder(session, 35234)
#folder_name = gaudeam_folder.get_name()
#folder_size = gaudeam_folder.get_size()
#logging.info(f"Filesize of '{folder_name}': {folder_size}")

uploader = GaudeamResizedImageUploader()
uploader.add_skip_file_name("komprimiert")
#uploader.delete_remote_orphan_files("/media/veracrypt1/Bilder/Ulmia/", gaudeam_folder, dry_run = True)
uploader.upload_folder_resized("/media/veracrypt1/Bilder/Ulmia/", gaudeam_folder)
