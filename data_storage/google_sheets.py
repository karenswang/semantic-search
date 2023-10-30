from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
import os

class GoogleSheetsStorage:
    def __init__(self, json_keyfile_path):
        self.SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        self.credentials = Credentials.from_service_account_file(json_keyfile_path, scopes=self.SCOPES)
        self.service = build('sheets', 'v4', credentials=self.credentials)

    def append_data(self, spreadsheet_id, range_name, values):
        """
        Append data to a Google Sheet.

        :param spreadsheet_id: ID of the Google Sheets document
        :param range_name: The range of cells to write the data in A1 notation
        :param values: Data to be written to Google Sheets
        """
        body = {'values': values}

        result = self.service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='RAW',
            body=body
        ).execute()

        print('{0} cells appended.'.format(result.get('updates').get('updatedCells')))
