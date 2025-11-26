import requests

TED_API = "https://ted.europa.eu/api/v2/notices/search"

def search_ted(keyword: str, limit=20):
    params = {
        "text": keyword,
        "limit": limit
    }
    resp = requests.get(TED_API, params=params)
    resp.raise_for_status()
    return resp.json()

def get_ted_notice(notice_id: str):
    url = f"https://ted.europa.eu/api/v2/notices/{notice_id}"
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json()

print(search_ted("géomètre"))
