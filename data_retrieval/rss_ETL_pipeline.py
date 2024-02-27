import feedparser
import pandas as pd
from datetime import datetime
import pandas as pd
from tqdm import tqdm
from sentence_transformers import SentenceTransformer

import weaviate
import json
import os
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()

OPENAI_APIKEY = os.getenv('OPENAI_API_KEY')
client = weaviate.Client(
    url = "https://semantic-search-bfasidnu.weaviate.network",
    auth_client_secret=weaviate.AuthApiKey(api_key="xoXo297Sh8pBywKsSkiQVNsr8L33w4YI7dC7"), 
    additional_headers = {
        "X-OpenAI-Api-Key": OPENAI_APIKEY
    }
)

if client.schema.exists("Legislation"):
    client.schema.delete_class("Legislation")
    
# for pre-vectorized data
class_obj = {
    "class": "Legislation",
    "vectorizer": "none",
    "moduleConfig": {
        "generative-openai": {}  # Ensure the `generative-openai` module is used for generative queries
    }
}

client.schema.create_class(class_obj)




# URL of the RSS feed
rss_url = 'https://www.legis.iowa.gov/subscribe/rss/feeds/IowaBills.xml'

# Parse the RSS feed
feed = feedparser.parse(rss_url)

# Initialize an empty list to store the data
data = []

# Loop through the entries and extract information
for entry in feed.entries:
    title = entry.title
    link = entry.link
    description = entry.description
    pub_date = entry.published
    
    # Append the extracted information to the data list
    data.append({
        'Title': title,
        'Link': link,
        'Description': description,
        'Publication Date': pub_date
    })

# Convert the list of dictionaries into a pandas DataFrame
legislature = pd.DataFrame(data)



# pre-vectorize the snippet to avoid using huggingface API which costs money
model = SentenceTransformer('sentence-transformers/msmarco-MiniLM-L6-cos-v5')
print("Max Sequence Length:", model.max_seq_length)
model.max_seq_length = 512

legislature['text_vector'] = None

for index, row in tqdm(legislature.iterrows(), total=legislature.shape[0]):
    text = row['Description']
    text_vector = model.encode(text).tolist()

    # Store embeddings in DataFrame
    legislature.at[index, 'text_vector'] = text_vector

print(legislature.shape)

# for pre-vectorized data
client.batch.configure(batch_size=100)
with client.batch as batch:
    for index, row in (legislature.iterrows()):
        properties = {
            "title": row['Title'],
            "publication_date": row['Publication Date'],
            "description": row['Description']
        }
        batch.add_data_object(properties, "Legislation", vector=row["text_vector"])


# graphql (allows to group/merge similar results)
# query_text = "Find articles about police shooting that resulted in death of the victims. The incident is about police officer,deputy, sheriff, trooper, cop who fatally fired shots and killed someone. The victims are dead."
# query_text = "Recent police shooting incidents leading to fatalities of the victims. The incidents are about police officer, deputy, sheriff, trooper, cop who fatally fired shots and killed someone."
query_text = "Find topic relating to gender identity, LGBTQ+ groups, trans, nonbinary, gender-nonconforming, genderqueer, genderfluid."

query_vector = model.encode(query_text).tolist()

get_legislation_group = f"""
{{
  Get {{
    Legislation(
      nearVector: {{
        vector: {query_vector}
      }},
      group: {{
        type: merge,
        force: 0.15
      }},
      limit: 10
    ) {{
      title,
      publication_date,
      description,
      _additional {{
        generate(
          singleResult: {{
            prompt: \"\"\"Summarize the legislation: '{'{{description}}'}' in one sentence.\"\"\"
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


query_result = client.query.raw(get_legislation_group)
# save to csv
df = pd.DataFrame(query_result['data']['Get']['Legislation'])
timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
df.to_csv(f'./data_storage/{timestamp}_legislation_weaviate_result.csv', index=False)