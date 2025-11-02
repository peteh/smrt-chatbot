from __future__ import annotations
import logging
import json
import datetime
import typing
import xml.etree.ElementTree as ET
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import tempfile
from PIL import Image
class GaudeamSession():
    """Session information to talk to Gaudeam. 
    """

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
        if status == 302: # redirect, login successful
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
    """Member directory of the gaudeam instance. 
    """
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
    """Class to access global and user calendar from gaudeam.de"""

    def __init__(self, gaudeam_session: GaudeamSession):
        self._session = gaudeam_session

    @staticmethod
    def date_string_to_datetime(date: str) -> datetime.datetime:
        """Gives a date time object back for dates in the following formats: 
            2025-11-02T14:23:45.123456Z
            Sun, 02 Nov 2025 14:23:45 +0000
        Args:
            date (str): The date string

        Returns:
            datetime.datetime: The parsed datetime
        """
        if date[-1] == "Z":
            dt = datetime.datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%fZ")
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        else:
            dt = datetime.datetime.strptime(date, "%a, %d %b %Y %H:%M:%S %z")
        return dt.astimezone(datetime.timezone.utc)

    def user_calendar(self, start_date: datetime.date, end_date: datetime.date) -> list[dict]:
        """Returns the custom user calendar for the currently logged in user. 

        Args:
            start_date (datetime.date): The start time to collect entries
            end_date (datetime.date): The end time to collect entries

        Returns:
            list[dict]: The list of events in this time
        """
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

    def global_calendar(self, start_date: datetime.date, end_date: datetime.date) -> list[GaudeamEvent]:
        """Returns events from the global calendar of the instance. 

        Args:
            start_date (datetime.date): The start time from which to collect events
            end_date (datetime.date): The end time till which to collect events

        Returns:
            list[dict]: List of events
        """
        start_str = start_date.strftime("%Y-%m-%dT00:00:00Z")
        end_str = end_date.strftime("%Y-%m-%dT00:00:00Z")
        url = f"{self._session.url()}/global_calendar.json?start={start_str}&end={end_str}&timeZone=UTC"
        response = self._session.client().get(url)
        if response.status_code != 200:
            logging.error(f"Error fetching calendar: {response.status_code}, {response.text}")
            return []

        all_events = response.json()
        events = []
        for event_data in all_events:
            if "personal_records" in event_data["url"]: # skip, it's a birthday
                continue
            else: # normal events
                event_id = event_data["id"]
                events.append(GaudeamEvent(self._session, event_id, event_data))
        events = sorted(events, key=lambda x: self.date_string_to_datetime(x._properties["start"]))

        return events

class GaudeamEvent():
    def __init__(self, session: GaudeamSession, event_id: str, properties: dict = None):
        self._session = session
        self._event_id = event_id
        if properties is None:
            self._properties = self._get_properties()
        else:
            self._properties = properties

    def _get_properties(self) -> dict:
        url = f"{self._session.url()}/api/v1/events/{self._event_id}"
        response = self._session.client().get(url)
        if response.status_code == 200:
            return response.json()
        else:
            raise ValueError(f"Error fetching event properties for event '{self._event_id}': {response.status_code}, {response.text}")

    def get_title(self) -> str:
        return self._properties["title"]

    def get_description(self) -> str:
        return self._properties["description"]
    
    def get_event_url(self) -> str:
        return self._properties["url"]
    
    def download_media(self, folder_path: Path|str):
        folder_path = Path(folder_path)
        for post in self.get_posts():
            creator_name = post.get_creator_name()

            for media in post.get_media():
                sub_folder = folder_path / creator_name
                if not sub_folder.exists():
                    sub_folder.mkdir(parents=True)
                file_name = media.get_download_name()
                
                save_path = sub_folder / file_name
                if save_path.exists():
                    logging.info(f"Skipping {save_path}: File already exists")
                    continue
                media.download(save_path)

    def get_start_datetime(self) -> datetime.datetime:
        return GaudeamCalendar.date_string_to_datetime(self._properties["start"])

    def get_posts(self) -> typing.List[EventPost]:
        url = f"{self._session.url()}/api/v1/events/{self._event_id}/posts"
        response = self._session.client().get(url)
        if response.status_code == 200:
            post_list = []
            for post_data in response.json():
                post_id = post_data["id"]
                post = EventPost(self._session, self._event_id, post_id, post_data)
                post_list.append(post)
            return post_list
        else:
            raise ValueError(f"Could not get posts for event_id '{self._event_id}'")

class EventPost():
    
    def __init__(self, session: GaudeamSession, event_id: str, post_id: str, properties = None):
        self._session = session
        self._event_id = event_id
        self._post_id = post_id
        if properties is None:
            self._properties = self._get_properties()
        else:
            self._properties = properties

    def _get_properties(self) -> dict:
        url = f"{self._session.url()}/api/v1/events/{self._event_id}/posts/{self._post_id}"
        response = self._session.client().get(url)
        if response.status_code == 200:
            return response.json()
        else:
            raise ValueError(f"Error fetching post properties for post '{self._post_id}': {response.status_code}, {response.text}")

    def get_creator_name(self) -> str:
        return self._properties["creator"]["full_name"]
        
    def get_media(self) -> GaudeamMedia: 
        #/api/v1/posts/post_id/event_media
        url = f"{self._session.url()}/api/v1/posts/{self._post_id}/event_media"
        response = self._session.client().get(url)
        if response.status_code == 200:
            media_list = []
            for media_data in response.json():
                media_id = media_data["id"]
                media_list.append(GaudeamMedia(self._session, media_id, media_data))
            return media_list
        else:
            raise ValueError(f"Could not get media for post_id '{self._post_id}'")

class GaudeamMedia():
    def __init__(self, session: GaudeamSession, media_id: str, properties: dict):
        self._session = session
        self._media_id = media_id
        self._properties = properties
    
    def get_properties(self):
        return self._properties
    
    def get_download_name(self) -> str:
        return self._properties["uploaded_file"]["file_name"]
    
    def download(self, file_path: str|Path) -> bool:
        """Downloads a file to a local path

        Args:
            file_path (str | Path): The path to save the file to

        Returns:
            bool: True if the download was successful.
        """
        # TODO: the download link does actually not work
        #file_id = self._properties["uploaded_file"]["id"]
        #url = f"{self._session.url()}/drive/uploaded_files/{file_id}/download"
        
        url = self._properties["uploaded_file"]["original"]["url"]
        response = self._session.client().get(url)
        if response.status_code != 200:
            raise ValueError(f"Could not download media '{self._media_id}' on {url}")
        # TODO: error handling

        # Save as binary file
        with open(file_path, "wb") as f:
            f.write(response.content)
        return True
        
class GaudeamDriveFolder:
    def __init__(self, session: GaudeamSession, folder_id: str, properties = None):
        self._session = session
        self._folder_id = folder_id
        if properties is None:
            self._properties = self._get_properties()
        else:
            self._properties = properties

    def _get_properties(self) -> dict:
        url = f"{self._session.url()}/api/v1/drive/folders/{self._folder_id}"
        response = self._session.client().get(url)
        if response.status_code == 200:
            return response.json()
        else:
            raise ValueError(f"Error fetching drive folder properties for folder '{self._folder_id}': {response.status_code}, {response.text}")

    def _properties_force_refresh(self) -> None:
        self._properties = self._get_properties()

    def get_name(self) -> str:
        """Gets the name of the folder

        Returns:
            str: Name of the folder
        """
        return self._properties.get("name", None)

    def create_sub_folder(self, name: str, description: str = "") -> GaudeamDriveFolder:
        """Creates a new folder with the same rights as the parent. 

        Args:
            name (str): Name of the new folder
            description (str, optional): Optional description of the folder. Defaults to "".

        Returns:
            GaudeamDriveFolder: The newly created folder
        """
        owner_type = self._properties["owner_type"]
        owner_id_from_parent = self._properties["owner_id"]
        
        data = {
            "inode": {
                "description": description,
                "name": name,
                "ordering": [
                    "<name"
                ],
                "owner_id": owner_id_from_parent, 
                #"owner_type": "Group",
                "parent_id": self._folder_id, # folder_id from parent folder
                #"restrict_to_id": restrict_to_id_from_parent, # restrict to access group id
                "type": "Folder"
            }
        }
        # parent owner is a group, we copy the settings
        if owner_type == "Group":
            restrict_to_id_from_parent = self._properties["restrict_to"]["id"]
            data["inode"]["owner_type"] = "Group"
            data["inode"]["restrict_to_id"] = restrict_to_id_from_parent
        # parent owner is a Member, we copy member settings
        elif owner_type == "GroupMember":
            data["inode"]["owner_type"] = "GroupMember"
            data["inode"]["restrict_to_id"] = None
        else:
            raise RuntimeError("cannot create file as parent is not owned by GroupMember or Group")

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
        """Returns a lift of sub folders in the current folder. 

        Returns:
            typing.List[GaudeamDriveFolder]: List of sub folders
        """
        url = f"{self._session.url()}/api/v1/drive/folders?parent_id={self._folder_id}&order=%3Ename&offset=0&limit=200000"
        response = self._session.client().get(url)
        results = []
        if response.status_code == 200:
            for entry in response.json()["results"]:
                entry_type = entry["type"]
                if entry_type in ["Folder", "Gallery"]:
                    folder = GaudeamDriveFolder(self._session, entry["id"], entry)
                    results.append(folder)
                else:
                    #logging.debug(f"Skipping non-folder entry: {entry['name']} ({entry_type})")
                    pass
            return results
        else:
            logging.error(f"Error fetching folder contents: {response.status_code}, {response.text}")
            return []

    def get_files(self) -> typing.List[GaudeamDriveFile]:
        """Gets a list of files in the folder

        Returns:
            typing.List[GaudeamDriveFile]: List of files
        """
        url = f"{self._session.url()}/api/v1/drive/folders?parent_id={self._folder_id}&order=%3Ename&offset=0&limit=200000"
        response = self._session.client().get(url)
        results = []
        if response.status_code == 200:
            for entry in response.json()["results"]:
                entry_type = entry["type"]
                if entry_type in ["Photo", "DriveFile"]:
                    folder = GaudeamDriveFile(self._session, entry["id"], entry)
                    results.append(folder)
                else:
                    #logging.debug(f"Skipping non-file entry: {entry['name']} ({entry_type})")
                    pass
            return results
        else:
            logging.error(f"Error fetching folder contents: {response.status_code}, {response.text}")
            return []

    def delete(self) -> bool:
        """Deletes the folder including all files. 

        Returns:
            bool: True if deletion was successful
        """
        url = f"{self._session.url()}/api/v1/drive/folders/{self._folder_id}"
        response = self._session.client().delete(url)
        if response.status_code == 200:
            return True
        else:
            logging.error(f"Error deleting folder: {response.status_code}, {response.text}")
            return False
    
    def delete_content(self) -> bool:
        """Deletes the content of a folder

        Returns:
            bool: True if all files and folders could be deleted
        """
        success = True
        for folder in self.get_sub_folders():
            folder_name = folder.get_name()
            logging.info(f"Deleting folder: {folder_name}")
            if not folder.delete():
                logging.warning(f"Could not delete folder '{folder_name}'")
                success = False
        for file in self.get_files():
            file_name = file.get_name()
            logging.info(f"Deleting folder: {file_name}")
            if not file.delete():
                logging.warning(f"Could not delete file '{file_name}'")
                success = False
        return success

    def _mime_type_from_filename(self, filename: str) -> str:
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

    def get_size(self) -> int:
        """Returns the file size of the folder including all sub folders. 

        Returns:
            int: The file size of the folder.
        """
        size = 0
        for sub_folder in self.get_sub_folders():
            size += sub_folder.get_size()
        for file in self.get_files():
            size += file.get_size()
        return size

    def upload_folder(self, local_folder_path: Path|str) -> bool:
        """Uploads a local folder to the Gaudeam folder. 
        It skips all files that already exist with the same 'download name'. 

        Args:
            local_folder_path (Path | str): Local path of the folder to upload

        Returns:
            bool: True if upload was successful
        """
        local_folder_path = Path(local_folder_path)
        if not local_folder_path.is_dir():
            logging.error(f"Local path is not a directory: {local_folder_path}")
            return False
        for entry in local_folder_path.iterdir():
            if entry.is_file():
                for file_in_folder in self.get_files():
                    if file_in_folder.get_download_name() == entry.name:
                        logging.info(f"File already exists in remote folder, skipping upload: {entry}")
                        break
                else:
                    logging.info(f"Uploading file: {entry} to folder: {self.get_name()}")
                    success = self.upload_file(entry)
                    if not success:
                        logging.error(f"Failed to upload file: {entry}")
                        return False
            elif entry.is_dir():
                # check if folder already exists
                # if exists -> use existing and continue upload into it
                # if not -> create folder and continue upload into it
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
                success = new_remote_folder.upload_folder(entry)
                if not success:
                    logging.error(f"Failed to upload folder: {entry}")
                    return False
        return True

    def upload_file(self, file_path: Path|str) -> bool:
        """Uploads a specific file to this folder. 

        Args:
            file_path (Path | str): The local file path to the file to upload

        Returns:
            bool: True if the upload was successful
        """
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
        #logging.debug(f"File uploaded response: {upload_response.status_code}, {upload_response.text}")
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
                "content_type": self._mime_type_from_filename(filename_with_ext),
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
        #logging.debug(f"Uploaded file confirmation response: {upload_response.status_code}, {upload_response.text}")
        return True

    def download(self, destination_path: Path|str) -> bool:
        """Downloads the whole folder including sub folders and files to a local folder. 
        It skips files that already exist based on 'download name'. 

        Args:
            destination_path (Path | str): Destination path to download to. 

        Returns:
            bool: True if the download was successful
        """
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
    """A file on gaudeam drive. 
    """
    def __init__(self, session: GaudeamSession, file_id: str, properties = None):
        self._session = session
        self._file_id = file_id
        if properties is None:
            self._properties = self._get_properties()
        else:
            self._properties = properties

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
        """Returns the human readable name on gaudeam, usually without file extensions

        Returns:
            str: name of the file on gaudeam. 
        """
        return self._properties.get("name", None)

    def get_properties(self) -> dict:
        return self._properties

    def get_download_name(self) -> str:
        """Returns the download name of the file. This is the original file name with the full file extension. 

        Returns:
            str: The download name. 
        """
        return self._properties.get("download_name", None)

    def get_size(self) -> int:
        """Returns the filesize in bytes. 

        Returns:
            int: filesize in bytes
        """
        return self._properties["file_size"]

    def download(self, file_path: str|Path) -> bool:
        """Downloads a file to a local path

        Args:
            file_path (str | Path): The path to save the file to

        Returns:
            bool: True if the download was successful.
        """
        url = f"{self._session.url()}/drive/uploaded_files/{self._file_id}/download"
        response = self._session.client().get(url)

        # TODO: error handling

        # Save as binary file
        with open(file_path, "wb") as f:
            f.write(response.content)
        return True

    def delete(self) -> bool:
        """Deletes a file from the drive

        Returns:
            bool: True if the deletion was successful
        """
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

class GaudeamResizedImageUploader():
    def __init__(self, max_width: int = 2000, max_height: int = 2000, jpeg_quality = 90):
        self._max_width = max_width
        self._max_height = max_height
        self._jpeg_quality = jpeg_quality
        self._skip_file_names = []
        self._allowed_extensions = [".jpg", ".jpeg", ".png"]

    def add_skip_file_name(self, skip_file_name: str):
        self._skip_file_names.append(skip_file_name)

    def save_as_jpeg_resized(self, input_path, output_path):
        img = Image.open(input_path)

        # Keep aspect ratio
        img.thumbnail((self._max_width, self._max_height), Image.Resampling.LANCZOS)

        # Ensure no alpha channel (JPEG doesn’t support transparency)
        if img.mode in ("RGBA", "LA"):
            img = img.convert("RGB")

        img.save(output_path, format="JPEG", quality=self._jpeg_quality)

    def _in_allowed_extensions(self, file_path: Path) -> bool:
        source_extension = file_path.suffix.lower()
        ## skip files based on extension
        return source_extension in self._allowed_extensions

    def _in_skip_files(self, file_path: Path) -> bool:
        file_name = str(file_path.name)
        for skip_file_name in self._skip_file_names:
            if str(skip_file_name).lower() in file_name.lower():
                # skip files that contain the substring which is in skipfile in the file name
                return True
        return False
    
    def _file_name_exists(self, file_name: str,  gaudeam_files_in_folder: typing.List[GaudeamDriveFile]):
        for file_in_folder in gaudeam_files_in_folder:
            if file_in_folder.get_download_name() == file_name:
                return True
        return False
    
    def delete_remote_orphan_files(self, local_folder_path: Path|str, gaudeam_folder: GaudeamDriveFolder, dry_run = False):
        local_folder_path = Path(local_folder_path)
        local_sub_folders = [
                            item.name
                            for item in local_folder_path.iterdir()
                            if item.is_dir()
                        ]
        local_target_file_names = [
                            self._get_target_name_from_file_path(item)
                            for item in local_folder_path.iterdir()
                            if item.is_file() \
                                and self._in_allowed_extensions(item) \
                                and not self._in_skip_files(item)
                        ]
        for gaudeam_sub_folder in gaudeam_folder.get_sub_folders():
            gaudeam_sub_folder_name = gaudeam_sub_folder.get_name()
            if gaudeam_sub_folder_name not in local_sub_folders:
                # folder does not exist locally -> delete
                if not dry_run:
                    logging.warning(f"Deleting gaudeam folder '{gaudeam_sub_folder_name}' because it's not in {local_folder_path}")
                    gaudeam_sub_folder.delete()
                else:
                    logging.info(f"[DRY_RUN] Deleting gaudeam folder '{gaudeam_sub_folder_name}' because it's not in {local_folder_path}")
            else:
                # folder exists locally -> check it's sub contents
                sub_folder_path = local_folder_path / gaudeam_sub_folder_name
                self.delete_remote_orphan_files(sub_folder_path, gaudeam_sub_folder)

        for gaudeam_sub_file in gaudeam_folder.get_files():
            gaudeam_sub_file_name = gaudeam_sub_file.get_download_name()
            if gaudeam_sub_file_name not in local_target_file_names:
                if not dry_run:
                    logging.warning(f"Deleting gaudeam file '{gaudeam_sub_file_name}' because it's not derived from a file in {local_folder_path}")
                    gaudeam_sub_file.delete()
                else:
                    logging.info(f"[DRY_RUN] Deleting gaudeam file '{gaudeam_sub_file_name}' because it's not derived from a file in {local_folder_path}")

    def _get_target_name_from_file_path(self, local_file_path: Path):
        local_file_path = Path(local_file_path)
        target_extension = ".jpg"
        target_name = local_file_path.stem + target_extension
        return target_name

    def upload_folder_resized(self, local_folder_path: Path|str, gaudeam_folder: GaudeamDriveFolder) -> bool:
        local_folder_path = Path(local_folder_path)
        if not local_folder_path.is_dir():
            logging.error(f"Local path is not a directory: {local_folder_path}")
            return False
        # get the files that already exist in the folder
        gaudeam_files_in_folder = gaudeam_folder.get_files()
        gaudeam_sub_folders_in_folder = gaudeam_folder.get_sub_folders()
        for entry in local_folder_path.iterdir():
            if entry.is_file():
                ## skip files based on extension
                if not self._in_allowed_extensions(entry):
                    # skip files like videos, that we don't want to upload
                    logging.info(f"Skipping: {entry}: File type is not in processing list ({self._allowed_extensions})")
                    continue

                ## skip files based on name blacklist
                if self._in_skip_files(entry):
                    logging.info(f"Skipping: {entry}: File name is skipped because it contains a blacklisted name ({self._skip_file_names}), ")
                    continue

                ## skip files if they already exist remotely
                target_name = self._get_target_name_from_file_path(entry)
                if self._file_name_exists(target_name, gaudeam_files_in_folder):
                    logging.info(f"Skipping: {entry}: File already exists in remote folder as '{target_name}'")
                    continue

                # if not exists, upload shrinked version
                with tempfile.TemporaryDirectory() as tmpdirname:
                    target_path = Path(tmpdirname) / target_name
                    logging.info(f"Resizing file: {entry} as: {target_path}")
                    self.save_as_jpeg_resized(entry, target_path)
                    logging.info(f"Uploading file: {target_path} to folder: {gaudeam_folder.get_name()}")
                    success = gaudeam_folder.upload_file(target_path)
                    if not success:
                        logging.error(f"Failed to upload file: {target_path}")
                        return False
            elif entry.is_dir():
                for sub_folder in gaudeam_sub_folders_in_folder:
                    if sub_folder.get_name() == entry.name:
                        logging.info(f"Sub-folder already exists in remote folder, using existing folder: {entry.name}")
                        new_remote_folder = sub_folder
                        break
                else:
                    logging.info(f"Creating sub-folder: {entry.name} in folder: {gaudeam_folder.get_name()}")
                    new_remote_folder = gaudeam_folder.create_sub_folder(entry.name)
                    if new_remote_folder is None:
                        logging.error(f"Failed to create sub-folder: {entry.name}")
                        return False
                success = self.upload_folder_resized(entry, new_remote_folder)
                if not success:
                    logging.error(f"Failed to upload folder: {entry.path}")
                    return False
        return True