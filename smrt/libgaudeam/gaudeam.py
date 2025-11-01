from __future__ import annotations
import logging
import json
import datetime
import typing
import xml.etree.ElementTree as ET
from pathlib import Path
from os import scandir
import requests
from bs4 import BeautifulSoup



class GaudeamSession():
    def __init__(self, gaudeam_session_cookie: str, subdomain: str):
        """Creates a session for Gaudeam

        Args:
            gaudeam_session_cookie (str): The cookie value from "_gaudeam_session" 
                                    exported from a logged in browser session
            subdomain (str): Subdomain of your gaudeam instance, 
                                    e.g. "yourinstance" for "yourinstance.gaudeam.de"
        """
        self._gaudeam_session = gaudeam_session_cookie
        self._subdomain = subdomain

        self._client = requests.Session()
        self._client.cookies.update({"_gaudeam_session": gaudeam_session_cookie})
    
    @staticmethod
    def with_user_auth(email: str, password: str) -> GaudeamSession:
        """Logs in using user and password and creates a session. 

        Args:
            email (str): Email of your user account
            password (str): Password of your user account

        Raises:
            ValueError: If user and/or password are wrong

        Returns:
            GaudeamSession: The session to Gaudeam
        """
        temp_session = requests.Session()
        url_login = "https://auth.gaudeam.de/login"
        response_login_page = temp_session.get(url_login)
        soup = BeautifulSoup(response_login_page.content, "html.parser")
        authenticity_token = soup.find("input", {"name": "authenticity_token"})["value"]
        
        data = {
            "authenticity_token": authenticity_token,
            "user[email]": email,
            "user[password]": password,
            "user[remember_me]": [
                "0",
                "1"
            ],
            "user[anchor_after_login]": "",
            "commit": "Einloggen"
        }

        response_auth = temp_session.post(url_login, data, allow_redirects=False)
        status = response_auth.status_code
        if (status == 302): # redirect, login successful
            redirect_url = response_auth.headers.get("Location")
            subdomain = redirect_url.removeprefix("https://").split(".gaudeam.de")[0]
            session_cookie = response_auth.cookies["_gaudeam_session"]

            return GaudeamSession(session_cookie, subdomain)
        else: 
            raise ValueError("Failed to login to gaudeam, check credentials")


    def client(self) -> requests.Session:
        """Returns the requests session for the gaudeam connection

        Returns:
            requests.Session: session for gaudeam connection
        """
        return self._client

    def url(self) -> str:
        """Returns the base url, e.g. "https://yourinstance.gaudeam.de"

        Returns:
            str: the base url of your instance
        """
        return f"https://{self._subdomain}.gaudeam.de"

class GaudeamMembers:
    def __init__(self, gaudeam_session: GaudeamSession):
        self._session = gaudeam_session

    def get_members(self, include_dead=False, include_alliances=False, include_resigned=False, seach_term=""):
        offset = 0
        limit = 100
        params = {
            "q": seach_term,
            "offset": offset,
            "limit": limit,
            "order": "name",
            "asc": "true",
            "dead": str(include_dead).lower(),
            "alliances": str(include_alliances).lower(),
            "resigned": str(include_resigned).lower()
        }

        response_count = self._session.client().get(f"{self._session.url()}/api/v1/members/count", params=params)
        num_records = response_count.json()["count"]

        response_members = self._session.client().get(f"{self._session.url()}/api/v1/members/index", params=params)
        members = response_members.json()["results"]
        while len(members) < num_records:
            offset += limit
            params["offset"] = offset
            response_members = self._session.client().get(f"{self._session.url()}/api/v1/members/index", params=params)
            members.extend(response_members.json()["results"])
        return members
class GaudeamCalendar:
    def __init__(self, gaudeam_session: GaudeamSession):
        self._session = gaudeam_session

    @staticmethod
    def date_string_to_datetime(date: str):
        if date[-1] == "Z":
            dt = datetime.datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%fZ")
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        else:
            dt = datetime.datetime.strptime(date, "%a, %d %b %Y %H:%M:%S %z")
        return dt.astimezone(datetime.timezone.utc)

    def user_calendar(self, start_date: datetime.date, end_date: datetime.date) -> list[dict]:
        start_str = start_date.strftime("%Y-%m-%dT00:00:00Z")
        end_str = end_date.strftime("%Y-%m-%dT00:00:00Z")
        url = f"{self._session.url()}/user_calendar.json?start={start_str}&end={end_str}&timeZone=UTC"
        response = self._session.client().get(url)
        if response.status_code == 200:
            events = response.json()
            events = sorted(events, key=lambda x: self.date_string_to_datetime(x["start"]))
            return events
        else:
            logging.error(f"Error fetching calendar: {response.status_code}, {response.text}")
            return []

    def global_calendar(self, start_date: datetime.date, end_date: datetime.date, filter_events = False, filter_birthdays = False) -> list[dict]:
        start_str = start_date.strftime("%Y-%m-%dT00:00:00Z")
        end_str = end_date.strftime("%Y-%m-%dT00:00:00Z")
        url = f"{self._session.url()}/global_calendar.json?start={start_str}&end={end_str}&timeZone=UTC"
        response = self._session.client().get(url)
        if response.status_code != 200:
            logging.error(f"Error fetching calendar: {response.status_code}, {response.text}")
            return []

        all_events = response.json()
        events = []
        for event in all_events:
            if "personal_records" in event["url"]: # birthday
                if not filter_birthdays:
                    events.append(event)
            else: # normal events
                if not filter_events:
                    events.append(event)
        events = sorted(events, key=lambda x: self.date_string_to_datetime(x["start"]))
        return events
            
    
class GaudeamDriveFolder:
    def __init__(self, session: GaudeamSession, folder_id: str):
        self._session = session
        self._folder_id = folder_id

        self._properties = self._get_properties()

    def _get_properties(self) -> dict:
        url = f"{self._session.url()}/api/v1/drive/folders/{self._folder_id}"
        response = self._session.client().get(url)
        if response.status_code == 200:
            return response.json()
        else:
            logging.error(f"Error fetching folder properties: {response.status_code}, {response.text}")
            return {}

    def _properties_force_refresh(self) -> None:
        self._properties = self._get_properties()

    def get_name(self) -> str:
        return self._properties.get("name", None)

    def create_sub_folder(self, name: str, description = "") -> GaudeamDriveFolder:
        owner_id_from_parent = self._properties["owner_id"]
        restrict_to_id_from_parent = self._properties["restrict_to"]["id"]
        data = {
            "inode": {
                "description": description,
                "name": name,
                "ordering": [
                    "<name"
                ],
                "owner_id": owner_id_from_parent, 
                "owner_type": "Group",
                "parent_id": self._folder_id, # folder_id from parent folder
                "restrict_to_id": restrict_to_id_from_parent, # restrict to access group id
                "type": "Folder"
            }
        }
        url = f"{self._session.url()}/api/v1/drive/folders"
        response = self._session.client().post(url, json=data)
        if response.status_code == 200:
            self._properties_force_refresh()
            new_folder_id = response.json()["id"]
            logging.debug(f"Created sub-folder '{name}' with ID: {new_folder_id}")
            return GaudeamDriveFolder(self._session, new_folder_id)
        else:
            logging.error(f"Error creating sub-folder: {response.status_code}, {response.text}")
            return None

    def get_sub_folders(self) -> typing.List[GaudeamDriveFolder]:
        url = f"{self._session.url()}/api/v1/drive/folders?parent_id={self._folder_id}&order=%3Ename&offset=0&limit=200000"
        response = self._session.client().get(url)
        results = []
        if response.status_code == 200:
            for entry in response.json()["results"]:
                entry_type = entry["type"]
                if entry_type in ["Folder", "Gallery"]:
                    folder = GaudeamDriveFolder(self._session, entry["id"])
                    results.append(folder)
                else:
                    logging.debug(f"Skipping non-folder entry: {entry['name']} ({entry_type})")
            return results
        else:
            logging.error(f"Error fetching folder contents: {response.status_code}, {response.text}")
            return []

    def get_files(self) -> typing.List[GaudeamDriveFile]:
        url = f"{self._session.url()}/api/v1/drive/folders?parent_id={self._folder_id}&order=%3Ename&offset=0&limit=200000"
        response = self._session.client().get(url)
        results = []
        if response.status_code == 200:
            for entry in response.json()["results"]:
                entry_type = entry["type"]
                if entry_type in ["Photo", "DriveFile"]:
                    folder = GaudeamDriveFile(self._session, entry["id"])
                    results.append(folder)
                else:
                    logging.debug(f"Skipping non-file entry: {entry['name']} ({entry_type})")
            return results
        else:
            logging.error(f"Error fetching folder contents: {response.status_code}, {response.text}")
            return []

    def delete(self) -> bool:
        url = f"{self._session.url()}/api/v1/drive/folders/{self._folder_id}"
        response = self._session.client().delete(url)
        if response.status_code == 200:
            return True
        else:
            logging.error(f"Error deleting folder: {response.status_code}, {response.text}")
            return False

    def mime_type_from_filename(self, filename: str) -> str:
        extension = filename.split(".")[-1].lower()
        mime_types = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "gif": "image/gif",
            "bmp": "image/bmp",
            "tiff": "image/tiff",
            "mp4": "video/mp4",
            "mov": "video/quicktime",
            "avi": "video/x-msvideo",
            "mkv": "video/x-matroska",
            "pdf": "application/pdf",
            "doc": "application/msword",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "xls": "application/vnd.ms-excel",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "ppt": "application/vnd.ms-powerpoint",
            "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            # add more as needed
        }
        # default to binary stream
        return mime_types.get(extension, "application/octet-stream")

    def upload_folder(self, local_folder_path: Path|str) -> bool:
        local_path = Path(local_folder_path)
        if not local_path.is_dir():
            logging.error(f"Local path is not a directory: {local_folder_path}")
            return False
        for entry in scandir(local_folder_path):
            if entry.is_file():
                for file_in_folder in self.get_files():
                    if file_in_folder.get_download_name() == Path(entry.path).name:
                        logging.info(f"File already exists in remote folder, skipping upload: {entry.path}")
                        break
                else:
                    logging.info(f"Uploading file: {entry.path} to folder: {self.get_name()}")
                    success = self.upload_file(entry.path)
                    if not success:
                        logging.error(f"Failed to upload file: {entry.path}")
                        return False
            elif entry.is_dir():
                for sub_folder in self.get_sub_folders():
                    if sub_folder.get_name() == entry.name:
                        logging.info(f"Sub-folder already exists in remote folder, using existing folder: {entry.name}")
                        new_remote_folder = sub_folder
                        break
                else:
                    logging.info(f"Creating sub-folder: {entry.name} in folder: {self.get_name()}")
                    new_remote_folder = self.create_sub_folder(entry.name)
                    if new_remote_folder is None:
                        logging.error(f"Failed to create sub-folder: {entry.name}")
                        return False
                    success = new_remote_folder.upload_folder(entry.path)
                    if not success:
                        logging.error(f"Failed to upload folder: {entry.path}")
                        return False
        return True

    def upload_file(self, file_path: Path|str) -> bool:
        file_path = Path(file_path)
        # get upload signature
        url = f"{self._session.url()}/api/v1/drive/sign"
        response = self._session.client().post(url)
        if response.status_code != 200:
            logging.error(f"Error getting upload signature: {response.status_code}, {response.text}")
            return False
        sign_data = response.json()
        logging.debug(f"Upload sign data: {json.dumps(sign_data, indent=2)}")

        # upload file
        post_endpoint = sign_data["postEndpoint"]
        signature = sign_data["signature"]

        files = {'file': open(file_path, 'rb')}

        upload_response = requests.post(post_endpoint, data=signature, files=files)
        if upload_response.status_code != 201: # created
            logging.error(f"Error uploading file: {upload_response.status_code}, {upload_response.text}")
            return False
        logging.debug(f"File uploaded response: {upload_response.status_code}, {upload_response.text}")
        xml_response = upload_response.text

        # register file upload at gaudeam
        xml_response_root = ET.fromstring(xml_response)

        location = xml_response_root.find("Location").text
        bucket = xml_response_root.find("Bucket").text
        key = xml_response_root.find("Key").text
        etag = xml_response_root.find("ETag").text.strip('"')  # remove quotes around ETag

        print("Location:", location)
        print("Bucket:", bucket)
        print("Key:", key)
        print("ETag:", etag)

        upload_url = f"{self._session.url()}/api/v1/drive/uploaded_files"
        path = Path(file_path)
        filename_without_ext = path.stem
        filename_with_ext = path.name

        data = {
            "inode": {
                "content_type": self.mime_type_from_filename(filename_with_ext),
                "name": filename_without_ext, # Gaudeam usually skips the extension in the name
                "parent_id": self._folder_id,
                "physically_created_at": "",
                "stored_file": key,
                # only for images
                #"height": 4080,
                #"width": 3072,
            }
        }
        upload_response = self._session.client().post(upload_url, json=data)
        if upload_response.status_code != 200:
            logging.error(f"Error confirming uploaded file: {upload_response.status_code}, {upload_response.text}")
            return False
        logging.debug(f"Uploaded file confirmation response: {upload_response.status_code}, {upload_response.text}")
        return True

    def download(self, destination_path: Path|str) -> bool:
        destination_folder = Path(destination_path)

        if not destination_folder.exists():
            logging.debug(f"Destination does not exist yet, creating '{destination_folder}'")
            destination_folder.mkdir(parents=True)

        for sub_folder in self.get_sub_folders():
            folder_name = sub_folder.get_name()
            sub_folder.download(destination_folder / folder_name)

        for file_in_folder in self.get_files():
            file_name = file_in_folder.get_download_name()
            destination_file = destination_folder / file_name
            if destination_file.exists():
                logging.info(f"Skipping '{destination_file}' - already exists")
                continue
            # download file
            file_in_folder.download(destination_file)
class GaudeamDriveFile:
    def __init__(self, session: GaudeamSession, file_id: str):
        self._session = session
        self._file_id = file_id

        self._properties = self._get_properties()

    def _get_properties(self) -> dict:
        url = f"{self._session.url()}/api/v1/drive/folders/{self._file_id}"
        response = self._session.client().get(url)
        if response.status_code == 200:
            return response.json()
        else:
            logging.error(f"Error fetching folder properties: {response.status_code}, {response.text}")
            return {}

    def _properties_force_refresh(self) -> None:
        self._properties = self._get_properties()

    def get_name(self) -> str:
        return self._properties.get("name", None)

    def get_properties(self) -> dict:
        return self._properties

    def get_download_name(self) -> str:
        return self._properties.get("download_name", None)

    def download(self, file_path: str|Path) -> bool:
        url = f"{self._session.url()}/drive/uploaded_files/{self._file_id}/download"
        response = self._session.client().get(url)

        # TODO: error handling

        # Save as binary file
        with open(file_path, "wb") as f:
            f.write(response.content)
        return True

    def delete(self) -> bool:
        url = f"{self._session.url()}/api/v1/drive/uploaded_files/{self._file_id}"
        response = self._session.client().delete(url)
        if response.status_code == 200:
            return True
        else:
            logging.error(f"Error deleting file: {response.status_code}, {response.text}")
            return False

class GaudeamDrive:
    def __init__(self, session: GaudeamSession):
        self._session = session

    def get_sub_folders(self) -> list[GaudeamDriveFolder]:
        url = f"{self._session.url()}/api/v1/drive/categories"
        response = self._session.client().get(url)
        if response.status_code == 200:
            return response.json()["results"]
        else:
            logging.error(f"Error fetching folders: {response.status_code}, {response.text}")
            return []
    
    def delete_folder(self, folder_id: str) -> bool:
        url = f"{self._session.url()}/api/v1/drive/folders/{folder_id}"
        response = self._session.client().delete(url)
        if response.status_code == 200:
            return True
        else:
            logging.error(f"Error deleting folder: {response.status_code}, {response.text}")
            return False