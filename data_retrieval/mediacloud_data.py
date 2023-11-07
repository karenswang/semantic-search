from waybacknews.searchapi import SearchApiClient
# from mediacloud import api
from datetime import datetime
from IPython.display import display, HTML
import pandas as pd

# Query parameters
query_term = 'police shooting'
start =  datetime(2023, 10, 24)
end = datetime.today()
language = "en"

domains = ['nytimes.com','cnn.com','foxnews.com','nypost.com','washingtonpost.com','usatoday.com','cnbc.com',
              'theguardian.com','breakingnews.com','buzzfeed.com','cbsnews.com','reuters.com','huffingtonpost.com',
              'usnews.com','latimes.com','politico.com','newsweek.com','breitbart.com',]
domains_str = f"domain:({' OR '.join(domains)})"

query = f"{query_term} AND language:{language} AND {domains_str}"
print(query)

# Instantiate API
api = SearchApiClient("mediacloud")
article_generator = api.all_articles(query, start, end)

articles = []
for list_of_articles in article_generator:
    articles += list_of_articles    

print(f"all_articles endpoint: {len(articles)} articles")

results = pd.DataFrame(articles)\
        .sort_values(by='publication_date', ascending=False)

results.to_csv('data_storage/results_df.csv', index=False)

