import os

from dotenv import load_dotenv
from firecrawl import Firecrawl

load_dotenv()

firecrawl = Firecrawl(api_key=os.environ["FIRECRAWL_API_KEY"])


def fetch_raw_text(url: str) -> str:
    result = firecrawl.scrape(url, formats=["markdown"])
    return result.markdown
