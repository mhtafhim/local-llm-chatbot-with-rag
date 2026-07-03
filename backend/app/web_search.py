import requests
from bs4 import BeautifulSoup


def web_search(query: str, max_results: int = 4) -> list[dict[str, str]]:
    try:
        resp = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15,
        )
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for result in soup.select(".result")[:max_results]:
            title_el = result.select_one(".result__title")
            snippet_el = result.select_one(".result__snippet")
            link_el = result.select_one(".result__url")
            if title_el and snippet_el:
                results.append(
                    {
                        "title": title_el.get_text(strip=True),
                        "snippet": snippet_el.get_text(strip=True),
                        "url": link_el.get_text(strip=True) if link_el else "",
                    }
                )
        return results
    except Exception as exc:
        return [{"title": "Search failed", "snippet": str(exc), "url": ""}]
