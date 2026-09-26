import html
import os
import re
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


def fetch_page_text(url: str) -> str:
    """Plain-HTTP fetch of an HTML page, reduced to its visible text (no Firecrawl).

    Scripts and styles are dropped so embedded JSON (which on some sites holds
    rules for many other products) cannot be mistaken for the page's own text.
    """
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        html_text = response.read().decode("utf-8", errors="replace")
    html_text = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html_text)
    # Block-level tags become line breaks, so a banner keeps its own line
    # instead of being glued to the UI labels around it; inline tags become spaces.
    html_text = re.sub(r"(?i)</?(?:div|p|h[1-6]|li|ul|ol|br|section|article|header|footer|main|nav|tr|td|th|table)\b[^>]*>", "\n", html_text)
    html_text = re.sub(r"(?s)<[^>]+>", " ", html_text)
    lines = (" ".join(line.split()) for line in html.unescape(html_text).split("\n"))
    return "\n".join(line for line in lines if line)


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
