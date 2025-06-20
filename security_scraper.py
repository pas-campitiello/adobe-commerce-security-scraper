#!/usr/bin/env python3
"""
Adobe Commerce Security Bulletin Scraper

This script automatically scrapes Adobe Commerce security bulletins weekly
and generates markdown reports with relevant security information.
"""

import requests
import trafilatura
from bs4 import BeautifulSoup
import schedule
import time
import re
import logging
from datetime import datetime, timedelta
from pathlib import Path
import json
from typing import List, Dict, Optional
from config import URLS, KEYWORDS, OUTPUT_FILE, LOG_FILE
from utils import setup_logging, retry_request, parse_date, clean_text

class SecurityScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.logger = logging.getLogger(__name__)
        
    def scrape_adobe_security_page(self, url: str) -> List[Dict]:
        """Scrape Adobe security page for relevant bulletins"""
        try:
            self.logger.info(f"Scraping Adobe security page: {url}")
            
            # Get page content using trafilatura
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                self.logger.error(f"Failed to download content from {url}")
                return []
            
            # Extract text content
            text_content = trafilatura.extract(downloaded)
            
            # Also get HTML for structured parsing
            response = retry_request(self.session, url)
            if not response:
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            bulletins = []
            
            # Look for security bulletin entries
            # Adobe security page typically has entries in specific structures
            security_entries = soup.find_all(['article', 'div', 'section'], 
                                           class_=re.compile(r'(bulletin|security|advisory)', re.I))
            
            if not security_entries:
                # Fallback: look for any elements containing security keywords
                security_entries = soup.find_all(['div', 'article', 'section', 'li'], 
                                                string=re.compile(r'(adobe commerce|magento)', re.I))
            
            for entry in security_entries:
                title_elem = entry.find(['h1', 'h2', 'h3', 'h4', 'a'])
                if not title_elem:
                    continue
                    
                title = clean_text(title_elem.get_text())
                
                # Check if entry is relevant to Adobe Commerce/Magento
                entry_text = clean_text(entry.get_text().lower())
                if not any(keyword.lower() in entry_text for keyword in KEYWORDS):
                    continue
                
                # Extract link
                link = None
                link_elem = entry.find('a', href=True)
                if link_elem:
                    link = link_elem['href']
                    if link.startswith('/'):
                        link = f"https://helpx.adobe.com{link}"
                
                # Extract date
                date_text = self.extract_date_from_entry(entry)
                
                # Extract description
                description = self.extract_description_from_entry(entry, title)
                
                bulletin = {
                    'title': title,
                    'link': link or url,
                    'date': date_text,
                    'description': description,
                    'source': 'Adobe Security'
                }
                
                bulletins.append(bulletin)
                self.logger.info(f"Found security bulletin: {title}")
            
            return bulletins
            
        except Exception as e:
            self.logger.error(f"Error scraping Adobe security page {url}: {str(e)}")
            return []
    
    def scrape_release_notes_page(self, url: str) -> List[Dict]:
        """Scrape Adobe Commerce release notes for security information"""
        try:
            self.logger.info(f"Scraping release notes page: {url}")
            
            response = retry_request(self.session, url)
            if not response:
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            bulletins = []
            
            # Look for release entries with security content
            release_sections = soup.find_all(['section', 'div', 'article'], 
                                           class_=re.compile(r'(release|version|update)', re.I))
            
            for section in release_sections:
                # Look for security-related content within releases
                security_content = section.find_all(string=re.compile(r'(security|cve|patch|vulnerability)', re.I))
                
                if not security_content:
                    continue
                
                # Extract release title
                title_elem = section.find(['h1', 'h2', 'h3', 'h4'])
                if not title_elem:
                    continue
                
                title = clean_text(title_elem.get_text())
                
                # Extract version/date info
                date_text = self.extract_date_from_entry(section)
                
                # Extract security-related description
                description = self.extract_security_description(section)
                
                # Extract link
                link = None
                link_elem = section.find('a', href=True)
                if link_elem:
                    link = link_elem['href']
                    if link.startswith('/'):
                        link = f"https://experienceleague.adobe.com{link}"
                
                bulletin = {
                    'title': title,
                    'link': link or url,
                    'date': date_text,
                    'description': description,
                    'source': 'Release Notes'
                }
                
                bulletins.append(bulletin)
                self.logger.info(f"Found release note with security info: {title}")
            
            return bulletins
            
        except Exception as e:
            self.logger.error(f"Error scraping release notes page {url}: {str(e)}")
            return []
    
    def scrape_patches_page(self, url: str) -> List[Dict]:
        """Scrape Adobe Commerce patches page for security patches"""
        try:
            self.logger.info(f"Scraping patches page: {url}")
            
            response = retry_request(self.session, url)
            if not response:
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            bulletins = []
            
            # Look for patch entries
            patch_sections = soup.find_all(['div', 'section', 'article'], 
                                         class_=re.compile(r'(patch|quality|security)', re.I))
            
            for section in patch_sections:
                # Check for security-related patches
                section_text = clean_text(section.get_text().lower())
                if not any(keyword.lower() in section_text for keyword in KEYWORDS):
                    continue
                
                title_elem = section.find(['h1', 'h2', 'h3', 'h4'])
                if not title_elem:
                    continue
                
                title = clean_text(title_elem.get_text())
                
                # Extract date
                date_text = self.extract_date_from_entry(section)
                
                # Extract description
                description = self.extract_description_from_entry(section, title)
                
                # Extract link
                link = None
                link_elem = section.find('a', href=True)
                if link_elem:
                    link = link_elem['href']
                    if link.startswith('/'):
                        link = f"https://experienceleague.adobe.com{link}"
                
                bulletin = {
                    'title': title,
                    'link': link or url,
                    'date': date_text,
                    'description': description,
                    'source': 'Quality Patches'
                }
                
                bulletins.append(bulletin)
                self.logger.info(f"Found security patch: {title}")
            
            return bulletins
            
        except Exception as e:
            self.logger.error(f"Error scraping patches page {url}: {str(e)}")
            return []
    
    def extract_date_from_entry(self, entry) -> str:
        """Extract date from a bulletin entry"""
        # Look for various date patterns
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
            r'\d{2}/\d{2}/\d{4}',  # MM/DD/YYYY
            r'\d{1,2}\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}',
            r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}'
        ]
        
        entry_text = entry.get_text()
        for pattern in date_patterns:
            match = re.search(pattern, entry_text, re.I)
            if match:
                return parse_date(match.group())
        
        return datetime.now().strftime('%Y-%m-%d')
    
    def extract_description_from_entry(self, entry, title: str) -> str:
        """Extract description from a bulletin entry"""
        # Look for description in various elements
        desc_elem = entry.find(['p', 'div'], class_=re.compile(r'(description|summary|abstract)', re.I))
        
        if desc_elem:
            description = clean_text(desc_elem.get_text())
        else:
            # Fallback: use first paragraph or text content
            paragraphs = entry.find_all('p')
            if paragraphs:
                description = clean_text(paragraphs[0].get_text())
            else:
                # Use first 200 characters of entry text, excluding title
                entry_text = clean_text(entry.get_text())
                title_clean = clean_text(title)
                description = entry_text.replace(title_clean, '').strip()[:200]
        
        # Ensure description is 2-3 sentences
        sentences = re.split(r'[.!?]+', description)
        if len(sentences) > 3:
            description = '. '.join(sentences[:3]) + '.'
        
        return description or "Security update for Adobe Commerce."
    
    def extract_security_description(self, section) -> str:
        """Extract security-specific description from a section"""
        # Look for security-related content
        security_paragraphs = section.find_all('p', string=re.compile(r'(security|cve|vulnerability|patch)', re.I))
        
        if security_paragraphs:
            description = clean_text(security_paragraphs[0].get_text())
        else:
            # Look for lists or bullet points with security content
            security_items = section.find_all(['li', 'ul'], string=re.compile(r'(security|cve)', re.I))
            if security_items:
                description = clean_text(security_items[0].get_text())
            else:
                description = "Contains security updates and fixes."
        
        # Ensure proper length
        sentences = re.split(r'[.!?]+', description)
        if len(sentences) > 3:
            description = '. '.join(sentences[:3]) + '.'
        
        return description
    
    def scrape_all_sources(self) -> List[Dict]:
        """Scrape all configured sources for security bulletins"""
        all_bulletins = []
        
        for url_info in URLS:
            url = url_info['url']
            source_type = url_info['type']
            
            try:
                if source_type == 'security':
                    bulletins = self.scrape_adobe_security_page(url)
                elif source_type == 'release_notes':
                    bulletins = self.scrape_release_notes_page(url)
                elif source_type == 'patches':
                    bulletins = self.scrape_patches_page(url)
                else:
                    self.logger.warning(f"Unknown source type: {source_type}")
                    continue
                
                all_bulletins.extend(bulletins)
                
            except Exception as e:
                self.logger.error(f"Error scraping {url}: {str(e)}")
                continue
        
        # Remove duplicates based on title and link
        unique_bulletins = []
        seen = set()
        
        for bulletin in all_bulletins:
            key = (bulletin['title'], bulletin['link'])
            if key not in seen:
                seen.add(key)
                unique_bulletins.append(bulletin)
        
        return unique_bulletins
    
    def generate_markdown_report(self, bulletins: List[Dict]) -> str:
        """Generate markdown report from bulletins"""
        if not bulletins:
            return self.generate_empty_report()
        
        # Sort bulletins by date (newest first)
        sorted_bulletins = sorted(bulletins, 
                                key=lambda x: parse_date(x['date']), 
                                reverse=True)
        
        # Generate report
        report_date = datetime.now().strftime('%Y-%m-%d')
        
        markdown = f"""# Adobe Commerce Security Bulletin Weekly Report
Generated on: {report_date}

## Summary
Found {len(sorted_bulletins)} security-related items from Adobe Commerce sources.

## Security Items

"""
        
        for bulletin in sorted_bulletins:
            title = bulletin['title']
            link = bulletin['link']
            date = bulletin['date']
            description = bulletin['description']
            source = bulletin['source']
            
            markdown += f"""### [{title}]({link})
**Date:** {date}  
**Source:** {source}

{description}

---

"""
        
        markdown += f"""## Sources Monitored
- [Adobe Security](https://helpx.adobe.com/security.html)
- [Adobe Commerce Release Notes](https://experienceleague.adobe.com/docs/commerce-operations/release/release-notes/overview.html)
- [Adobe Commerce Quality Patches](https://experienceleague.adobe.com/docs/commerce-operations/upgrade/quality-patches/overview.html)

---
*Report generated automatically by Adobe Commerce Security Scraper*
"""
        
        return markdown
    
    def generate_empty_report(self) -> str:
        """Generate report when no security items are found"""
        report_date = datetime.now().strftime('%Y-%m-%d')
        
        return f"""# Adobe Commerce Security Bulletin Weekly Report
Generated on: {report_date}

## Summary
No new security-related items found this week from monitored Adobe Commerce sources.

## Sources Monitored
- [Adobe Security](https://helpx.adobe.com/security.html)
- [Adobe Commerce Release Notes](https://experienceleague.adobe.com/docs/commerce-operations/release/release-notes/overview.html)
- [Adobe Commerce Quality Patches](https://experienceleague.adobe.com/docs/commerce-operations/upgrade/quality-patches/overview.html)

---
*Report generated automatically by Adobe Commerce Security Scraper*
"""
    
    def save_report(self, report: str) -> None:
        """Save markdown report to file"""
        try:
            output_path = Path(OUTPUT_FILE)
            output_path.write_text(report, encoding='utf-8')
            self.logger.info(f"Report saved to {OUTPUT_FILE}")
            
            # Also create timestamped backup
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = f"weekly_security_report_{timestamp}.md"
            Path(backup_file).write_text(report, encoding='utf-8')
            self.logger.info(f"Backup report saved to {backup_file}")
            
        except Exception as e:
            self.logger.error(f"Error saving report: {str(e)}")
    
    def run_weekly_scrape(self) -> None:
        """Run the weekly scraping job"""
        self.logger.info("Starting weekly Adobe Commerce security scrape")
        
        try:
            # Scrape all sources
            bulletins = self.scrape_all_sources()
            
            # Generate report
            report = self.generate_markdown_report(bulletins)
            
            # Save report
            self.save_report(report)
            
            self.logger.info(f"Weekly scrape completed. Found {len(bulletins)} security items.")
            
        except Exception as e:
            self.logger.error(f"Error during weekly scrape: {str(e)}")

def main():
    """Main function to run the security scraper"""
    # Setup logging
    setup_logging()
    
    scraper = SecurityScraper()
    
    # Check if running as one-time execution or scheduling
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--now':
        # Run immediately
        scraper.run_weekly_scrape()
    elif len(sys.argv) > 1 and sys.argv[1] == '--schedule':
        # Schedule weekly runs
        schedule.every().monday.at("09:00").do(scraper.run_weekly_scrape)
        
        print("Adobe Commerce Security Scraper scheduled to run every Monday at 9:00 AM")
        print("Press Ctrl+C to stop the scheduler")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            print("\nScheduler stopped.")
    else:
        # Show usage
        print("Adobe Commerce Security Bulletin Scraper")
        print("\nUsage:")
        print("  python security_scraper.py --now       Run scraper immediately")
        print("  python security_scraper.py --schedule  Schedule weekly runs")
        print("\nThe scraper monitors Adobe Commerce security sources and generates weekly reports.")

if __name__ == "__main__":
    main()
