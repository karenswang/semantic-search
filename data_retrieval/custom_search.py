from googleapiclient.discovery import build
from dotenv import load_dotenv
import os
from google.oauth2.service_account import Credentials

load_dotenv()
google_api_key = os.getenv('google_api_key')
google_engine_id = os.getenv('google_engine_id')

# retrieve the top-10 results for the query from Google
query = "Newsroom OR journalist AND \"AI policy\""
date_restrict = "d"  # d/w/m/y
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

# # terminate if less than 10 results
# if len(res['items']) < 10:
#     print("Less than 10 results returned. Exiting...")
#     exit()

# save the title, snippet and url of each of the top-10 results in a csv
# for message in res['items']:
    # print(message['title'])
    # print(message['snippet'])
    # print(message['link'])
    # print()


# Prepare your data for Sheets (the rows of the spreadsheet)
values = [
    ["Title", "Snippet", "URL"]  # Headers or column names
] + [
    [item['title'], item['snippet'], item['link']]  # Data rows
    for item in res['items']
]


# Set up the Sheets API connection
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = './google-sheets-keys/semantic-search-1697418273136-21da8a05218e.json'  # Replace with the path to your downloaded JSON file

credentials = Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)

service_sheets = build('sheets', 'v4', credentials=credentials)

SPREADSHEET_ID = '1qWjTUjCMFU_K31xGZqPwNMZQg_HVRsmQq15_2pvvjMA'  # Get this from the URL of your Google Sheets document
sheet_range = 'Sheet1!A1'  # This points to the top-left cell of your Sheet, adjust as needed

# Prepare the data structure for the request body
body = {
    'values': values
}

# Use the Sheets API to append the data
sheet = service_sheets.spreadsheets()
result = sheet.values().append(
    spreadsheetId=SPREADSHEET_ID,
    range=sheet_range,
    valueInputOption='RAW',
    body=body
).execute()

print('{0} cells appended.'.format(result \
                                   .get('updates') \
                                   .get('updatedCells')))




