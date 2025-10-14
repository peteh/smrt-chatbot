import trafilatura
import requests
from bs4 import BeautifulSoup

class PageUnlocker:
    def __init__(self, link: str):
        self._link = link
        self._headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36'}
        self._session = requests.Session()

        self._markers= {
            "spiegel.de": "paywall-purchase-button",
            "faz.net": '<div class="wall__wrapper">', 
            "bild.de": '<div class="offer-module">'
        }
        
    def is_paywalled(self) -> bool:
        for url_part, marker in self._markers.items():
            if url_part in self._link:
                response = self._session.get(self._link, headers=self._headers)
                if marker in response.content.decode("utf-8"):
                    return True
        return False

    def _getArchiveIsLink(self):
        response = self._session.get(f"https://archive.is/{self._link}", headers=self._headers)
        soup = BeautifulSoup(response.content, features="lxml")
        data = soup.findAll('div',attrs={'class':'THUMBS-BLOCK'})
        if len(data) != 1:
            return None
        links = data[0].findAll("a")
        if len(links) > 0:
            return links[-1]["href"]
        return None

    def unpaywall(self):
        archiveIsLink = self._getArchiveIsLink()
        if archiveIsLink is None:
            return None
        response = self._session.get(archiveIsLink, headers=self._headers)
        #response = self._session.get(self._link, headers=self._headers)
        config = trafilatura.settings.use_config()
        config.set("DEFAULT", "EXTRACTION_TIMEOUT", "0")
        extracted_text = trafilatura.extract(response.content, config=config)
        print(extracted_text)