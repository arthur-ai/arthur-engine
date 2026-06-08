import logging
from typing import Any, Dict

import httpx

from schemas.chatbot_schemas import WikipediaArticle, WikipediaSearchResult

logger = logging.getLogger(__name__)

WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php"
WIKIPEDIA_PAGE_URL = "https://en.wikipedia.org/wiki"
WIKIPEDIA_USER_AGENT = "ArthurEngineDemoBot/1.0 (https://www.arthur.ai)"
WIKIPEDIA_HTTP_TIMEOUT_SECONDS = 15.0
WIKIPEDIA_SEARCH_RESULT_LIMIT = 5


async def wikipedia_search(query: str) -> WikipediaSearchResult:
    params = {
        "action": "opensearch",
        "search": query,
        "limit": str(WIKIPEDIA_SEARCH_RESULT_LIMIT),
        "namespace": "0",
        "format": "json",
    }
    async with httpx.AsyncClient(timeout=WIKIPEDIA_HTTP_TIMEOUT_SECONDS) as client:
        response = await client.get(
            WIKIPEDIA_API_URL,
            params=params,
            headers={"User-Agent": WIKIPEDIA_USER_AGENT},
        )
        response.raise_for_status()
        payload = response.json()

    titles = payload[1] if len(payload) > 1 and isinstance(payload[1], list) else []
    return WikipediaSearchResult(titles=[str(t) for t in titles])


async def wikipedia_fetch(title: str) -> WikipediaArticle:
    params = {
        "action": "query",
        "prop": "extracts",
        "explaintext": "1",
        "redirects": "1",
        "titles": title,
        "format": "json",
        "formatversion": "2",
    }
    async with httpx.AsyncClient(timeout=WIKIPEDIA_HTTP_TIMEOUT_SECONDS) as client:
        response = await client.get(
            WIKIPEDIA_API_URL,
            params=params,
            headers={"User-Agent": WIKIPEDIA_USER_AGENT},
        )
        response.raise_for_status()
        payload: Dict[str, Any] = response.json()

    pages = payload.get("query", {}).get("pages", [])
    page = pages[0] if pages else {}
    resolved_title = str(page.get("title", title))
    extract = str(page.get("extract", ""))
    page_slug = resolved_title.replace(" ", "_")
    return WikipediaArticle(
        title=resolved_title,
        extract=extract,
        url=f"{WIKIPEDIA_PAGE_URL}/{page_slug}",
    )
