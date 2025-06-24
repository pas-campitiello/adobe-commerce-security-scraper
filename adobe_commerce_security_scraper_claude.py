import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def parse_date(date_str):
    """Convert various date formats to datetime object."""
    try:
        # Common date formats found on Adobe pages
        formats = [
            '%B %d, %Y',  # e.g., January 14, 2025
            '%Y-%m-%d',   # e.g., 2025-01-14
            '%m/%d/%Y',   # e.g., 01/14/2025
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        return None
    except Exception:
        return None

def create_session():
    """Create a requests session with retry logic."""
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def scrape_security_patches(urls, from_date, to_date):
    """Scrape Adobe Commerce security patches from given URLs within date range."""
    patches = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124'}
    session = create_session()

    for url in urls:
        try:
            response = session.get(url, headers=headers, timeout=30)  # Increased timeout to 30s
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for potential security bulletin entries
            bulletin_items = soup.find_all(['a', 'div', 'tr', 'li'], text=re.compile(r'(APSB|Security|Patch)', re.I))

            for item in bulletin_items:
                # Extract title
                title = item.get_text(strip=True) if item.get_text() else ''
                if not title or ('commerce' not in title.lower() and 'magento' not in title.lower()):
                    continue

                # Find parent or sibling elements that might contain date
                date = None
                parent = item.find_parent(['tr', 'div', 'li'])
                if parent:
                    date_text = parent.find(text=re.compile(r'\d{1,2}/\d{1,2}/\d{4}|\w+\s+\d{1,2},\s+\d{4}'))
                    if date_text:
                        date = parse_date(date_text)

                # If no date found, try to find date in nearby elements
                if not date:
                    sibling = item.find_previous() or item.find_next()
                    if sibling:
                        date_text = sibling.get_text(strip=True)
                        date = parse_date(date_text)

                # Extract link
                link = item.get('href') if item.name == 'a' else ''
                if link and not link.startswith('http'):
                    link = requests.compat.urljoin(url, link)

                # Filter by date range and Adobe Commerce relevance
                if date and from_date <= date <= to_date and ('commerce' in title.lower() or 'magento' in title.lower()):
                    patches.append({
                        'date': date,
                        'title': title,
                        'link': link or url
                    })

        except requests.exceptions.RequestException as e:
            print(f"Error scraping {url}: {e}")
            continue

    return sorted(patches, key=lambda x: x['date'], reverse=True)

def main():
    # Input parameters
    urls = [
        'https://helpx.adobe.com/security/products/magento.html',
        'https://helpx.adobe.com/security.html',
        'https://devdocs.magento.com/guides/v2.4/release-notes/bk-release-notes.html',
        'https://support.magento.com/hc/en-us/sections/360010506631-Security-patches',
        'https://magento.com/security/patches',
        'https://experienceleague.adobe.com/docs/commerce-operations/installation-guide/tutorials/extensions.html'
    ]
    from_date = datetime(2025, 1, 1)
    to_date = datetime.now()

    # Scrape and filter patches
    patches = scrape_security_patches(urls, from_date, to_date)

    # Print results
    if not patches:
        print("No Adobe Commerce security patches found in the specified date range.")
    else:
        print("\nAdobe Commerce Security Patches:")
        print("-" * 50)
        for patch in patches:
            print(f"Date: {patch['date'].strftime('%Y-%m-%d')}")
            print(f"Title: {patch['title']}")
            print(f"Link: {patch['link']}")
            print("-" * 50)

if __name__ == "__main__":
    main()