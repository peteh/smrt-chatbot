"""Youtube extractor for links and subtitles"""
import urllib.parse
import youtube_transcript_api
import youtube_transcript_api.formatters

class YoutubeExtract():
    """Extracts youtube subtitles from links. """
    def __init__(self, link: str) -> None:
        self._link = link

    @staticmethod
    def _extract_youtube_video_id(link):
        """
        Examples:
        - http://youtu.be/SA2iWivDJiE
        - http://www.youtube.com/watch?v=_oPAwA_Udwc&feature=feedu
        - http://www.youtube.com/embed/SA2iWivDJiE
        - http://www.youtube.com/v/SA2iWivDJiE?version=3&amp;hl=en_US
        """
        query = urllib.parse.urlparse(link)
        if query.hostname == 'youtu.be':
            return query.path[1:]
        if query.hostname in ('www.youtube.com', 'youtube.com', "m.youtube.com"):
            if query.path == '/watch':
                p = urllib.parse.parse_qs(query.query)
                return p['v'][0]
            if query.path[:7] == '/embed/':
                return query.path.split('/')[2]
            if query.path[:3] == '/v/':
                return query.path.split('/')[2]
        # fail?
        return None

    @staticmethod
    def is_youtube_link(link: str) -> bool:
        """Checks if a link is a youtube link

        Args:
            link (str): The link to check

        Returns:
            bool: True if the link is a youtube link. 
        """
        return YoutubeExtract._extract_youtube_video_id(link) is not None

    def get_script(self) -> str:
        """Gets the script from the youtube link. 

        Returns:
            str: script of the youtube video. 
        """
        video_id = self._extract_youtube_video_id(self._link)
        transcript = youtube_transcript_api.YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'de'])
        text_formatter = youtube_transcript_api.formatters.TextFormatter()

        text = text_formatter.format_transcript(transcript)
        return text
