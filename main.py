import os
from dotenv import load_dotenv
# from use_cases.ai_policy import AIPoliciesSearch
from use_cases.police_shootings import PoliceShootingsPoliciesSearch

# Load environment variables
load_dotenv()

def main():
    # Path to service account key file (from Google Cloud Console)
    SERVICE_ACCOUNT_FILE = './data_storage/semantic-search-1697418273136-1630a5c96bc7.json' # see google_service account in repo secret
    
    # SPREADSHEET_ID = '1qWjTUjCMFU_K31xGZqPwNMZQg_HVRsmQq15_2pvvjMA'  # AI policy
    SPREADSHEET_ID = '1I4nbVVCLLNJXTOqElUOpAlJs1zkNTkZ0A9mtknF6YoA' # mass shootings

    # Initialize the AIPoliciesSearch use case
    # ai_policies_search = AIPoliciesSearch(
    #     json_keyfile_path=SERVICE_ACCOUNT_FILE,
    #     spreadsheet_id=SPREADSHEET_ID
    # )
    police_shootings_policies_search = PoliceShootingsPoliciesSearch(
        json_keyfile_path=SERVICE_ACCOUNT_FILE,
        spreadsheet_id=SPREADSHEET_ID
    )

    # Execute the search and save results operation
    # ai_policies_search.execute()
    police_shootings_policies_search.execute()


if __name__ == '__main__':
    main()
