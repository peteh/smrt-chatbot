import requests
import logging
import json
import datetime

class Gaudeam:
    def __init__(self, gaudeam_session):
        self._client = requests.Session()
        self._client.cookies.update({"_gaudeam_session": gaudeam_session})
        self._url = "https://ulmia-stuttgart.gaudeam.de"

    def members(self, include_dead=False, include_alliances=False, include_resigned=False, seach_term=""):
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
        response_count = self._client.get(f"{self._url}/api/v1/members/count", params=params)
        num_records = response_count.json()["count"]
        response_members = self._client.get(f"{self._url}/api/v1/members/index", params=params)
        members = response_members.json()["results"]
        while len(members) < num_records:
            offset += limit
            params["offset"] = offset
            response_members = self._client.get("https://ulmia-stuttgart.gaudeam.de/api/v1/members/index", params=params)
            members.extend(response_members.json()["results"])
        return members

    def calendar(self, start_date: datetime.date, end_date: datetime.date) -> list[dict]:
        start_str = start_date.strftime("%Y-%m-%dT00:00:00Z")
        end_str = end_date.strftime("%Y-%m-%dT00:00:00Z")
        url = f"{self._url}/user_calendar.json?start={start_str}&end={end_str}&timeZone=UTC"
        response = self._client.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            logging.error(f"Error fetching calendar: {response.status_code}, {response.text}")
            return []