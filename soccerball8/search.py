"""Google Custom Search JSON API wrapper."""

from typing import List, TypedDict

import requests


class SearchResult(TypedDict):
    title: str
    snippet: str
    link: str


class GoogleSearchError(RuntimeError):
    pass


def search_google(
    query: str, api_key: str, cse_id: str, num_results: int = 8
) -> List[SearchResult]:
    if not api_key or not cse_id:
        raise GoogleSearchError("GOOGLE_API_KEY / GOOGLE_CSE_ID are not configured")

    response = requests.get(
        "https://www.googleapis.com/customsearch/v1",
        params={"key": api_key, "cx": cse_id, "q": query, "num": min(num_results, 10)},
        timeout=15,
    )
    if response.status_code != 200:
        raise GoogleSearchError(f"Google search failed: {response.status_code} {response.text}")

    data = response.json()
    return [
        {
            "title": item.get("title", ""),
            "snippet": item.get("snippet", ""),
            "link": item.get("link", ""),
        }
        for item in data.get("items", [])
    ]
