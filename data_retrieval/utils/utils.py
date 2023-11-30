import requests
from newspaper import Article
# import unicodedata
import concurrent.futures

# Function to split the domain list into chunks
def split_into_chunks(domains, chunk_size):
    for i in range(0, len(domains), chunk_size):
        yield domains[i:i + chunk_size]
        
def get_snippet_from_newspaper3k(url):
    extracted_article = Article(url)
    extracted_article.download()
    extracted_article.parse()
    return extracted_article.text

def get_snippet_from_wayback_machine(url):
    response = requests.get(url)
    response.raise_for_status()
    snippet = response.json().get('snippet', '')
    # return response.text 
    return snippet

def fetch_snippet(article_url, wayback_url):
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_to_method = {
            executor.submit(get_snippet_from_newspaper3k, article_url): 'newspaper3k',
            executor.submit(get_snippet_from_wayback_machine, wayback_url): 'wayback'
        }
        for future in concurrent.futures.as_completed(future_to_method):
            method = future_to_method[future]
            try:
                data = future.result()
                return data, method
            except Exception as exc:
                print(f"{method} method failed with exception: {exc}")


def sanitize_snippet(snippet):
    sanitized_snippet = snippet.replace('\n', ' ').replace('\r', '').strip()
    # Normalize Unicode characters
    # normalized_snippet = unicodedata.normalize('NFKD', sanitized_snippet)
    return sanitized_snippet