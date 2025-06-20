"""
Configuration file for Adobe Commerce Security Scraper
"""
import os
# URLs to monitor for security information
URLS = [
    {
        'url': 'https://helpx.adobe.com/security.html',
        'type': 'security'
    },
    {
        'url': 'https://experienceleague.adobe.com/docs/commerce-operations/release/release-notes/overview.html',
        'type': 'release_notes'
    },
    {
        'url': 'https://experienceleague.adobe.com/docs/commerce-operations/upgrade/quality-patches/overview.html',
        'type': 'patches'
    }
]
# Keywords to filter for relevant content
KEYWORDS = [
    'Adobe Commerce',
    'Magento',
    'Security',
    'Patch',
    'CVE',
    'Vulnerability',
    'Security Update',
    'Security Fix',
    'Security Advisory',
    'Security Bulletin',
    'APSB',
    'Commerce',
    'Security Patch'
]
# Output configuration
OUTPUT_FILE = 'weekly_security_report.md'
LOG_FILE = 'security_scraper.log'
# Request configuration
REQUEST_TIMEOUT = 10
MAX_RETRIES = 2
RETRY_DELAY = 2  # seconds
# User agent for requests
USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
# Logging configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'