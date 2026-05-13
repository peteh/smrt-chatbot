import logging
import yaml
import datetime
from igitur import GaudeamDriveFolder, GaudeamSession, GaudeamCalendar, GaudeamResizedImageUploader
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

config_file = open("config.yml", "r", encoding="utf-8")
configuration = yaml.safe_load(config_file)
config_file.close()

email = configuration["gaudeam"][0]["user_email"]
password = configuration["gaudeam"][0]["user_password"]
session = GaudeamSession.with_user_auth(email, password)
gaudeam = GaudeamCalendar(session)

gaudeam_folder = GaudeamDriveFolder(session, "35234")
#folder_name = gaudeam_folder.get_name()
#folder_size = gaudeam_folder.get_size()
#logging.info(f"Filesize of '{folder_name}': {folder_size}")

uploader = GaudeamResizedImageUploader()
uploader.add_skip_file_name("komprimiert")
#uploader.delete_remote_orphan_files("/media/veracrypt1/Bilder/Ulmia/", gaudeam_folder, dry_run = True)
#uploader.delete_duplicates(gaudeam_folder, dry_run = False)
#uploader.delete_empty_sub_folders(gaudeam_folder, dry_run = False)
uploader.upload_folder_resized("/media/veracrypt1/Bilder/Ulmia/", gaudeam_folder)
