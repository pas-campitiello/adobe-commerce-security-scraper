import requests
from bs4 import BeautifulSoup
from datetime import datetime

def scrape_adobe_security(url, from_date, to_date):
    """
    Scrapes Adobe's security bulletin page for Adobe Commerce security patches or updates.

    Args:
    - url (str): URL of the Adobe security bulletin page.
    - from_date (datetime): Start date for filtering patches.
    - to_date (datetime): End date for filtering patches.

    Returns:
    - list: List of dictionaries containing patch information (date, title, link).
    """
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    patches = []

    # Look for links containing "apsb" or pages about security updates
    for link in soup.find_all('a'):
        href = link.get('href')
        if href and ("apsb" in href or "security" in href.lower()):
            try:
                # Extract publication date from the link text or nearby elements
                date_text = link.text.strip() or link.find_next('span').text.strip()
                date = datetime.strptime(date_text, '%B %d, %Y')  # Assuming this format
            except (AttributeError, ValueError):
                # Try to find a nearby date element
                date_element = link.find_next(['span', 'p'])
                if date_element:
                    try:
                        date = datetime.strptime(date_element.text.strip(), '%B %d, %Y')
                    except ValueError:
                        continue  # Skip if date parsing fails
                else:
                    continue  # Skip if no date found

            if from_date <= date <= to_date:
                patches.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'title': link.text.strip() or 'Security Update',
                    'link': href if href.startswith('http') else f"https://helpx.adobe.com{href}"
                })

    return patches

def main():
    urls = [
        'https://helpx.adobe.com/security/products/magento.html',
        'https://helpx.adobe.com/security.html',
        'https://devdocs.magento.com/guides/v2.4/release-notes/bk-release-notes.html',
        'https://support.magento.com/hc/en-us/sections/360010506631-Security-patches',
        'https://magento.com/security/patches',
        'https://experienceleague.adobe.com/docs/commerce-operations/installation-guide/tutorials/extensions.html'
    ]

    from_date = datetime(2025, 1, 1)
    to_date = datetime.today()

    all_patches = []
    for url in urls:
        patches = scrape_adobe_security(url, from_date, to_date)
        all_patches.extend(patches)

    # Sort patches by date
    all_patches.sort(key=lambda x: x['date'])

    # Print the patches
    print("Adobe Commerce Security Patches:")
    for patch in all_patches:
        print(f"{patch['date']} - {patch['title']}: {patch['link']}")

if __name__ == "__main__":
    main()
