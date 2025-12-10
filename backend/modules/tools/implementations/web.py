"""
Web content tool implementations - Webpage fetching and content extraction
"""
from typing import Dict, Any
from modules.agent.context import AgentContext
import httpx
from bs4 import BeautifulSoup


async def fetch_webpage_impl(
    context: AgentContext,
    url: str,
    extract_text: bool = False
) -> Dict[str, Any]:
    """
    Fetch content from a web URL
    
    Args:
        context: Agent context
        url: The URL to fetch (e.g., 'https://polygon.readthedocs.io/en/latest/Stocks.html')
        extract_text: If True, attempts to extract clean text from HTML (removes tags). Default: False
    
    Returns:
        Dict with success status, content, and metadata
    """
    try:
        # Fetch the URL
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                url,
                headers={'User-Agent': 'Mozilla/5.0 (compatible; FinchBot/1.0)'},
                follow_redirects=True
            )
            response.raise_for_status()
            
            content = response.text
            content_type = response.headers.get('content-type', '')
            
            # Extract text if requested and content is HTML
            if extract_text and 'html' in content_type.lower():
                try:
                    soup = BeautifulSoup(content, 'html.parser')
                    # Remove script and style elements
                    for script in soup(["script", "style"]):
                        script.decompose()
                    # Get text
                    text = soup.get_text()
                    # Clean up whitespace
                    lines = (line.strip() for line in text.splitlines())
                    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                    content = '\n'.join(chunk for chunk in chunks if chunk)
                except Exception as e:
                    # If text extraction fails, return raw HTML
                    print(f"⚠️ Text extraction failed: {e}, returning raw HTML")
            
            return {
                "success": True,
                "url": str(response.url),
                "content": content,
                "content_type": content_type,
                "size_bytes": len(content),
                "status_code": response.status_code
            }
    
    except httpx.HTTPError as e:
        return {
            "success": False,
            "error": f"HTTP error: {str(e)}",
            "url": url
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to fetch URL: {str(e)}",
            "url": url
        }

