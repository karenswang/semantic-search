from datetime import datetime
import pandas as pd
import requests
from tqdm import tqdm
# import unicodedata
from sentence_transformers import SentenceTransformer
from InstructorEmbedding import INSTRUCTOR

import weaviate
import json
import os
from dotenv import load_dotenv


load_dotenv()
timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
weaviate_api_key = os.getenv('WEAVIATE_API_KEY')
weaviate_url = os.getenv('WEAVIATE_URL')
openai_key = os.getenv('OPENAI_API_KEY')
billtrack50_api_key = os.getenv('bill_tracker_api_key')

client = weaviate.Client(
    url = weaviate_url,
    auth_client_secret=weaviate.AuthApiKey(api_key=weaviate_api_key), 
    additional_headers = {
        "X-OpenAI-Api-Key": openai_key
    }
)


state = "NY"
# # Configuration for API requests
# api_url = "https://www.billtrack50.com/bt50api/2.1/json/bills"
# params = {
#     "searchText": "gender",
#     "stateCodes": state
# }
# headers = {
#     "Authorization": f"apiKey {billtrack50_api_key}"
# }

# # Initialize DataFrame to store combined data
# combined_results = pd.DataFrame()

# # Implement pagination
# current_page = 1
# total_pages = None  # We'll update this based on the API responses

# while total_pages is None or current_page <= total_pages:
#     print(f"Fetching data for page {current_page}...")
#     response = requests.get(api_url, headers=headers, params={**params, "page": current_page})
#     if response.status_code == 200:
#         data = response.json()
#         if total_pages is None:
#             # Assuming the API provides total pages directly
#             total_pages = data.get('totalPages', 1)
#         bills = data['bills']
#         combined_results = pd.concat([combined_results, pd.DataFrame(bills)], ignore_index=True)
#         current_page += 1
#     else:
#         print(f"Failed to fetch data for page {current_page}. Status Code: {response.status_code}")
#         break

# print("Shape of result dataframe:", combined_results.shape)
# print(combined_results.head())
# combined_results.to_csv(f'./data_storage/legislation/{state}_billtrack50_results.csv', index=False)
combined_results = pd.read_csv(f'./data_storage/legislation/{state}_billtrack50_results.csv')



#------------------ vectorization ------------------
# pre-vectorize the snippet to avoid using huggingface API which costs money
model = SentenceTransformer('sentence-transformers/msmarco-MiniLM-L12-cos-v5')
# model = INSTRUCTOR('hkunlp/instructor-large')
# instruction = "Represent the legislation bills for retrieval:"

print("Max Sequence Length:", model.max_seq_length)
model.max_seq_length = 512



# Adjusted to vectorize only specific fields as requested
combined_results['billName_vector'] = None
combined_results['summary_vector'] = None
combined_results['keyWords_vector'] = None

# Assuming you have initialized the model as in the original script
for index, row in tqdm(combined_results.iterrows(), total=combined_results.shape[0]):
    # Vectorize the specified fields
    for field in ['billName', 'summary', 'keyWords']:
        field_value = row[field]
        vector = model.encode(field_value).tolist()
        # vector = model.encode([[instruction, field_value]]).tolist()
        # vector = [item for sublist in vector for item in sublist]
        combined_results.at[index, f'{field}_vector'] = vector

print(combined_results.shape)

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


# for pre-vectorized data        
client.batch.configure(batch_size=100)
with client.batch as batch:
    for index, row in combined_results.iterrows():
        properties = {
            "billID": row['billID'],
            "stateBillID": row['stateBillID'],
            "stateCode": row['stateCode'],            
            "billName": row['billName'],
            "summary": row['summary'],
            "sponsorCount": row['sponsorCount'],
            "sponsors": row['sponsors'],
            "subjects": row['subjects'],
            "keyWords": row['keyWords'],
            "actions": row['actions'],	
            "lastAction": row['lastAction'],
            "actionDate": row['actionDate'],
            "votes": row['votes'],
            "billProgress": row['billProgress'],	
            "officialDocument": row['officialDocument'],
            "created": row['created']   
        }
        # concatenated_vector = row['billName_vector'] + row['summary_vector'] + row['keyWords_vector']

        # Adjust the property names and structure according to your schema requirements
        batch.add_data_object(properties, "Legislation", vector=row['summary_vector'])


query_text = """
Find bills relating to gender identity, LGBTQ+ groups, trans, nonbinary, gender-nonconforming, genderqueer, genderfluid. Also include bills that could have a bigger impact on these groups than others.
This could include but not limited to topics on : Sex reassignment, gender reassignment, Biological sex, Natural sex hormones, Sex organs etc.

"""
instruction_prompt = "Represent the legislation bill for retrieval:"

negative_text = "A list of, archive"
# query_text = "Find recent hate crime incidents targeting gender or gender identity of the victims."

query_vector = model.encode(query_text).tolist()
# query_vector = model.encode([[instruction_prompt,query_text]]).tolist()
# query_vector = [item for sublist in query_vector for item in sublist]

get_legislation_group = f"""
{{
  Get {{
    Legislation(
      nearVector: {{
        vector: {query_vector}
      }},
      group: {{
        type: merge,
        force: 0
      }},
      limit: 80
    ) {{
      billID,
        stateBillID,
        stateCode,
        billName,
        summary,
        sponsorCount,
        sponsors,
        subjects,
        keyWords,
        actions,
        lastAction,
        actionDate,
        votes,
        billProgress,
        officialDocument,
        created,
    }}
  }}
}}
"""


query_result = client.query.raw(get_legislation_group)
print(query_result)
# save to csv
df = pd.DataFrame(query_result['data']['Get']['Legislation'])
df.to_csv(f'./data_storage/{state}_test_weaviate_result.csv', index=False)