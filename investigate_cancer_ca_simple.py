#!/usr/bin/env python
"""
Simpler investigation using requests to check if content is server-rendered
"""

import requests
from bs4 import BeautifulSoup

# Test just a few URLs
test_urls = [
    ("nav", "https://cancer.ca/en/living-with-cancer"),
    ("nav", "https://cancer.ca/en/living-with-cancer/coping-with-changes"),
    ("content", "https://cancer.ca/en/living-with-cancer/coping-with-changes/newly-diagnosed"),
    ("content", "https://cancer.ca/en/cancer-information/cancer-types/breast"),
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
}

for category, url in test_urls:
    print(f"\n{'='*80}")
    print(f"Fetching: {url}")
    print(f"Category: {category}")
    print(f"{'='*80}\n")

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Check if content is present
        body_text = soup.get_text()
        if len(body_text.strip()) < 100:
            print("WARNING: Very little text content - might be JavaScript-rendered")
            print(f"Body text length: {len(body_text)}")
            continue

        # Find main content
        main = soup.find('main') or soup.find('article') or soup.find(id='main')

        if main:
            print(f"✓ Found main content area")

            # Headings
            h1 = main.find('h1')
            if h1:
                print(f"  H1: {h1.get_text(strip=True)}")

            h2s = main.find_all('h2')
            print(f"  H2 count: {len(h2s)}")
            if h2s:
                for h2 in h2s[:3]:
                    print(f"    - {h2.get_text(strip=True)[:60]}")

            # Paragraphs
            paragraphs = main.find_all('p')
            print(f"  Paragraphs: {len(paragraphs)}")

            # Word count
            text = main.get_text(strip=True)
            words = len(text.split())
            print(f"  Word count: {words}")

            # Links
            links = main.find_all('a')
            print(f"  Links: {len(links)}")

            # Save sample
            filename = url.split('/')[-1] or 'index'
            filepath = f'/tmp/cancer_ca_{category}_{filename}.html'
            with open(filepath, 'w') as f:
                f.write(str(main.prettify()))
            print(f"\n  Saved to: {filepath}")

            # Assessment
            print(f"\n  Assessment:")
            if words < 300 or len(paragraphs) < 3:
                print(f"    → Likely NAVIGATION page (words:{words}, paragraphs:{len(paragraphs)})")
            else:
                print(f"    → Likely CONTENT page (words:{words}, paragraphs:{len(paragraphs)})")
        else:
            print("✗ Could not find main content area")
            print(f"  Total body text length: {len(body_text)}")

    except requests.RequestException as e:
        print(f"ERROR: {e}")

print("\n" + "="*80)
print("Investigation complete - check /tmp/cancer_ca_*.html files")
print("="*80)
