from googleapiclient.discovery import build
from dotenv import load_dotenv
import os

load_dotenv()
google_api_key = os.getenv('google_api_key')
google_engine_id = os.getenv('google_engine_id')

# retrieve the top-10 results for the query from Google
query = "Newsroom OR journalist AND \"AI policy\""
date_restrict = "w"  # d/w/m/y
service = build(
    "customsearch", "v1", developerKey=google_api_key
)
# res is a Python object built from the JSON response sent by the API server
res = (
    service.cse()
    .list(
        q=query,
        cx=google_engine_id,
        dateRestrict=date_restrict,
    )
    .execute()
)

print(res) # need to parse it here