import openai
import pandas as pd
import os

openai.api_key = os.getenv('openai_key')

df = pd.read_csv('data_storage/results_df_with_snippets.csv')

def classify_snippet(snippet, prompt):
    if len(snippet) > 7000:  # keep context window and tokens used limited
        snippet = snippet[:7000]  
    response = openai.completions.create(
      model="davinci",  
      prompt=f"{prompt}\n\n{snippet}\n\nIs this article about a fatal police shooting? (Y/N): ",
      max_tokens=1  # limit to 1 token to force a binary response
    )
    answer = response.choices[0].text.strip().lower()
    return 'Y' if 'yes' in answer else 'N'

# Classify each snippet
for index, row in df.iterrows():
    df.at[index, 'is_fatal_police_shooting'] = classify_snippet(row['snippet'], "Based on the snippet, help me identify if the article is about a fatal police shooting. The strict requirements are: fatal, police-involved, shooting.")

df.to_csv('data_storage/classified_results.csv', index=False)
