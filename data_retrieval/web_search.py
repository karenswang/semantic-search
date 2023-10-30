from googleapiclient.discovery import build
import os

class ArticleFetcher:
    def __init__(self):
        self.google_api_key = os.getenv('google_api_key')
        self.google_engine_id = os.getenv('google_engine_id')
        self.service = build("customsearch", "v1", developerKey=self.google_api_key)

    def fetch_articles(self, query, date_restrict="d"):
        """
        Fetch articles based on the provided query.

        :param query: Search query or parameters
        :param date_restrict: Restrict search by date (default is 'd' for day)
        :return: List of articles
        """
        # res is a Python object built from the JSON response sent by the API server
        res = (
            self.service.cse()
            .list(
                q=query,
                cx=self.google_engine_id,
                dateRestrict=date_restrict,
            )
            .execute()
        )

        articles = [{"title": item['title'], "snippet": item['snippet'], "link": item['link']} for item in res.get('items', [])]
        return articles
