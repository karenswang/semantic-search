import openai
import pandas as pd
import os

from openai import OpenAI

openai.api_key = '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'
client = OpenAI(
  api_key=openai.api_key,
)

df = pd.read_csv('data_storage/results_df_with_snippets.csv')

if 'is_fatal_police_shooting' not in df.columns:
    df['is_fatal_police_shooting'] = None
# if 'not_duplicate?' not in df.columns:
#     df['not_duplicate?'] = None

#TODO add request cache

def classify_snippet(snippet, model):
    if len(snippet) > 7000:  # keep context window and tokens used limited
        snippet = snippet[:7000] 
    # if model == 'davinci': 
    #     response = openai.completions.create(
    #     model=model,  
    #     prompt=f"{prompt}\n\n{snippet}\n\nIs this article about a fatal police shooting? (Y/N): ",
    #     max_tokens=1  # limit to 1 token to force a binary response
    #     )
    #     answer = response.choices[0].text
        # pass
    if model == 'gpt-3.5-turbo':
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a researcher skilled in reading news articles to identify the ones about fatal police shooting incidents."},
                # {"role": "user", "content": f"Based on the news snippet, help me identify if the article is about a fatal police shooting. The incident has to be about police officer fired shots and killed someone. The victims should be dead. Return Y or N. Snippet: {snippet}"}
                {"role": "user", "content": f"Based on the news snippet, help me identify if the article is about a recent fatal police shooting. The incident has to be about police officer fired shots and killed someone. The victims should be dead. And the incident should happened within three days of the publication date, not happened in the past. Return Y if the article satisfies all these requirements, otherwise return N. Snippet: {snippet}"}
            ]
            )
        answer = completion.choices[0].message.content
        print(answer)
        print("----")
    return answer

# def detect_duplicate(snippet, model):
    # if model == 'gpt-3.5-turbo':
    #     completion = client.chat.completions.create(
    #         model="gpt-3.5-turbo",
    #         messages=[
    #             # {"role": "system", "content": "You are a researcher skilled in reading news articles to identify the ones about fatal police shooting incidents."},
    #             {"role": "user", "content": f"Based on the news snippet, help me identify if this shooting incident has already been recorded in the database. If it is a duplicate, return N. Otherwise return Y. Snippet: {snippet}"}
    #         ]
    #         )
    #     answer = completion.choices[0].message.content
    #     print(answer)
    #     print("----")
    # return answer

model = 'gpt-3.5-turbo'
# Classify each snippet
for index, row in df.iterrows():
    df.at[index, 'is_fatal_police_shooting'] = classify_snippet(row['snippet'], model)
    # if df.at[index, 'is_fatal_police_shooting'] == 'Y':
    #     df.at[index, 'not_duplicate?'] = detect_duplicate(row['snippet'], model)
df.to_csv(f'data_storage/classified_results_{model}.csv', index=False)
