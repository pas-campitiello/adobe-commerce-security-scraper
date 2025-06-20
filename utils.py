"""
Utility functions for Adobe Commerce Security Scraper
"""

import requests
import time
import logging
import re
from datetime import datetime
from typing import Optional
from config import REQUEST_TIMEOUT, MAX_RETRIES, RETRY_DELAY, LOG_FILE, LOG_LEVEL, LOG_FORMAT

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format=LOG_FORMAT,
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )

def retry_request(session: requests.Session, url: str, max_retries: int = MAX_RETRIES) -> Optional[requests.Response]:
    """
    Make HTTP request with retry logic
    
    Args:
        session: requests session object
        url: URL to request
        max_retries: maximum number of retry attempts
    
    Returns:
        Response object or None if all retries failed
    """
    logger = logging.getLogger(__name__)
    
    for attempt in range(max_retries + 1):
        try:
            logger.debug(f"Attempting to fetch {url} (attempt {attempt + 1})")
            
            response = session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            
            logger.debug(f"Successfully fetched {url}")
            return response
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request failed for {url} (attempt {attempt + 1}): {str(e)}")
            
            if attempt < max_retries:
                logger.info(f"Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
            else:
                logger.error(f"All retry attempts failed for {url}")
                return None
    
    return None

def clean_text(text: str) -> str:
    """
    Clean and normalize text content
    
    Args:
        text: raw text to clean
    
    Returns:
        cleaned text
    """
    if not text:
        return ""
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    # Remove common unwanted characters
    text = re.sub(r'[\r\n\t]+', ' ', text)
    
    # Remove multiple spaces
    text = re.sub(r' {2,}', ' ', text)
    
    return text

def parse_date(date_string: str) -> datetime:
    """
    Parse various date formats into datetime object
    
    Args:
        date_string: date string in various formats
    
    Returns:
        datetime object
    """
    if not date_string:
        return datetime.now()
    
    # Clean the date string
    date_string = clean_text(date_string)
    
    # Common date patterns and their corresponding formats
    date_patterns = [
        (r'\d{4}-\d{2}-\d{2}', '%Y-%m-%d'),
        (r'\d{2}/\d{2}/\d{4}', '%m/%d/%Y'),
        (r'\d{1,2}/\d{1,2}/\d{4}', '%m/%d/%Y'),
        (r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}', '%B %d, %Y'),
        (r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}', '%b %d, %Y'),
        (r'\d{1,2}\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}', '%d %B %Y'),
        (r'\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}', '%d %b %Y'),
    ]
    
    for pattern, date_format in date_patterns:
        match = re.search(pattern, date_string, re.I)
        if match:
            try:
                # Clean up the matched string
                matched_date = match.group().replace(',', '')
                return datetime.strptime(matched_date, date_format)
            except ValueError:
                continue
    
    # If no pattern matches, return current date
    logging.getLogger(__name__).warning(f"Could not parse date: {date_string}")
    return datetime.now()

def is_recent_date(date_obj: datetime, days: int = 30) -> bool:
    """
    Check if a date is within the last N days
    
    Args:
        date_obj: datetime object to check
        days: number of days to consider as recent
    
    Returns:
        True if date is recent, False otherwise
    """
    now = datetime.now()
    delta = now - date_obj
    return delta.days <= days

def extract_cve_ids(text: str) -> list:
    """
    Extract CVE IDs from text
    
    Args:
        text: text to search for CVE IDs
    
    Returns:
        list of CVE IDs found
    """
    if not text:
        return []
    
    cve_pattern = r'CVE-\d{4}-\d{4,}'
    cve_ids = re.findall(cve_pattern, text, re.I)
    
    # Remove duplicates and return
    return list(set(cve_ids))

def truncate_text(text: str, max_length: int = 200) -> str:
    """
    Truncate text to specified length while preserving word boundaries
    
    Args:
        text: text to truncate
        max_length: maximum length of text
    
    Returns:
        truncated text
    """
    if not text or len(text) <= max_length:
        return text
    
    # Find the last space within the limit
    truncated = text[:max_length]
    last_space = truncated.rfind(' ')
    
    if last_space > 0:
        truncated = truncated[:last_space]
    
    return truncated + '...'

def validate_url(url: str) -> bool:
    """
    Validate if a URL is properly formatted
    
    Args:
        url: URL to validate
    
    Returns:
        True if valid, False otherwise
    """
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    return url_pattern.match(url) is not None

def format_markdown_link(title: str, url: str) -> str:
    """
    Format a markdown link with proper escaping
    
    Args:
        title: link title
        url: link URL
    
    Returns:
        formatted markdown link
    """
    # Escape special characters in title
    title = title.replace('[', '\\[').replace(']', '\\]')
    
    return f"[{title}]({url})"

def get_domain_from_url(url: str) -> str:
    """
    Extract domain from URL
    
    Args:
        url: URL to extract domain from
    
    Returns:
        domain name
    """
    import urllib.parse
    
    try:
        parsed = urllib.parse.urlparse(url)
        return parsed.netloc
    except Exception:
        return url
