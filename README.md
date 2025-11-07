# Vital Atlas - BC Cancer Health Info Web Scraper

A web scraping application that crawls and extracts health information articles from the BC Cancer Agency's website (bccancer.bc.ca), converting them to Markdown format for use in RAG (Retrieval-Augmented Generation) pipelines.

## Features

- **Comprehensive Crawling**: Automatically discovers and scrapes all articles under the `/health-info` section
- **Markdown Conversion**: Converts HTML to clean Markdown while preserving document structure
- **Metadata Extraction**: Captures URLs, dates, breadcrumbs, sidebar links, images, and more
- **Change Detection**: Tracks new and updated articles across scraping runs
- **JavaScript Support**: Uses Playwright to render JavaScript-heavy pages
- **Respectful Scraping**: Implements rate limiting and follows robots.txt

## Project Structure

```
Vital-Atlas/
├── vital_atlas/               # Main Scrapy project
│   ├── scrapy.cfg            # Scrapy configuration
│   └── vital_atlas/
│       ├── spiders/
│       │   └── bc_cancer_spider.py  # Main spider
│       ├── items.py          # Data structures
│       ├── pipelines.py      # Data processing pipelines
│       ├── settings.py       # Scrapy settings
│       └── middlewares.py    # Spider middlewares
├── utils/                    # Utility modules
│   ├── html_to_markdown.py  # HTML→Markdown converter
│   ├── metadata_extractor.py  # Metadata extraction
│   └── change_detector.py   # Change tracking
├── scraped_data/            # Output directory (created on first run)
│   ├── articles/            # Markdown files organized by URL structure
│   └── metadata/            # JSON metadata files
├── environment.yml          # Conda environment specification
├── .gitignore              # Git ignore rules
└── Claude.md               # Project context for Claude

```

## Setup

### 1. Create and Activate Conda Environment

```bash
conda env create -f environment.yml
conda activate vital-atlas
```

### 2. Install Playwright Browsers

Playwright requires browser binaries to be installed:

```bash
playwright install chromium
```

### 3. Verify Installation

```bash
cd vital_atlas
scrapy list
```

You should see `bc_cancer` in the output.

## Usage

### Running the Scraper

From the `vital_atlas` directory:

```bash
# Basic run
scrapy crawl bc_cancer

# Run with custom settings
scrapy crawl bc_cancer -s DOWNLOAD_DELAY=3

# Run with logging to file
scrapy crawl bc_cancer --logfile=scraper.log
```

### Output Structure

Scraped articles are saved in `scraped_data/`:

```
scraped_data/
├── articles/
│   └── health-info/
│       ├── types-of-cancer/
│       │   ├── breast-cancer.md
│       │   ├── lung.md
│       │   └── ...
│       └── coping-with-cancer/
│           ├── emotional-support.md
│           └── ...
└── metadata/
    ├── breast-cancer.json
    ├── lung.json
    ├── url_index.json      # URL to file mapping
    └── change_log.json     # Log of all changes
```

### Markdown File Format

Each article is saved as a Markdown file with YAML frontmatter:

```markdown
---
title: "Breast Cancer"
url: https://www.bccancer.bc.ca/health-info/types-of-cancer/breast-cancer
date_scraped: 2025-11-06T19:30:00
date_last_update: November 5, 2025
date_next_review: November 5, 2026
categories:
  - Health Info
  - Types Of Cancer
breadcrumbs:
  - text: "Home"
    url: https://www.bccancer.bc.ca/
  - text: "Health Info"
    url: https://www.bccancer.bc.ca/health-info
images:
  - src: https://www.bccancer.bc.ca/images/breast-diagram.jpg
    alt: "Breast anatomy diagram"
---

# Breast Cancer

Article content in Markdown format...
```

## Change Detection

The scraper automatically tracks changes between runs:

- **New Articles**: First-time discoveries are logged
- **Updated Content**: Changes to article content are detected via content hash
- **Metadata Changes**: Updates to titles, dates, and other metadata are tracked

View recent changes in `scraped_data/metadata/change_log.json`:

```json
[
  {
    "timestamp": "2025-11-06T19:30:00",
    "type": "new",
    "url": "https://www.bccancer.bc.ca/health-info/types-of-cancer/breast-cancer",
    "title": "Breast Cancer"
  },
  {
    "timestamp": "2025-11-06T19:35:00",
    "type": "updated",
    "url": "https://www.bccancer.bc.ca/health-info/types-of-cancer/lung",
    "title": "Lung Cancer"
  }
]
```

## Scheduling

To run the scraper on a schedule, you can use:

### Cron (Linux/Mac)

```bash
# Run daily at 2 AM
0 2 * * * cd /path/to/Vital-Atlas/vital_atlas && /path/to/conda/envs/vital-atlas/bin/scrapy crawl bc_cancer
```

### Task Scheduler (Windows)

Create a batch file and schedule it with Windows Task Scheduler.

### Python Script with APScheduler

```python
from apscheduler.schedulers.blocking import BlockingScheduler
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

def run_scraper():
    process = CrawlerProcess(get_project_settings())
    process.crawl('bc_cancer')
    process.start()

scheduler = BlockingScheduler()
scheduler.add_job(run_scraper, 'cron', hour=2)  # Run at 2 AM daily
scheduler.start()
```

## Configuration

Key settings in `vital_atlas/vital_atlas/settings.py`:

- `DOWNLOAD_DELAY`: Time between requests (default: 2 seconds)
- `CONCURRENT_REQUESTS`: Max concurrent requests (default: 8)
- `ROBOTSTXT_OBEY`: Respect robots.txt (default: True)
- `SCRAPED_DATA_DIR`: Output directory (default: ../scraped_data)

## Use with RAG Pipeline

The scraped Markdown files are optimized for RAG pipelines:

1. **Structured Content**: Clear hierarchy with headings and sections
2. **Rich Metadata**: Frontmatter includes all contextual information
3. **Clean Formatting**: Minimal noise, maximum signal
4. **Change Tracking**: Only process new/updated articles

Example integration with LangChain:

```python
from langchain.document_loaders import DirectoryLoader, UnstructuredMarkdownLoader

loader = DirectoryLoader(
    'scraped_data/articles/',
    glob="**/*.md",
    loader_cls=UnstructuredMarkdownLoader
)
documents = loader.load()
```

## Development

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black vital_atlas/
flake8 vital_atlas/
```

## Troubleshooting

### Playwright Issues

If Playwright fails to launch browsers:

```bash
playwright install chromium
```

### Permission Errors

Ensure the output directory is writable:

```bash
chmod -R 755 scraped_data/
```

### Rate Limiting

If you're being rate-limited, increase the download delay:

```bash
scrapy crawl bc_cancer -s DOWNLOAD_DELAY=5
```

## License

This project is for educational and research purposes. Please respect BC Cancer's terms of service and robots.txt when scraping.

## Contributing

Contributions are welcome! Please ensure all clarification questions are addressed before implementing features.
