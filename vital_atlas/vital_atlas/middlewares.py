"""
Scrapy middlewares for vital_atlas project
"""

from scrapy import signals


class VitalAtlasSpiderMiddleware:
    """
    Spider middleware for handling spider input and output.
    """

    @classmethod
    def from_crawler(cls, crawler):
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        return None

    async def process_spider_output(self, response, result, spider):
        async for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        pass

    async def process_start(self, start, spider):
        """Process the start requests from the spider."""
        async for r in start:
            yield r

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)
