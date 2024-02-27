import pandas as pd
from datetime import datetime, timedelta

def find_matching_records(csv1_path, csv2_path, start_date, end_date):
    # Load the CSV files
    csv1 = pd.read_csv(csv1_path)
    csv2 = pd.read_csv(csv2_path)

    # Convert date columns to datetime for easy comparison
    csv2['date'] = pd.to_datetime(csv2['date'])
    csv1['publication_date'] = pd.to_datetime(csv1['publication_date'], errors='coerce')

    # Filter records in CSV 2 within the date range
    filtered_csv2 = csv2[(csv2['date'] >= start_date) & (csv2['date'] <= end_date)]

    # Initialize list to store matching records
    matching_records = []

    # Iterate over filtered records in CSV 2
    for _, row in filtered_csv2.iterrows():
        # Extract keywords for searching
        keywords = [str(row['city']), str(row['county']), str(row['name'])]

        # Filter CSV 1 records where snippet or title contains any of the keywords
        for keyword in keywords:
            matches = csv1[(csv1['snippet'].str.contains(keyword, case=False, na=False)) | 
                           (csv1['title'].str.contains(keyword, case=False, na=False))]

            # Further filter matches based on publication_date criteria
            valid_matches = matches[(matches['publication_date'] >= row['date']) & 
                                    (matches['publication_date'] <= row['date'] + timedelta(days=10))]

            # Append valid matches to the list
            for _, match in valid_matches.iterrows():
                match_record = match.to_dict()
                match_record['csv2_id'] = row['id']  # Add id from CSV 2 for reference
                matching_records.append(match_record)

    # Convert the list of matching records to a DataFrame
    matching_df = pd.DataFrame(matching_records)

    # Save the DataFrame to a new CSV file
    output_csv_path = 'matching_records.csv'
    matching_df.to_csv(output_csv_path, index=False)

    return len(matching_records), output_csv_path

# Usage example
csv1_path = 'path_to_csv1.csv'  # Replace with your actual file path
csv2_path = 'path_to_csv2.csv'  # Replace with your actual file path
start_date = '2023-12-01'
end_date = '2023-12-15'

num_matches, output_csv = find_matching_records(csv1_path, csv2_path, start_date, end_date)
print(f"Number of matches found: {num_matches}")
print(f"Output CSV file: {output_csv}")
