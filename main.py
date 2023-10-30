import os
from dotenv import load_dotenv
from use_cases.ai_policy import AIPoliciesSearch

# Load environment variables
load_dotenv()

def main():
    # Path to service account key file (from Google Cloud Console)
    SERVICE_ACCOUNT_FILE = './data_storage/semantic-search-1697418273136-1630a5c96bc7.json'
    
    SPREADSHEET_ID = '1qWjTUjCMFU_K31xGZqPwNMZQg_HVRsmQq15_2pvvjMA'  

    # Initialize the AIPoliciesSearch use case
    ai_policies_search = AIPoliciesSearch(
        json_keyfile_path=SERVICE_ACCOUNT_FILE,
        spreadsheet_id=SPREADSHEET_ID
    )

    # Execute the search and save results operation
    ai_policies_search.execute()

# This is the standard boilerplate that calls the main() function.
if __name__ == '__main__':
    main()
