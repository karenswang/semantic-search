from waybacknews.searchapi import SearchApiClient
from datetime import datetime
import pandas as pd
import requests
from retrying import retry
import requests_cache
from tqdm import tqdm
# import mediacloud.api
from newspaper import Article
# import unicodedata
import concurrent.futures
from utils.utils import split_into_chunks, fetch_snippet, sanitize_snippet, get_snippet_from_wayback_machine
from sentence_transformers import SentenceTransformer

import weaviate
import json
import os


# set up weaviate client
OPENAI_APIKEY = os.environ['OPENAI_API_KEY']
client = weaviate.Client(
    url = "https://semantic-search-cluster-mp9jmm6o.weaviate.network",  # Replace with your endpoint
    auth_client_secret=weaviate.AuthApiKey(api_key="kEzuSpJyK8J7IDLLsmzoBlH8mOtkrfkCjIH6"),  # Replace w/ your Weaviate instance API key
    additional_headers = {
        "X-OpenAI-Api-Key": OPENAI_APIKEY
    }
)

if client.schema.exists("Article"):
    client.schema.delete_class("Article")
    
# for pre-vectorized data
class_obj = {
    "class": "Article",
    "vectorizer": "none",
    "moduleConfig": {
        "generative-openai": {}  # Ensure the `generative-openai` module is used for generative queries
    }
}

client.schema.create_class(class_obj)

import mediacloud.api
collection_id = "38379429"
api = SearchApiClient("mediacloud")

SOURCES_PER_PAGE = 100  # the number of sources retrieved per page
mc_directory = mediacloud.api.DirectoryApi('e85cce24da8b73eaa05329d258146c044ef055db')
sources = []
offset = 0   # offset for paging through
while True:
    # grab a page of sources in the collection
    response = mc_directory.source_list(collection_id=collection_id, limit=SOURCES_PER_PAGE, offset=offset)
    # add it to our running list of all the sources in the collection
    sources += response['results']
    # if there is no next page then we're done so bail out
    if response['next'] is None:
        break
    # otherwise setup to fetch the next page of sources
    offset += len(response['results'])
print("Collection has {} sources".format(len(sources)))
all_domains = [s['name'] for s in sources]

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
# domains_df.to_csv('domains.csv', index=False)

domain_chunks = list(split_into_chunks(cleaned_domains, 1000))

# Enable requests cache
requests_cache.install_cache('article_cache', backend='filesystem', expire_after=3600)


# Query parameters
# query_term = '("police shooting" OR "shot by police" OR "police shot" OR "officer-involved shooting" OR "police-involved shooting" OR "police officer shooting" OR "police shot" OR "officer shot")'
query_term = '("police shooting" OR "shot by police" OR "police shot" OR "officer-involved shooting" OR "police-involved shooting" OR "police officer shooting" OR "officer shot" OR "deputy shot" OR "sheriff shot" OR "cop shot" OR "trooper shot" OR "shot by officer" OR "shot by deputy" OR "shot by sheriff" OR "shot by cop" OR "shot by trooper" OR \
    "killed by police" OR "killed by officer" OR "killed by deputy" OR "killed by sheriff" OR "killed by cop" OR "killed by trooper")'

# query_term = 'police AND shot'
start = datetime(2023, 7, 1) #11/6 - 11/15
end = datetime(2023, 7, 15) 
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
timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
combined_results.to_csv(f'../data_storage/{timestamp}_no_snippet.csv', index=False)

for index, article in tqdm(combined_results.iterrows(), total=combined_results.shape[0]):
    # only use wayback machine
    wayback_url = article['article_url']
    snippet = get_snippet_from_wayback_machine(wayback_url)
    if snippet:
        sanitized_snippet = sanitize_snippet(snippet)
        combined_results.loc[index, 'snippet'] = sanitized_snippet

# print(combined_results.shape)
combined_results.dropna(subset=['snippet'], inplace=True)
print("after dropping null snippets: ", combined_results.shape)
combined_results.reset_index(drop=True, inplace=True)
combined_results.to_csv(f'../data_storage/{timestamp}.csv', index=False)
print(f"Data retrieval complete. Results saved to '../data_storage/{timestamp}.csv'.")


# pre-vectorize the snippet to avoid using huggingface API which costs money
model = SentenceTransformer('all-MiniLM-L6-v2')
print("Max Sequence Length:", model.max_seq_length)
model.max_seq_length = 512

combined_results['snippet_vector'] = None

for index, row in tqdm(combined_results.iterrows(), total=combined_results.shape[0]):
    snippet = row['snippet']
    snippet_vector = model.encode(snippet).tolist()

    # Store embeddings in DataFrame
    combined_results.at[index, 'snippet_vector'] = snippet_vector

print(combined_results.shape)

# for pre-vectorized data
client.batch.configure(batch_size=100)
with client.batch as batch:
    for index, row in (combined_results.iterrows()):
        properties = {
            "title": row['title'],
            "publication_date": row['publication_date'],
            "snippet": row['snippet']
        }
        batch.add_data_object(properties, "Article", vector=row["snippet_vector"])


# graphql (allows to group/merge similar results)
query_text = "Find articles about police shooting that resulted in death of the victims. The incident is about police officer,deputy, sheriff, trooper, cop who fatally fired shots and killed someone. The victims are dead."

query_vector = model.encode(query_text).tolist()

get_articles_group = f"""
{{
  Get {{
    Article(
      nearVector: {{
        vector: {query_vector}
      }},
      group: {{
        type: merge,
        force: 0.15
      }},
      limit: 100
    ) {{
      title,
      publication_date,
      snippet,
      _additional {{
        generate(
          singleResult: {{
            prompt: \"\"\"Summarize the article: '{'{{snippet}}'}' in one sentence.\"\"\"
          }}
        ) {{
          singleResult,
          error
        }}
      }}
    }}
  }}
}}
"""


query_result = client.query.raw(get_articles_group)
# save to csv
df = pd.DataFrame(query_result['data']['Get']['Article'])
df.to_csv(f'../data_storage/test_weaviate_result.csv', index=False)