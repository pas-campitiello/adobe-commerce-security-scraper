import requests
from bs4 import BeautifulSoup
from datetime import datetime

# --- User Inputs ---
URLS = [
    "https://helpx.adobe.com/security/products/magento.html",
    "https://helpx.adobe.com/security.html",
    "https://experienceleague.adobe.com/en/docs/commerce-operations/release/notes/security-patches/overview",
    "https://devdocs.magento.com/guides/v2.4/release-notes/bk-release-notes.html",
    "https://support.magento.com/hc/en-us/sections/360010506631-Security-patches",
    "https://magento.com/security/patches",
    "https://experienceleague.adobe.com/docs/commerce-operations/installation-guide/tutorials/extensions.html"
    # Add more URLs as needed
]
FROM_DATE = datetime(2025, 5, 1)
TO_DATE = datetime(2025, 6, 25)  # Current date

# --- Helper Functions ---

def parse_date(date_str):
    """Parse date in various formats found on Adobe bulletins."""
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%Y-%m-%d", "%m/%d/%Y", "%d %B %Y", "%B %Y"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    # Try ISO format
    try:
        return datetime.fromisoformat(date_str)
    except Exception:
        return None

def is_adobe_commerce_bulletin(title, url):
    """Heuristics to identify Adobe Commerce (Magento) security bulletins."""
    keywords = ["commerce", "magento"]
    return any(k in title.lower() for k in keywords) or any(k in url.lower() for k in keywords)

def extract_bulletins_from_security_bulletin_page(url):
    """Extracts bulletins from Adobe's main security bulletin table."""
    bulletins = []
    resp = requests.get(url)
    soup = BeautifulSoup(resp.content, "html.parser")

    # Find tables with bulletin listings
    tables = soup.find_all("table")
    for table in tables:
        headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]
        if "title" in headers and "originally posted" in headers:
            for row in table.find_all("tr")[1:]:
                cells = row.find_all("td")
                if len(cells) < 2:
                    continue
                title = cells[0].get_text(strip=True)
                date_str = cells[1].get_text(strip=True)
                date = parse_date(date_str)
                link = cells[0].find("a")
                href = link["href"] if link and link.has_attr("href") else url
                if is_adobe_commerce_bulletin(title, href):
                    bulletins.append({
                        "title": title,
                        "date": date,
                        "url": href if href.startswith("http") else "https://helpx.adobe.com" + href
                    })
    return bulletins

def extract_bulletins_from_magento_page(url):
    """Extracts bulletins from the Magento-specific security page."""
    bulletins = []
    resp = requests.get(url)
    soup = BeautifulSoup(resp.content, "html.parser")
    # Look for tables or lists of bulletins
    for link in soup.find_all("a", href=True):
        href = link["href"]
        text = link.get_text(strip=True)
        if "apsb" in href.lower() or "security" in href.lower():
            # Try to find a date near the link
            date = None
            parent = link.find_parent("tr") or link.find_parent("li") or link.parent
            if parent:
                possible_dates = [t for t in parent.stripped_strings if any(c.isdigit() for c in t) and len(t) >= 8]
                for t in possible_dates:
                    d = parse_date(t)
                    if d:
                        date = d
                        break
            if is_adobe_commerce_bulletin(text, href):
                bulletins.append({
                    "title": text,
                    "date": date,
                    "url": href if href.startswith("http") else "https://helpx.adobe.com" + href
                })
    return bulletins

def extract_bulletins_from_experienceleague_page(url):
    """Extracts bulletins from the Experience League security patch notes."""
    bulletins = []
    resp = requests.get(url)
    soup = BeautifulSoup(resp.content, "html.parser")
    # Look for sections or tables with patch releases
    for header in soup.find_all(["h2", "h3"]):
        title = header.get_text(strip=True)
        if is_adobe_commerce_bulletin(title, url):
            # Try to find a date in the following sibling
            date = None
            sib = header.find_next_sibling()
            while sib and not date:
                if sib.name and ("date" in sib.get_text(strip=True).lower() or any(c.isdigit() for c in sib.get_text(strip=True))):
                    d = parse_date(sib.get_text(strip=True))
                    if d:
                        date = d
                        break
                sib = sib.find_next_sibling()
            bulletins.append({
                "title": title,
                "date": date,
                "url": url
            })
    return bulletins

def get_bulletins(url):
    """Dispatch to the right extraction function based on URL."""
    if "security.html" in url:
        return extract_bulletins_from_security_bulletin_page(url)
    elif "magento" in url:
        return extract_bulletins_from_magento_page(url)
    elif "experienceleague" in url:
        return extract_bulletins_from_experienceleague_page(url)
    else:
        # Fallback: try generic extraction
        return extract_bulletins_from_magento_page(url)

# --- Main Logic ---

all_bulletins = []
for url in URLS:
    print(url)
    try:
        bulletins = get_bulletins(url)
        all_bulletins.extend(bulletins)
    except Exception as e:
        print(f"Failed to scrape {url}: {e}")

# Filter by date range and deduplicate
seen = set()
filtered = []
for b in all_bulletins:
    if not b["date"]:
        continue
    if FROM_DATE <= b["date"] <= TO_DATE:
        key = (b["title"], b["date"], b["url"])
        if key not in seen:
            seen.add(key)
            filtered.append(b)

# Sort by date descending
filtered.sort(key=lambda x: x["date"], reverse=True)

# --- Output ---
print(f"\nAdobe Commerce Security Patches from {FROM_DATE.date()} to {TO_DATE.date()}:\n")
for b in filtered:
    date_str = b["date"].strftime("%Y-%m-%d") if b["date"] else "Unknown Date"
    print(f"{date_str} | {b['title']}\n  {b['url']}\n")
