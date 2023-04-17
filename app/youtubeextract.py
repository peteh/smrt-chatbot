import youtube_transcript_api
import youtube_transcript_api.formatters
import urllib.parse


class YoutubeExtract():
    def __init__(self, link: str) -> None:
        self._link = link

    @staticmethod
    def _extractYoutubeVideoId(link):
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
    def isYoutubeLink(link: str) -> bool:
        return YoutubeExtract._extractYoutubeVideoId(link) is not None

    def getScript(self):
        videoId = self._extractYoutubeVideoId(self._link)
        transcript = youtube_transcript_api.YouTubeTranscriptApi.get_transcript(videoId, languages=['en', 'de'])
        textFormatter = youtube_transcript_api.formatters.TextFormatter()
        
        text = textFormatter.format_transcript(transcript)
        return text