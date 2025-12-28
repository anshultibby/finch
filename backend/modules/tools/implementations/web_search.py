"""
Web Search Implementation

First-order web search tools using Serper (Google Search) and Jina AI (scraping).
"""
import os
import requests
from typing import Optional
from pydantic import BaseModel, Field

from modules.agent.context import AgentContext
from utils.logger import get_logger

logger = get_logger(__name__)


class WebSearchParams(BaseModel):
    """Parameters for web search"""
    query: str = Field(..., description="Search query string")
    num_results: int = Field(default=10, description="Number of results (max 100)")
    search_type: str = Field(
        default="search",
        description="Type of search: 'search' (web), 'news', or 'images'"
    )


class ScrapeUrlParams(BaseModel):
    """Parameters for URL scraping"""
    url: str = Field(..., description="URL to scrape")
    timeout: int = Field(default=30, description="Request timeout in seconds")


def _call_serper_api(endpoint: str, payload: dict) -> dict:
    """Call Serper API endpoint"""
    api_key = os.getenv('SERPER_API_KEY')
    if not api_key:
        return {"error": "SERPER_API_KEY not set"}
    
    url = f"https://google.serper.dev{endpoint}"
    
    try:
        response = requests.post(
            url,
            headers={
                'X-API-KEY': api_key,
                'Content-Type': 'application/json'
            },
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    except requests.RequestException as e:
        return {"error": f"Serper API request failed: {str(e)}"}


def web_search_impl(
    query: str,
    context: AgentContext,
    num_results: int = 10,
    search_type: str = "search"
) -> dict:
    """
    Search the web using Google via Serper API
    
    Returns:
        dict with search results:
            - organic: List of web results with title, link, snippet
            - news: List of news articles (if search_type="news")
            - answerBox: Featured snippet if available
            - knowledgeGraph: Knowledge panel if available
    """
    endpoint = f"/{search_type}"
    payload = {
        "q": query,
        "num": min(num_results, 100)
    }
    
    result = _call_serper_api(endpoint, payload)
    
    if "error" in result:
        return {"success": False, "error": result["error"]}
    
    return {"success": True, **result}


def news_search_impl(
    query: str,
    context: AgentContext,
    num_results: int = 10
) -> dict:
    """Search Google News"""
    return web_search_impl(query, context, num_results, search_type="news")


def scrape_url_impl(
    url: str,
    context: AgentContext,
    timeout: int = 30
) -> dict:
    """
    Scrape a webpage and convert to clean markdown text using Jina AI Reader.
    
    Jina Reader:
    - Removes ads, navigation, footers
    - Extracts main content
    - Converts to clean markdown
    - Handles JavaScript-rendered pages
    
    Returns:
        dict with:
            - success: bool
            - content: Clean markdown text of the page
            - title: Page title
            - url: Final URL (after redirects)
            - error: Error message if failed
    """
    try:
        jina_url = f"https://r.jina.ai/{url}"
        
        response = requests.get(
            jina_url,
            headers={'Accept': 'text/plain'},
            timeout=timeout
        )
        response.raise_for_status()
        
        content = response.text
        
        title = ""
        for line in content.split('\n'):
            if line.startswith('# '):
                title = line[2:].strip()
                break
        
        return {
            "success": True,
            "content": content,
            "title": title,
            "url": url
        }
    
    except requests.Timeout:
        return {
            "success": False,
            "content": "",
            "title": "",
            "url": url,
            "error": f"Request timed out after {timeout} seconds"
        }
    
    except requests.RequestException as e:
        return {
            "success": False,
            "content": "",
            "title": "",
            "url": url,
            "error": f"Failed to scrape URL: {str(e)}"
        }

