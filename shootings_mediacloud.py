import mediacloud.api

# # api = mediacloud.api.BaseApi(auth_token='e85cce24da8b73eaa05329d258146c044ef055db')

# directory_api = mediacloud.api.DirectoryApi(auth_token='e85cce24da8b73eaa05329d258146c044ef055db')
# collections = directory_api.collection_list(platform=mediacloud.api.DirectoryApi.PLATFORM_ONLINE_NEWS)
# print(collections)

import requests
import json

api_key = 'e85cce24da8b73eaa05329d258146c044ef055db'  # replace with your actual API key
base_url = 'https://search.mediacloud.org/api/'  # this might be different for the actual MediaCloud API


def fetch_stories(api, keywords, collection_id):
    all_stories = []
    page = 0
    page_size = 100  # number of stories to fetch per request, adjust based on the API's limits

    while True:
        # Construct the URL for searching stories. This may vary depending on the actual API's structure.
        url = f"{base_url}stories_public/list"

        # Prepare the query parameters. This might include pagination parameters and your search query.
        params = {
            'q': keywords,  # your search query
            'fq': f"collections_id:{collection_id}",  # Filter query to specific collection
            'page': page,
            'page_size': page_size,
        }

        # Include your API key in the header
        headers = {
            'Authorization': f'Token {api_key}',
        }

        # Make the HTTP request
        response = requests.get(url, params=params, headers=headers, allow_redirects=False)


        if response.status_code == 200:
            try:
                # Attempt to decode the JSON
                data = response.json()
                # ... (handle your data)
            except json.JSONDecodeError:
                # The JSON is invalid, print the response or log an error message
                print(f"Invalid JSON response received: {response.text}")
        else:
            # The server didn't respond with a 200 status, handle the error
            print(f"Unsuccessful request. Status code: {response.status_code} Response: {response.text}")

            print(response.text)
            break

    return all_stories

# Usage
api = mediacloud.api.BaseApi(auth_token=api_key)  # Initialize your API client
collection_id = "38379429"
keywords = 'shooting OR shooter'  # using OR to search for stories with either keyword
stories = fetch_stories(api, keywords, collection_id)

print(stories.head())
