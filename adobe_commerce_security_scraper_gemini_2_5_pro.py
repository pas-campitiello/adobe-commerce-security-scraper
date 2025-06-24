import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re

def parse_date(date_string):
    """
    Attempts to parse a date string into a datetime object, handling multiple common formats.
    """
    formats = [
        "%B %d, %Y",  # e.g., "May 14, 2024"
        "%b. %d, %Y", # e.g., "Dec. 12, 2023"
        "%m/%d/%Y",   # e.g., "10/10/2023"
        "%Y-%m-%d"    # e.g., "2023-01-01"
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_string, fmt)
        except ValueError:
            continue
    return None # Return None if no format matches

def scrape_helpx_adobe_magento_security(url):
    """
    Scrapes https://helpx.adobe.com/security/products/magento.html for security bulletins.
    This page typically lists Magento-specific bulletins in a table format.
    """
    patches = []
    print(f"  Fetching: {url}")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find the main table containing the security bulletins
        table = soup.find('table', class_='table-with-borders')
        if not table:
            # Fallback if the specific class is not found, try a generic table
            print(f"  Warning: Specific table class 'table-with-borders' not found on {url}. Trying generic table.")
            table = soup.find('table')
            if not table:
                print(f"  Warning: No table found on {url}. Skipping this URL.")
                return patches

        rows = table.find_all('tr')
        # Skip header row if present (check for <th> tags in the first row)
        if rows and rows[0].find('th'):
            rows = rows[1:]

        for row in rows:
            cols = row.find_all('td')
            # Expecting at least 3 columns: Link (APSB ID), Title/Description, Date
            if len(cols) >= 3:
                link_tag = cols[0].find('a')
                # Ensure it's an APSB link and points to a security advisory
                if link_tag and 'APSB' in link_tag.get_text(strip=True) and "/security/" in link_tag.get('href', ''):
                    title = cols[1].get_text(strip=True)
                    date_str = cols[2].get_text(strip=True)
                    full_link = requests.compat.urljoin(url, link_tag['href']) # Construct full URL

                    published_date = parse_date(date_str)
                    if published_date:
                        patches.append({
                            'title': title,
                            'date': published_date,
                            'link': full_link
                        })
    except requests.exceptions.RequestException as e:
        print(f"  Error accessing {url}: {e}")
    except Exception as e:
        print(f"  Error parsing {url}: {e}")
    return patches

def scrape_helpx_adobe_general_security(url):
    """
    Scrapes https://helpx.adobe.com/security.html for general security advisories,
    then filters for those related to Adobe Commerce/Magento.
    """
    patches = []
    print(f"  Fetching: {url}")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find year sections (e.g., <h2> or <h3> tags with year numbers)
        year_sections = soup.find_all(['h2', 'h3'], text=re.compile(r'^\d{4}$'))

        for year_section in year_sections:
            # Find the next sibling that contains the list of advisories (usually a ul or div)
            current_element = year_section.find_next_sibling()
            while current_element and current_element.name not in ['h2', 'h3']:
                # Look for list items (li) or paragraphs (p) that contain advisories
                for item in current_element.find_all(['li', 'p']):
                    link_tag = item.find('a')
                    # Check if the link contains "APSB" and the text mentions "Adobe Commerce" or "Magento"
                    if link_tag and 'APSB' in link_tag.get_text(strip=True):
                        full_text = item.get_text(strip=True)
                        if "Adobe Commerce" in full_text or "Magento" in full_text:
                            # Extract date: e.g., "(Published: May 14, 2024)"
                            date_match = re.search(r'Published:\s*(.*?)\)', full_text)
                            date_str = date_match.group(1).strip() if date_match else ''

                            # Extract title: often text after the date part e.g., ") - Some Title"
                            title_parts = full_text.split(') - ', 1) # Split only on the first occurrence
                            title = title_parts[1].strip() if len(title_parts) > 1 else full_text # Fallback

                            # Further refine title: remove APSB ID if it's still at the beginning
                            if title.startswith('APSB'):
                                # Attempt to remove "APSBxx-xx" from title if present
                                title = re.sub(r'APSB\d{2}-\d{2}\s*', '', title, 1).strip()


                            full_link = requests.compat.urljoin(url, link_tag['href'])

                            published_date = parse_date(date_str)
                            if published_date:
                                patches.append({
                                    'title': title,
                                    'date': published_date,
                                    'link': full_link
                                })
                current_element = current_element.find_next_sibling()

    except requests.exceptions.RequestException as e:
        print(f"  Error accessing {url}: {e}")
    except Exception as e:
        print(f"  Error parsing {url}: {e}")
    return patches

def adobe_commerce_security_scraper(urls, from_date_str, to_date_str):
    """
    Scrapes Adobe security bulletins for Adobe Commerce (Magento) patches
    within a specified date range.

    Args:
        urls (list): A list of Adobe security bulletin URLs.
        from_date_str (str): Start date in 'YYYY-MM-DD' format (e.g., '2025-01-01').
        to_date_str (str): End date in 'YYYY-MM-DD' format (e.g., '2025-06-24').
    """
    try:
        from_date = datetime.strptime(from_date_str, '%Y-%m-%d')
        # Set to_date to the end of the day to include patches published on to_date
        to_date = datetime.strptime(to_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59, microsecond=999999)
    except ValueError as e:
        print(f"Error: Invalid date format for 'from_date' or 'to_date'. Please use YYYY-MM-DD. {e}")
        return

    all_patches = []
    print("\n--- Starting Adobe Commerce Security Scraper ---")

    for url in urls:
        if "helpx.adobe.com/security/products/magento.html" in url:
            all_patches.extend(scrape_helpx_adobe_magento_security(url))
        elif "helpx.adobe.com/security.html" in url:
            all_patches.extend(scrape_helpx_adobe_general_security(url))
        else:
            print(f"  Skipping unsupported URL for specific security bulletin parsing: {url}")

    # Filter patches by the specified date range
    filtered_patches = [
        patch for patch in all_patches
        if from_date <= patch['date'] <= to_date
    ]

    # Remove duplicates based on link to ensure unique entries
    unique_patches_dict = {patch['link']: patch for patch in filtered_patches}
    unique_patches = list(unique_patches_dict.values())

    # Sort the unique patches by date
    sorted_patches = sorted(unique_patches, key=lambda x: x['date'])

    print("\n--- Adobe Commerce Security Patches Found ---")
    if not sorted_patches:
        print(f"No Adobe Commerce security patches found between {from_date_str} and {to_date_str}.")
    else:
        for patch in sorted_patches:
            print(f"Date: {patch['date'].strftime('%Y-%m-%d')}")
            print(f"Title: {patch['title']}")
            print(f"Link: {patch['link']}")
            print("-" * 30)
    print("--- Scraper Finished ---")

# Example Usage:
# To run this script, save it as a .py file (e.g., adobe_security_scraper.py)
# and execute it from your terminal: python adobe_security_scraper.py

# Define the URLs to scrape
# Only include URLs that are known to contain structured security bulletins
# for Adobe Commerce/Magento in a parseable format.
# The following URLs are supported by the current scraping logic.
urls_to_scrape = [
    'https://helpx.adobe.com/security/products/magento.html',
    'https://helpx.adobe.com/security.html',
    'https://devdocs.magento.com/guides/v2.4/release-notes/bk-release-notes.html',
    'https://support.magento.com/hc/en-us/sections/360010506631-Security-patches',
    'https://magento.com/security/patches',
    'https://experienceleague.adobe.com/docs/commerce-operations/installation-guide/tutorials/extensions.html'
]

# Define the date range
# You can change these dates as needed
from_date_input = "2025-01-01" # Example: A past date to get more results
to_date_input = datetime.now().strftime('%Y-%m-%d') # Today's date

# Example of how to call the function:
adobe_commerce_security_scraper(urls_to_scrape, from_date_input, to_date_input)
