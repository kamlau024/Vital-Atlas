#!/usr/bin/env python
"""
Investigate cancer.ca structure to understand:
1. How to distinguish navigation pages from content pages
2. HTML structure and content extraction
3. Metadata availability
"""

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json

# Test URLs at different levels
test_urls = {
    "top_level_nav": [
        "https://cancer.ca/en/living-with-cancer",
        "https://cancer.ca/en/cancer-information",
        "https://cancer.ca/en/treatments"
    ],
    "mid_level_nav": [
        "https://cancer.ca/en/living-with-cancer/coping-with-changes",
        "https://cancer.ca/en/cancer-information/cancer-types",
        "https://cancer.ca/en/treatments/treatment-types"
    ],
    "content_pages": [
        "https://cancer.ca/en/living-with-cancer/coping-with-changes/newly-diagnosed",
        "https://cancer.ca/en/cancer-information/cancer-types/breast",
        "https://cancer.ca/en/treatments/treatment-types/chemotherapy"
    ]
}

def analyze_page(url, category):
    """Fetch and analyze a single page"""
    print(f"\n{'='*80}")
    print(f"Analyzing: {url}")
    print(f"Category: {category}")
    print(f"{'='*80}\n")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)
        page.wait_for_load_state('networkidle')
        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, 'html.parser')

    # 1. Find main content area
    main_selectors = ['main', 'article', '[role="main"]', '.main-content', '#main-content']
    main_content = None
    main_selector_used = None

    for selector in main_selectors:
        main_content = soup.select_one(selector)
        if main_content:
            main_selector_used = selector
            break

    print(f"Main content selector: {main_selector_used}")

    if not main_content:
        print("WARNING: No main content found!")
        return

    # 2. Analyze headings
    headings = {
        'h1': main_content.find_all('h1'),
        'h2': main_content.find_all('h2'),
        'h3': main_content.find_all('h3'),
        'h4': main_content.find_all('h4')
    }

    print(f"\nHeading structure:")
    for level, tags in headings.items():
        print(f"  {level.upper()}: {len(tags)} found")
        for i, tag in enumerate(tags[:3]):  # Show first 3
            print(f"    - {tag.get_text(strip=True)[:60]}")
        if len(tags) > 3:
            print(f"    ... and {len(tags) - 3} more")

    # 3. Count paragraphs
    paragraphs = main_content.find_all('p')
    print(f"\nParagraphs: {len(paragraphs)}")

    # 4. Check for navigation lists
    nav_lists = main_content.find_all(['nav', 'ul', 'ol'])
    print(f"Lists/Nav elements: {len(nav_lists)}")

    # 5. Estimate content vs navigation ratio
    total_text = main_content.get_text(strip=True)
    word_count = len(total_text.split())
    print(f"\nTotal words in main content: {word_count}")

    # 6. Look for metadata
    print(f"\nMetadata search:")

    # Title
    title = soup.find('h1')
    if title:
        print(f"  Title (h1): {title.get_text(strip=True)}")

    # Meta tags
    meta_description = soup.find('meta', {'name': 'description'})
    if meta_description:
        print(f"  Meta description: {meta_description.get('content', '')[:60]}...")

    # Look for dates
    date_patterns = ['last-updated', 'published', 'modified', 'date']
    for pattern in date_patterns:
        date_elem = soup.find(class_=lambda x: x and pattern in x.lower() if x else False)
        if date_elem:
            print(f"  Date element ({pattern}): {date_elem.get_text(strip=True)[:60]}")

    # 7. Check for breadcrumbs
    breadcrumb_selectors = ['nav[aria-label*="breadcrumb"]', '.breadcrumb', '[class*="breadcrumb"]']
    for selector in breadcrumb_selectors:
        breadcrumbs = soup.select(selector)
        if breadcrumbs:
            print(f"\nBreadcrumbs found with selector: {selector}")
            for bc in breadcrumbs[:1]:  # Show first one
                links = bc.find_all('a')
                print(f"  Breadcrumb items: {len(links)}")
                for link in links[:5]:
                    print(f"    - {link.get_text(strip=True)}")

    # 8. Save sample HTML for inspection
    filename = url.split('/')[-1] or 'index'
    with open(f'/tmp/cancer_ca_{category}_{filename}.html', 'w') as f:
        f.write(str(main_content))
    print(f"\nSaved HTML to: /tmp/cancer_ca_{category}_{filename}.html")

    # 9. Heuristic: Is this a navigation page or content page?
    is_nav_page = False
    reasons = []

    if word_count < 300:
        is_nav_page = True
        reasons.append(f"Low word count ({word_count} < 300)")

    if len(paragraphs) < 3:
        is_nav_page = True
        reasons.append(f"Few paragraphs ({len(paragraphs)} < 3)")

    nav_link_count = len(main_content.find_all('a'))
    if nav_link_count > word_count / 10:  # More than 1 link per 10 words
        is_nav_page = True
        reasons.append(f"High link density ({nav_link_count} links, {word_count} words)")

    print(f"\n{'='*40}")
    if is_nav_page:
        print("ASSESSMENT: Navigation page (SKIP)")
        print("Reasons:")
        for reason in reasons:
            print(f"  - {reason}")
    else:
        print("ASSESSMENT: Content page (SCRAPE)")
    print(f"{'='*40}")

# Run analysis
for category, urls in test_urls.items():
    for url in urls:
        try:
            analyze_page(url, category)
        except Exception as e:
            print(f"ERROR analyzing {url}: {e}")
        print("\n" * 2)

print("\n" + "="*80)
print("INVESTIGATION COMPLETE")
print("="*80)
print("\nNext steps:")
print("1. Review saved HTML files in /tmp/cancer_ca_*.html")
print("2. Determine heuristics for navigation vs content pages")
print("3. Design content extraction selectors")
