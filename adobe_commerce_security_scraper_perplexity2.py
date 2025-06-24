import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re

# CONFIGURATION
urls = [
    "https://helpx.adobe.com/security/products/magento.html",
    "https://helpx.adobe.com/security.html",
    "https://devdocs.magento.com/guides/v2.4/release-notes/bk-release-notes.html",
    "https://support.magento.com/hc/en-us/sections/360010506631-Security-patches",
    "https://magento.com/security/patches",
    "https://experienceleague.adobe.com/docs/commerce-operations/installation-guide/tutorials/extensions.html",
]
from_date = datetime(2025, 1, 1)
to_date = datetime(2025, 6, 24)  # Current date

# Helper function to parse date strings in various formats
def parse_date(date_str):
    for fmt in ("%B %d, %Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d %b %Y"):
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    # Try extracting a date with regex if formats above fail
    match = re.search(r"(\d{4})[-/](\d{2})[-/](\d{2})", date_str)
    if match:
        return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    return None

# Main scraping logic
def scrape_adobe_security(urls, from_date, to_date):
    found_bulletins = []

    for url in urls:
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # Find all links that look like security bulletins for Magento/Adobe Commerce
            for link in soup.find_all("a", href=True):
                href = link["href"]
                text = link.get_text(strip=True)
                # Heuristic: look for 'magento', 'commerce', 'apsb', or 'security' in link or text
                if any(kw in href.lower() for kw in ["magento", "commerce", "apsb"]) or \
                   any(kw in text.lower() for kw in ["magento", "commerce", "apsb", "security"]):
                    # Try to extract date from surrounding text or parent elements
                    date = None
                    # Check if the link text or parent contains a date
                    parent = link.parent
                    candidates = [text]
                    if parent:
                        candidates.append(parent.get_text(" ", strip=True))
                    for c in candidates:
                        date_match = re.search(r"(\d{4}-\d{2}-\d{2})|([A-Za-z]{3,9} \d{1,2}, \d{4})", c)
                        if date_match:
                            date = parse_date(date_match.group(0))
                            break
                    # If not found, try to fetch the bulletin page and extract date from there
                    if not date and href.startswith("http"):
                        try:
                            b_resp = requests.get(href, timeout=10)
                            b_resp.raise_for_status()
                            b_soup = BeautifulSoup(b_resp.text, "html.parser")
                            # Look for date in meta, h1, h2, or summary sections
                            meta_date = b_soup.find("meta", {"name": "date"})
                            if meta_date and meta_date.get("content"):
                                date = parse_date(meta_date["content"])
                            else:
                                # Try to find a date in visible text
                                possible_dates = b_soup.find_all(text=re.compile(r"\d{4}-\d{2}-\d{2}|[A-Za-z]{3,9} \d{1,2}, \d{4}"))
                                for pd in possible_dates:
                                    date = parse_date(pd)
                                    if date:
                                        break
                        except Exception:
                            pass
                    # If date found and in range, add to results
                    if date and from_date <= date <= to_date:
                        found_bulletins.append({
                            "date": date,
                            "title": text if text else href,
                            "link": href if href.startswith("http") else f"https://{url.split('/')[2]}{href}"
                        })
        except Exception as e:
            print(f"Error processing {url}: {e}")

    # Remove duplicates
    seen = set()
    unique_bulletins = []
    for b in found_bulletins:
        key = (b['date'], b['title'], b['link'])
        if key not in seen:
            unique_bulletins.append(b)
            seen.add(key)

    # Sort by date descending
    unique_bulletins.sort(key=lambda x: x['date'], reverse=True)
    return unique_bulletins

# Print results
def print_bulletins(bulletins):
    if not bulletins:
        print("No Adobe Commerce security bulletins found in the specified date range.")
        return
    print("Adobe Commerce Security Bulletins:")
    for b in bulletins:
        print(f"{b['date'].strftime('%Y-%m-%d')} | {b['title']}\n  {b['link']}\n")

if __name__ == "__main__":
    bulletins = scrape_adobe_security(urls, from_date, to_date)
    print_bulletins(bulletins)
