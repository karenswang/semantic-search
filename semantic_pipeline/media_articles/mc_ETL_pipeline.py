from waybacknews.searchapi import SearchApiClient
from datetime import datetime
import pandas as pd
import requests_cache
from tqdm import tqdm
# import mediacloud.api
# from newspaper import Article
# import unicodedata
import concurrent.futures
from utils.utils import split_into_chunks, fetch_snippet, sanitize_snippet, get_snippet_from_wayback_machine
from sentence_transformers import SentenceTransformer
from InstructorEmbedding import INSTRUCTOR
from openai import OpenAI

import weaviate
import json
import os
from dotenv import load_dotenv


load_dotenv()
timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

weaviate_api_key = os.getenv('WEAVIATE_API_KEY')
weaviate_url = os.getenv('WEAVIATE_URL')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

client = weaviate.Client(
    url = weaviate_url,
    auth_client_secret=weaviate.AuthApiKey(api_key=weaviate_api_key), 
    additional_headers = {
        "X-OpenAI-Api-Key": OPENAI_API_KEY
    }
)

openai_client = OpenAI()

# ----------------- Media Cloud Data Retrieval -----------------
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
query_term = '("police shooting" OR "shot by police" OR "police shot" OR "officer-involved shooting" OR "police-involved shooting" OR "police officer shooting" OR "officer shot" OR "deputy shot" OR "sheriff shot" OR "cop shot" OR "trooper shot" OR "shot by officer" OR "shot by deputy" OR "shot by sheriff" OR "shot by cop" OR "shot by trooper" OR \
    # "killed by police" OR "killed by officer" OR "killed by deputy" OR "killed by sheriff" OR "killed by cop" OR "killed by trooper")'

# query_term = '("gender" AND "hate crime")'
start = datetime(2023, 12, 1) 
end = datetime(2023, 12, 15) 
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

combined_results.to_csv(f'./data_storage/{timestamp}_no_snippet.csv', index=False)

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
combined_results.to_csv(f'./data_storage/{start}.csv', index=False)
print(f"Data retrieval complete. Results saved to './data_storage/{start}.csv'.")

# ----------------- Vectorize the snippets -----------------
# use this line and uncomment above if importing existing web search results
combined_results = pd.read_csv('./data_storage/benchmark/web_search_results_benchmark.csv')

# pre-vectorize the snippet to avoid using huggingface API which costs money
# embed_model = SentenceTransformer('sentence-transformers/msmarco-MiniLM-L12-cos-v5')
# embed_model = SentenceTransformer("nomic-ai/nomic-embed-text-v1")
embed_model = INSTRUCTOR('hkunlp/instructor-large')
instruction = "Represent the news articles about police-involved fatal shooting for question answering:"

print("Max Sequence Length:", embed_model.max_seq_length)
embed_model.max_seq_length = 512



combined_results['snippet_vector'] = None

for index, row in tqdm(combined_results.iterrows(), total=combined_results.shape[0]):
    snippet = row['snippet']
    # snippet_vector = embed_model.encode(snippet).tolist()  
#     if snippet.__len__() > 8190:
#         snippet = snippet[:8190]
#     response = openai_client.embeddings.create(
#     input=snippet,
#     model="text-embedding-3-small"
# )
#     snippet_vector = response.data[0].embedding 
    snippet_vector = embed_model.encode([[instruction,snippet]]).tolist()
    snippet_vector = [item for sublist in snippet_vector for item in sublist]

    # Store embeddings in DataFrame
    combined_results.at[index, 'snippet_vector'] = snippet_vector

print(combined_results.shape)

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


# load pre-vectorized data
client.batch.configure(batch_size=100)
with client.batch as batch:
    for index, row in (combined_results.iterrows()):
        properties = {
            "title": row['title'],
            "publication_date": row['publication_date'],
            "snippet": row['snippet']
        }
        batch.add_data_object(properties, "Article", vector=row["snippet_vector"])


# ----------------- Query Weaviate -----------------
# graphql (allows to group/merge similar results)
# query_text = "Find articles about police shooting that resulted in death of the victims. The incident is about police officer,deputy, sheriff, trooper, cop who fatally fired shots and killed someone. The victims are dead."
query_text = """
Breaking news coverage on recent police shooting incidents in the United States leading to fatalities of the victims. The incidents are about police officer, deputy, sheriff, trooper, cop who fired shots and killed someone.
Do not include aggregated summary, list, or archive of incidents happened in the past. Do not include if it's about a past, not recent incident. Only include if the story mentioned the death of the victim.
Do not include if it's coverage on new evidence or recent legal proceedings, court cases, or trials of a past incident. Do not include if it's about the aftermath of the incident, such as protests, rallies, or demonstrations on a past incident.
Do not include if it happened in a foreign country, only include if it's about the United States. 
"""
# filter for US only
instruction_prompt = "Represent the news articles for retrieval:"

# # Using the text-embedding-3-large model to generate embeddings
# response = openai_client.embeddings.create(
#     input=query_text,
#     model="text-embedding-3-small"
# )
# query_vector = response.data[0].embedding

# query_model = SentenceTransformer("nomic-ai/nomic-embed-text-v1.5", trust_remote_code=True)
# query_vector = query_model.encode(query_text).tolist()

query_vector = embed_model.encode([[instruction_prompt,query_text]]).tolist()
query_vector = [item for sublist in query_vector for item in sublist]
print("vector:", query_vector.__len__())

get_articles_group = f"""
{{
  Get {{
    Article(
      nearVector: {{
        vector: {query_vector}
      }},
      group: {{
        type: merge,
        force: 0
      }},
      limit: 80
    ) {{
      title,
      publication_date,
      snippet
    }}
  }}
}}
"""


query_result = client.query.raw(get_articles_group)
# save to csv
df = pd.DataFrame(query_result['data']['Get']['Article'])
df.to_csv(f'./data_storage/{timestamp}_test_weaviate_result.csv', index=False)