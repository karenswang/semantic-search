from waybacknews.searchapi import SearchApiClient
from datetime import datetime
import pandas as pd
import requests
from retrying import retry
import requests_cache
from tqdm import tqdm

# Enable requests cache
requests_cache.install_cache('article_cache')

# Query parameters
query_term = '"police shooting" OR "shot by police" OR "police shot" OR "officer-involved shooting" OR "police-involved shooting" OR "police officer shooting" OR "police officer shot"'
start = datetime(2023, 8, 1)
end = datetime.today()
language = "en"

# Domains to search within
domains = ['nytimes.com','cnn.com','foxnews.com','nypost.com','washingtonpost.com','usatoday.com','cnbc.com',
              'theguardian.com','breakingnews.com','buzzfeed.com','cbsnews.com','reuters.com','huffingtonpost.com',
              'usnews.com','latimes.com','politico.com','newsweek.com','breitbart.com',]
domains_str = f"domain:({' OR '.join(domains)})"

query = f"{query_term} AND language:{language} AND {domains_str}"
print(f"Query: {query}")

# Instantiate API
api = SearchApiClient("mediacloud")

def get_snippet(url):
    response = requests.get(url)
    response.raise_for_status()  
    return response.json().get('snippet', '')

# Retrieve article URLs and snippets
articles = []
for list_of_articles in api.all_articles(query, start, end):
    articles.extend(list_of_articles)

print(f"all_articles endpoint: {len(articles)} articles")

results = pd.DataFrame(articles).sort_values(by='publication_date', ascending=False)

# Apply the get_snippet function to each wayback machine url
for index, article in tqdm(results.iterrows(), total=results.shape[0]):
    try:
        article_url = article['article_url']
        article_snippet = get_snippet(article_url)
        results.at[index, 'snippet'] = article_snippet
    except Exception as e:
        print(f"Error retrieving snippet for {article_url}: {e}")
        results.at[index, 'snippet'] = None  # or some placeholder text

results.to_csv('data_storage/results_df_with_snippets.csv', index=False)
print("Data retrieval complete. Results saved to 'data_storage/results_df_with_snippets.csv'.")

