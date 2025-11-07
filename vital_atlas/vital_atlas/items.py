import scrapy


class ArticleItem(scrapy.Item):
    """
    Data structure for scraped health information articles.
    """
    # URL and identification
    url = scrapy.Field()
    title = scrapy.Field()

    # Content
    content_markdown = scrapy.Field()
    content_html = scrapy.Field()  # Keep original HTML as backup

    # Metadata
    date_scraped = scrapy.Field()
    date_last_update = scrapy.Field()
    date_next_review = scrapy.Field()

    # Navigation and relationships
    breadcrumbs = scrapy.Field()
    sidebar_links = scrapy.Field()
    related_articles = scrapy.Field()

    # Media
    images = scrapy.Field()  # List of image URLs

    # Additional metadata
    page_type = scrapy.Field()
    categories = scrapy.Field()
    tags = scrapy.Field()

    # Storage path
    file_path = scrapy.Field()
