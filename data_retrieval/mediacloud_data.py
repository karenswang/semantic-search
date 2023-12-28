from waybacknews.searchapi import SearchApiClient
from datetime import datetime
import pandas as pd
import requests
from retrying import retry
import requests_cache
from tqdm import tqdm
import mediacloud.api
from newspaper import Article
# import unicodedata
import concurrent.futures
from utils.utils import split_into_chunks, fetch_snippet, sanitize_snippet, get_snippet_from_wayback_machine

# get news domains
collection_id = "38379429"
directory_api = mediacloud.api.DirectoryApi(auth_token='e85cce24da8b73eaa05329d258146c044ef055db')
api = SearchApiClient("mediacloud")

all_domains = []
# Pagination setup
offset = 0
limit = 100  # seems to have a 100 limit
more_pages = True

while more_pages:
    # Fetch sources with current offset
    sources_response = directory_api.source_list(collection_id=collection_id, limit=limit, offset=offset)
    sources = sources_response.get('results', [])
    domains = [source['homepage'] for source in sources]
    all_domains.extend(domains)
    
    # Update the offset
    offset += limit
    
    # Check if there are more pages to fetch
    more_pages = len(sources) == limit

# Cleaning up domains
cleaned_domains = [
    domain.replace('https://www.', '')
          .replace('http://www.', '')
          .replace('https://', '')
          .replace('http://', '')
          .replace('#spider', '')
          .replace('/#spider', '')
          .rstrip('/')
    for domain in all_domains
    if domain  # Ensure the domain is not None or empty
]
print(f"Number of sources: {len(cleaned_domains)}")
domains_df = pd.DataFrame(cleaned_domains, columns=['Domain'])
# Save the DataFrame to a CSV file
domains_df.to_csv('domains.csv', index=False)

domain_chunks = list(split_into_chunks(cleaned_domains, 1000))

# sources_response = directory_api.source_list(collection_id=collection_id)
# domains = [source['homepage'] for source in sources_response['results']]
# num_sources = len(sources_response['results'])
# print(f"Number of sources: {num_sources}")

# cleaned_domains = [domain.replace('https://www.', '').replace('http://www.', '').replace('https://','').replace('http://','') for domain in domains]
# cleaned_domains = [url.rstrip('/') for url in cleaned_domains]
# print(cleaned_domains)

# Enable requests cache
requests_cache.install_cache('article_cache', backend='filesystem', expire_after=3600)


# Query parameters
# query_term = '("police shooting" OR "shot by police" OR "police shot" OR "officer-involved shooting" OR "police-involved shooting" OR "police officer shooting" OR "police shot" OR "officer shot")'
query_term = '("police shooting" OR "shot by police" OR "police shot" OR "officer-involved shooting" OR "police-involved shooting" OR "police officer shooting" OR "officer shot" OR "deputy shot" OR "sheriff shot" OR "cop shot" OR "trooper shot" OR "shot by officer" OR "shot by deputy" OR "shot by sheriff" OR "shot by cop" OR "shot by trooper" OR \
    "killed by police" OR "killed by officer" OR "killed by deputy" OR "killed by sheriff" OR "killed by cop" OR "killed by trooper")'

# query_term = 'police AND shot'
start = datetime(2023, 9, 1) #11/6 - 11/15
end = datetime(2023, 10, 1) 
language = "en"

# DataFrame to store combined results
combined_results = pd.DataFrame()
results_list = []

for chunk in domain_chunks:
    domains_str = f"domain:({' OR '.join(chunk)})"
    query = f"{query_term} AND language:{language} AND {domains_str}"
    
    # Perform the search with the current chunk
    articles = []
    for list_of_articles in api.all_articles(query, start, end):
        articles.extend(list_of_articles)
        print(f"Found {len(articles)} articles")
    
    if articles:
        chunk_results = pd.DataFrame(articles)
        results_list.append(chunk_results)
    

# Concatenate all DataFrames in the list
combined_results = pd.concat(results_list, ignore_index=True)
# results = pd.DataFrame(articles).sort_values(by='publication_date', ascending=False)
combined_results.sort_values(by='publication_date', ascending=False, inplace=True)
print(combined_results.shape)
combined_results.drop_duplicates(subset=['title'], keep='first', inplace=True)
print("after dropping duplicates: ", combined_results.shape)
combined_results.to_csv(f'./data_storage/{start}_no_snippet.csv', index=False)


for index, article in tqdm(combined_results.iterrows(), total=combined_results.shape[0]):
    # only use wayback machine
    wayback_url = article['article_url']
    snippet = get_snippet_from_wayback_machine(wayback_url)
    if snippet:
        sanitized_snippet = sanitize_snippet(snippet)
        combined_results.loc[index, 'snippet'] = sanitized_snippet
        
    # or concurrently run mediacloud wayback machine and newspaper3k
    # article_url = article['url']
    # wayback_url = article['article_url']
    # snippet, method_used = fetch_snippet(article_url, wayback_url)
    # if snippet:
    #     sanitized_snippet = sanitize_snippet(snippet)
    #     combined_results.loc[index, 'snippet'] = sanitized_snippet
    #     # print(f"Snippet fetched using {method_used} method for URL: {article_url}")

print(combined_results.shape)
combined_results.dropna(subset=['snippet'], inplace=True)
print("after dropping null snippets: ", combined_results.shape)
combined_results.to_csv(f'./data_storage/{start}.csv', index=False)
print(f"Data retrieval complete. Results saved to './data_storage/{start}.csv'.")

