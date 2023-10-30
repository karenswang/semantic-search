import mediacloud.api

collection_name = "United States - State & Local"

api = mediacloud.api.BaseApi(auth_token='e85cce24da8b73eaa05329d258146c044ef055db')
collections = api.collection_list()
for collection in collections:
    if collection['name'] == collection_name:
        return collection['id']

directory_api = mediacloud.api.DirectoryApi(auth_token='e85cce24da8b73eaa05329d258146c044ef055db')
collections = directory_api.collection_list(platform=mediacloud.api.DirectoryApi.PLATFORM_ONLINE_NEWS)
print(collections)