#!/usr/bin/env python3
"""
Adobe Commerce Security Scraper

This script scrapes Adobe's official security bulletin web pages to find and list 
Adobe Commerce (Magento) security patches or updates published between specified dates.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, date
import re
import time
from urllib.parse import urljoin, urlparse
import sys

class AdobeCommerceSecurityScraper:
    def __init__(self):
        self.session = requests.Session()
        # Set a user agent to avoid being blocked
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.patches = []

    def parse_date(self, date_str):
        """Parse various date formats commonly used in Adobe bulletins"""
        if not date_str:
            return None
        
        # Clean the date string
        date_str = date_str.strip()
        
        # Common date formats
        date_formats = [
            '%B %d, %Y',      # January 1, 2025
            '%b %d, %Y',      # Jan 1, 2025
            '%Y-%m-%d',       # 2025-01-01
            '%m/%d/%Y',       # 01/01/2025
            '%d/%m/%Y',       # 01/01/2025
            '%Y/%m/%d',       # 2025/01/01
            '%B %Y',          # January 2025
            '%b %Y',          # Jan 2025
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        # Try to extract date with regex
        date_patterns = [
            r'(\w+ \d{1,2}, \d{4})',  # January 1, 2025
            r'(\d{4}-\d{2}-\d{2})',   # 2025-01-01
            r'(\d{1,2}/\d{1,2}/\d{4})', # 01/01/2025
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, date_str)
            if match:
                try:
                    return self.parse_date(match.group(1))
                except:
                    continue
        
        return None

    def scrape_adobe_security_page(self, url):
        """Scrape Adobe security pages for Commerce/Magento bulletins"""
        try:
            print(f"Scraping: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for security bulletins related to Commerce/Magento
            bulletins = []
            
            # Find links that contain APSB (Adobe Product Security Bulletin)
            apsb_links = soup.find_all('a', href=re.compile(r'apsb', re.I))
            
            for link in apsb_links:
                href = link.get('href')
                if href:
                    full_url = urljoin(url, href)
                    text = link.get_text(strip=True)
                    
                    # Check if it's related to Commerce/Magento
                    if any(keyword in text.lower() for keyword in ['commerce', 'magento']):
                        bulletins.append({
                            'title': text,
                            'url': full_url,
                            'date_text': ''
                        })
            
            # Look for table rows or list items with security information
            for row in soup.find_all(['tr', 'li', 'div']):
                text = row.get_text(strip=True)
                if any(keyword in text.lower() for keyword in ['commerce', 'magento']) and \
                   any(sec_keyword in text.lower() for sec_keyword in ['security', 'patch', 'update', 'bulletin', 'apsb']):
                    
                    # Try to find a link within this element
                    link = row.find('a')
                    if link and link.get('href'):
                        href = link.get('href')
                        full_url = urljoin(url, href)
                        
                        # Try to extract date from the row
                        date_match = re.search(r'(\w+ \d{1,2}, \d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})', text)
                        date_text = date_match.group(1) if date_match else ''
                        
                        bulletins.append({
                            'title': link.get_text(strip=True) or text[:100],
                            'url': full_url,
                            'date_text': date_text
                        })
            
            return bulletins
            
        except requests.RequestException as e:
            print(f"Error scraping {url}: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error scraping {url}: {e}")
            return []

    def scrape_bulletin_details(self, bulletin_url):
        """Scrape individual bulletin page for more details"""
        try:
            response = self.session.get(bulletin_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for publication date
            date_text = ''
            
            # Common selectors for dates in Adobe bulletins
            date_selectors = [
                'time',
                '.date',
                '.publish-date',
                '.publication-date',
                '[class*="date"]'
            ]
            
            for selector in date_selectors:
                date_element = soup.select_one(selector)
                if date_element:
                    date_text = date_element.get_text(strip=True)
                    break
            
            # If no date found, look in the text
            if not date_text:
                text = soup.get_text()
                date_match = re.search(r'(?:published|updated|released).*?(\w+ \d{1,2}, \d{4})', text, re.I)
                if date_match:
                    date_text = date_match.group(1)
            
            return date_text
            
        except Exception as e:
            print(f"Error getting details from {bulletin_url}: {e}")
            return ''

    def scrape_urls(self, urls, from_date, to_date):
        """Scrape multiple URLs and collect patches within date range"""
        print(f"Searching for Adobe Commerce security patches from {from_date} to {to_date}")
        print("=" * 70)
        
        all_bulletins = []
        
        for url in urls:
            bulletins = self.scrape_adobe_security_page(url)
            all_bulletins.extend(bulletins)
            time.sleep(1)  # Be respectful to the server
        
        # Process bulletins and filter by date
        filtered_patches = []
        
        for bulletin in all_bulletins:
            # If we don't have a date, try to get it from the bulletin page
            if not bulletin['date_text']:
                bulletin['date_text'] = self.scrape_bulletin_details(bulletin['url'])
                time.sleep(1)  # Be respectful
            
            # Parse the date
            patch_date = self.parse_date(bulletin['date_text'])
            
            if patch_date and from_date <= patch_date <= to_date:
                filtered_patches.append({
                    'date': patch_date,
                    'title': bulletin['title'],
                    'url': bulletin['url']
                })
        
        # Remove duplicates and sort by date
        unique_patches = []
        seen_urls = set()
        
        for patch in filtered_patches:
            if patch['url'] not in seen_urls:
                unique_patches.append(patch)
                seen_urls.add(patch['url'])
        
        # Sort by date (newest first)
        unique_patches.sort(key=lambda x: x['date'], reverse=True)
        
        return unique_patches

    def print_results(self, patches):
        """Print the results in a clean format"""
        if not patches:
            print("No Adobe Commerce security patches found in the specified date range.")
            return
        
        print(f"\nFound {len(patches)} Adobe Commerce security patch(es):")
        print("=" * 70)
        
        for patch in patches:
            print(f"Date: {patch['date'].strftime('%B %d, %Y')}")
            print(f"Title: {patch['title']}")
            print(f"Link: {patch['url']}")
            print("-" * 50)

def main():
    # Configuration
    urls = [
        "https://helpx.adobe.com/security/products/magento.html",
        "https://helpx.adobe.com/security.html",
        # Note: Some URLs might be outdated or require different scraping approaches
        # "https://devdocs.magento.com/guides/v2.4/release-notes/bk-release-notes.html",
        # "https://support.magento.com/hc/en-us/sections/360010506631-Security-patches",
        # "https://magento.com/security/patches",
        # "https://experienceleague.adobe.com/docs/commerce-operations/installation-guide/tutorials/extensions.html"
    ]
    
    # Date range
    from_date = date(2025, 1, 1)  # January 1, 2025
    to_date = date.today()        # Today's date
    
    # Create scraper and run
    scraper = AdobeCommerceSecurityScraper()
    
    try:
        patches = scraper.scrape_urls(urls, from_date, to_date)
        scraper.print_results(patches)
        
    except KeyboardInterrupt:
        print("\nScraping interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
