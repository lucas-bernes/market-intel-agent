import os
import urllib.request

from dotenv import load_dotenv
from firecrawl import Firecrawl

load_dotenv()

firecrawl = Firecrawl(api_key=os.environ["FIRECRAWL_API_KEY"])


# Páginas que já são texto/JSON puro não precisam do Firecrawl (que cobra por
# página): um GET simples resolve, de graça.
_PLAIN_SUFFIXES = (".txt", ".json", ".md")


def fetch_raw_text(url: str) -> str:
    if url.split("?")[0].endswith(_PLAIN_SUFFIXES):
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read().decode("utf-8", errors="replace")

    result = firecrawl.scrape(url, formats=["markdown"])
    return result.markdown


def _first_result(query: str) -> tuple[str, str]:
    # Devolve (url, markdown) do 1º resultado — a URL é guardada como fonte
    # (evidência) de cada dado extraído.
    results = firecrawl.search(query, limit=1, scrape_options={"formats": ["markdown"]})
    item = results.web[0]
    url = getattr(item, "url", None) or getattr(getattr(item, "metadata", None), "url", None)
    return url, item.markdown


def find_review_text(model_name: str) -> tuple[str, str]:
    return _first_result(f"{model_name} review realism consistency quality")


def find_provider_info(provider_name: str) -> tuple[str, str]:
    return _first_result(f"{provider_name} API pricing uptime reliability review")
