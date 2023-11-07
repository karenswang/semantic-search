from data_retrieval.web_search import ArticleFetcher
from data_storage.google_sheets import GoogleSheetsStorage

class PoliceShootingsPoliciesSearch:
    def __init__(self, json_keyfile_path, spreadsheet_id):
        self.article_fetcher = ArticleFetcher()
        self.google_sheets_storage = GoogleSheetsStorage(json_keyfile_path)
        self.spreadsheet_id = spreadsheet_id

    def execute(self):
        query = '"police shooting" OR "shot by police" OR "police shot" OR "officer-involved shooting" OR "police-involved shooting" OR "police officer shooting" OR "police officer shot"'
        articles = self.article_fetcher.fetch_articles(query)

        if articles:
            values = [["Title", "Snippet", "URL"]] + [[article['title'], article['snippet'], article['link']] for article in articles]
            self.google_sheets_storage.append_data(self.spreadsheet_id, 'Sheet1!A1', values)
        else:
            print("No articles found for the provided query.")
