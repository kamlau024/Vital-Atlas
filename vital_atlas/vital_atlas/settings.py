"""
Scrapy settings for vital_atlas project
"""

BOT_NAME = "vital_atlas"

SPIDER_MODULES = ["vital_atlas.spiders"]
NEWSPIDER_MODULE = "vital_atlas.spiders"

# Crawl responsibly by identifying yourself (and your website) on the user-agent
USER_AGENT = "VitalAtlas/1.0 (+https://github.com/yourusername/vital-atlas)"

# Obey robots.txt rules
ROBOTSTXT_OBEY = True

# Configure maximum concurrent requests
CONCURRENT_REQUESTS = 8
CONCURRENT_REQUESTS_PER_DOMAIN = 4

# Configure a delay for requests for the same website
DOWNLOAD_DELAY = 2  # 2 seconds delay between requests to be respectful

# Disable cookies (enabled by default)
COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
TELNETCONSOLE_ENABLED = False

# Override the default request headers:
DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Enable or disable spider middlewares
# SPIDER_MIDDLEWARES = {
#     "vital_atlas.middlewares.VitalAtlasSpiderMiddleware": 543,
# }

# Enable or disable downloader middlewares
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}

TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

# Playwright settings
PLAYWRIGHT_BROWSER_TYPE = "chromium"
PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": True,
}

# Configure item pipelines
ITEM_PIPELINES = {
    "vital_atlas.pipelines.MetadataExtractionPipeline": 100,
    "vital_atlas.pipelines.HtmlToMarkdownPipeline": 200,
    "vital_atlas.pipelines.FileStoragePipeline": 300,
}

# Enable and configure HTTP caching (disabled by default)
HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 86400  # 24 hours
HTTPCACHE_DIR = "httpcache"
HTTPCACHE_IGNORE_HTTP_CODES = [500, 502, 503, 504, 408, 429]
HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"

# Configure logging
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
LOG_DATEFORMAT = "%Y-%m-%d %H:%M:%S"

# Custom settings
SCRAPED_DATA_DIR = "../scraped_data"
