Prompt for all:

Build a Python script called "Adobe Commerce Security Scraper".

**Purpose:**
The script should scrape Adobe's official security bulletin web pages to find and list Adobe Commerce (Magento) security patches or updates published between a given "from_date" and "to_date".

**Inputs:**
- A list of URLs (e.g., Adobe Commerce security bulletin pages)
- A from_date (e.g., January 1, 2025)
- A to_date (e.g., today's date)

**Functionality:**
- For each URL:
  - Scrape the page for bulletins or advisories related to Adobe Commerce (look for links containing "apsb" or pages about security updates).
  - Extract:
    - Patch title or summary
    - Publication date
    - URL of the bulletin
- Filter the patches so only those **within the specified date range** are included.
- Output a readable list showing:
  - Date
  - Title
  - Link

**Example use case:**
If I run the script with URLs pointing to Adobe's Magento and general security bulletin pages, and with `from_date = 2025-01-01`, I should get a list of Adobe Commerce patches published between January 1, 2025, and today, each with its publication date and a link to read more.

The output should be simple and clean, just a list printed in the console.

No need for saving to a file or using command-line arguments in the first version.

Please use `requests` and `BeautifulSoup` for scraping. Make sure the code works with real Adobe URLs such as:
- https://helpx.adobe.com/security/products/magento.html
- https://helpx.adobe.com/security.html
- https://devdocs.magento.com/guides/v2.4/release-notes/bk-release-notes.html
- https://support.magento.com/hc/en-us/sections/360010506631-Security-patches
- https://magento.com/security/patches
- https://experienceleague.adobe.com/docs/commerce-operations/installation-guide/tutorials/extensions.html
