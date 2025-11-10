# Cancer.ca Site Structure Investigation - Summary

## Key Findings

### 1. Content is Server-Rendered ✓
- **No need for Playwright** - can use simple HTTP requests with BeautifulSoup
- Much faster and more reliable than BC Cancer scraping
- All content is in the initial HTML response

### 2. Page Structure

**Main Content Container:**
```html
<main class="site-main" id="main-content">
```

**Hero Section (contains title):**
```html
<section class="hero">
  <div class="hero__header">
    <h1 class="title">Page Title</h1>
  </div>
</section>
```

**Breadcrumbs:**
```html
<ol class="breadcrumb__list" itemscope itemtype="https://schema.org/BreadcrumbList">
  <li class="breadcrumb__item">
    <span class="breadcrumb__text">Home</span>
  </li>
  ...
</ol>
```
- Uses schema.org structured data
- Position metadata included
- Clean extraction possible

**Content Sections:**
- Navigation pages: `<section class="cards-with-cta-list">` with card links
- Content pages: `<section class="section">` with `<div class="wysiwyg">` blocks
- Standard HTML structure: H1, H2, H3, P tags
- No accordions or tabs like BC Cancer

### 3. Navigation vs Content Pages

**Heuristics for Detection:**

| Metric | Navigation Page | Content Page |
|--------|----------------|--------------|
| Word Count | 300-500 | 900-1000+ |
| Paragraph Count | 4-9 | 10+ |
| Has `.cards-with-cta-list` | YES | NO |
| URL Depth | 2-3 segments | 3-4+ segments |

**Examples:**
- **Navigation**: `/en/living-with-cancer` (474 words, 9 paragraphs)
- **Navigation**: `/en/living-with-cancer/coping-with-changes` (387 words, 7 paragraphs)
- **Content**: `/en/living-with-cancer/coping-with-changes/newly-diagnosed` (971 words, 13 paragraphs)
- **Content**: `/en/cancer-information/cancer-types/breast` (529 words, 4 paragraphs)

**Recommended Approach:**
- Use URL depth: Skip pages with only 2 path segments (e.g., `/en/living-with-cancer`)
- Scrape pages with 3+ segments (e.g., `/en/living-with-cancer/coping-with-changes/newly-diagnosed`)
- Additional filter: Require minimum 500 words OR absence of `.cards-with-cta-list`

### 4. Metadata Availability

**Available:**
- ✓ Title (H1 in hero section)
- ✓ Breadcrumbs (structured data)
- ✓ Images (with srcset for responsive images)
- ✓ Content structure (clean H1-H4 hierarchy)

**NOT Available (set to null):**
- ✗ Date last updated
- ✗ Date next review
- ✗ Explicit tags/categories

**Metadata Extraction Plan:**
- Title: `.hero h1.title`
- Breadcrumbs: `ol.breadcrumb__list span.breadcrumb__text`
- Images: `img` tags within main content
- Categories: Derive from URL path

### 5. Content Extraction Strategy

**Simple Approach:**
1. Extract `<main id="main-content">`
2. Remove:
   - Breadcrumb navigation (`.breadcrumb`)
   - Card navigation lists (`.cards-with-cta-list`)
   - Print buttons
3. Keep:
   - Hero section with title
   - All `.section` blocks
   - All `.wysiwyg` content blocks
   - Standard HTML elements (h1-h6, p, ul, ol, tables)

**No Special Processing Needed:**
- No tab content markers
- No accordion headings to promote
- No TOC lists to remove
- Standard markdown conversion should work well

### 6. URL Patterns

**Target Sections:**
- `/en/cancer-information/**`
- `/en/treatments/**`
- `/en/living-with-cancer/**`

**Exclude Patterns:**
- `/en/get-involved/**`
- `/en/about-us/**`
- `/en/research/**`
- Pages with only 2 path segments (navigation pages)

### 7. Differences from BC Cancer

| Feature | BC Cancer | Cancer.ca |
|---------|-----------|-----------|
| Rendering | JavaScript (Playwright needed) | Server-side (simple HTTP) |
| Content Structure | Tabs, accordions, complex | Standard HTML hierarchy |
| Metadata | Dates available | Dates not available |
| TOC Lists | Need removal | Not present |
| Special Cleanup | Yes (Tab Content, accordions) | No |
| Navigation Detection | URL pattern only | Multiple heuristics needed |

## Recommendations

### Spider Configuration
```python
name = "canadian_cancer_society"
allowed_domains = ["cancer.ca"]
start_urls = [
    "https://cancer.ca/en/cancer-information",
    "https://cancer.ca/en/treatments",
    "https://cancer.ca/en/living-with-cancer"
]

# No Playwright needed - use standard HTTP middleware
custom_settings = {
    'SCRAPED_DATA_DIR': '../scraped_data/canadian-cancer-society',
    'DOWNLOAD_DELAY': 1,  # Be polite
}
```

### URL Filtering
```python
def _is_article_url(self, url):
    """Content pages have 3+ path segments"""
    path = url.split('cancer.ca')[-1]
    segments = [s for s in path.split('/') if s and s != 'en']

    # Need at least 3 segments (section/subsection/page)
    # e.g., /cancer-information/cancer-types/breast
    return len(segments) >= 3
```

### Content Extraction
```python
def _extract_main_content(self, response):
    """Extract main content - simpler than BC Cancer"""
    from bs4 import BeautifulSoup

    main = response.css('main#main-content').get()
    soup = BeautifulSoup(main, 'html.parser')

    # Remove navigation elements
    for selector in ['.breadcrumb', '.cards-with-cta-list', '.breadcrumb__print']:
        for elem in soup.select(selector):
            elem.decompose()

    return str(soup)
```

### HTML to Markdown
- Use base `HTMLToMarkdownConverter` WITHOUT BC Cancer cleanup methods
- No need for:
  - `_remove_page_markers()`
  - `_promote_accordion_headings()`
  - Tab content processing
- Keep:
  - `_convert_relative_urls()`
  - `_remove_excessive_newlines()`
  - `_clean_whitespace()`

## Next Steps

1. ✅ Investigation complete
2. Create simple CCS-specific HTML to Markdown converter
3. Implement CCS metadata extractor (with null dates)
4. Build CCS spider with URL depth filtering
5. Test with small scrape (10-20 pages)
6. Verify markdown quality
