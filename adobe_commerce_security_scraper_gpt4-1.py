import requests
from bs4 import BeautifulSoup
from datetime import datetime
from dateutil import parser as dateparser

# -----------------------------------
# CONFIG: FILLED BY USER
urls = [
    "https://helpx.adobe.com/security/products/magento.html",
    "https://helpx.adobe.com/security.html",
    "https://devdocs.magento.com/guides/v2.4/release-notes/bk-release-notes.html",
    "https://support.magento.com/hc/en-us/sections/360010506631-Security-patches",
    "https://magento.com/security/patches",
    "https://experienceleague.adobe.com/docs/commerce-operations/installation-guide/tutorials/extensions.html"
]
from_date = datetime(2025, 1, 1)
to_date = datetime.today()
# -----------------------------------

KEYWORDS = ["magento", "commerce", "security", "patch"]

def date_in_range(date_obj):
    return from_date <= date_obj <= to_date

def extract_patch_info(url, soup):
    entries = []

    # Heuristic: Find all links/blocks with relevant keywords.
    for a in soup.find_all('a', href=True):
        text = f"{a.get_text(' ', strip=True)} {a['href']}".lower()
        if any(k in text for k in KEYWORDS):
            parent = a.find_parent()
            while parent and parent.name not in ['li', 'tr', 'div', 'article', 'section', 'td', 'p', 'body']:
                parent = parent.find_parent()
            block = parent or a
            # Attempt to find publication date nearby
            date_str = None
            for tag in block.find_all(text=True):
                try:
                    parsed = dateparser.parse(tag.strip(), fuzzy=False)
                    if 2000 < parsed.year < 2100:
                        date_str = tag.strip()
                        pub_date = parsed
                        break
                except (ValueError, TypeError):
                    continue
            # Fallback: No date nearby
            if not date_str:
                pub_date = None
            # Title is link text or surrounding block's header
            title = a.get_text(strip=True) or block.get_text(" ", strip=True).split('\n')[0]
            # URL may be relative
            link = a['href']
            if link.startswith('/'):
                root = '/'.join(url.split('/')[:3])
                link = root + link
            elif not link.startswith('http'):
                link = url.rstrip('/') + '/' + link
            entries.append({
                "date": pub_date,
                "title": title.strip(),
                "link": link
            })
    return entries

def filter_and_print(entries):
    # Remove duplicates by link
    seen = set()
    output = []
    for e in entries:
        if not e["date"]:
            continue
        if not date_in_range(e["date"]):
            continue
        if e["link"] in seen:
            continue
        seen.add(e["link"])
        date_fmt = e["date"].strftime('%Y-%m-%d')
        output.append((e["date"], date_fmt, e["title"], e["link"]))

    # Print sorted by date descending
    for _, date_fmt, title, link in sorted(output, reverse=True):
        print(f"{date_fmt} | {title}\n  {link}\n")

def main():
    all_entries = []
    for url in urls:
        print(f"Scanning: {url}")
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            entries = extract_patch_info(url, soup)
            all_entries.extend(entries)
        except Exception as e:
            print(f"Failed to fetch/process {url}: {e}")
    filter_and_print(all_entries)

if __name__ == "__main__":
    main()
