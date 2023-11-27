from waybacknews.searchapi import SearchApiClient
from datetime import datetime
import pandas as pd
import requests
from retrying import retry
import requests_cache
from tqdm import tqdm
import mediacloud.api
from newspaper import Article
import unicodedata

# get news domains
collection_id = "38379429"
directory_api = mediacloud.api.DirectoryApi(auth_token='e85cce24da8b73eaa05329d258146c044ef055db')
sources_response = directory_api.source_list(collection_id=collection_id)
domains = [source['homepage'] for source in sources_response['results']]
cleaned_domains = [domain.replace('https://www.', '').replace('http://www.', '').replace('https://','').replace('http://','') for domain in domains]
cleaned_domains = [url.rstrip('/') for url in cleaned_domains]
# print(cleaned_domains)

# Enable requests cache
requests_cache.install_cache('article_cache')

# Query parameters
query_term = '("police shooting" OR "shot by police" OR "police shot" OR "officer-involved shooting" OR "police-involved shooting" OR "police officer shooting" OR "police shot" OR "officer shot")'
# query_term = '("police shooting" OR "shot by police" OR "police shot" OR "officer-involved shooting" OR "police-involved shooting" OR "police officer shooting" OR "police shot" OR "officer shot" OR "deputy shot" OR "sheriff shot" OR "cop shot")'
# query_term = 'police AND shot'
start = datetime(2023, 11, 6) #11/6 - 11/15
end = datetime(2023, 11, 15) 
language = "en"

# Domains to search within
# domains = ['nytimes.com','cnn.com','foxnews.com','nypost.com','washingtonpost.com','usatoday.com','cnbc.com',
#               'theguardian.com','breakingnews.com','buzzfeed.com','cbsnews.com','reuters.com','huffingtonpost.com',
#               'usnews.com','latimes.com','politico.com','newsweek.com','breitbart.com',]
domains_str = f"domain:({' OR '.join(cleaned_domains)})"
print(domains_str)

query = f"{query_term} AND language:{language} AND {domains_str}"
# print(f"Query: {query}")

# Instantiate API
api = SearchApiClient("mediacloud")

def get_snippet(url):
    response = requests.get(url)
    response.raise_for_status()  
    snippet = response.json().get('snippet', '')
    return snippet
    # return response.json().get('snippet', '')

def sanitize_snippet(snippet):
    sanitized_snippet = snippet.replace('\n', ' ').replace('\r', '').strip()
    # Normalize Unicode characters
    normalized_snippet = unicodedata.normalize('NFKD', sanitized_snippet)
    return sanitized_snippet
# Retrieve article URLs and snippets
articles = []
for list_of_articles in api.all_articles(query, start, end):
    articles.extend(list_of_articles)

print(f"all_articles endpoint: {len(articles)} articles")

results = pd.DataFrame(articles).sort_values(by='publication_date', ascending=False)

# Apply the get_snippet function to each wayback machine url
for index, article in tqdm(results.iterrows(), total=results.shape[0]):
    try:
        article_url = article['url']
        
        extracted_article = Article(article_url)
        extracted_article.download()
        extracted_article.parse()
        article_snippet = extracted_article.text
        sanitized_snippet = sanitize_snippet(article_snippet)
        # Encode the snippet in utf-8
        # encoded_snippet = sanitized_snippet.encode('utf-8')
        results.loc[index, 'snippet'] = sanitized_snippet
    #     article_url = article['article_url']
    #     article_snippet = get_snippet(article_url)
    #     # Encode the snippet in utf-8
    #     encoded_snippet = article_snippet.encode('utf-8')
    #     # results.at[index, 'snippet'] = article_snippet
    #     results.loc[index, 'snippet'] = article_snippet
    except Exception as e:
        print(f"Error retrieving snippet for {article_url}: {e}, trying wayback machine url...")
        try:
            article_url = article['article_url']
            article_snippet = get_snippet(article_url)
            sanitized_snippet = sanitize_snippet(article_snippet)
            # Encode the snippet in utf-8
            # encoded_snippet = sanitized_snippet.encode('utf-8')
            # results.at[index, 'snippet'] = article_snippet
            results.loc[index, 'snippet'] = sanitized_snippet
        except Exception as e:
            print(f"Error retrieving snippet for {article_url}: {e}")
            results.loc[index, 'snippet'] = None
        
        

# results.drop_duplicates(subset=['title'], keep='first', inplace=True)

results.to_csv('./data_storage/results_df_with_snippets.csv', index=False)
print("Data retrieval complete. Results saved to 'data_storage/results_df_with_snippets.csv'.")

