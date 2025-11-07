# Vital Atlas - BC Cancer Health Info Web Scraper

## Project Overview

Vital Atlas is a web scraping application designed to crawl and extract health information articles from the BC Cancer Agency's website (bccancer.bc.ca). The scraped content will be converted to Markdown format and used to build a RAG (Retrieval-Augmented Generation) pipeline for an AI-based health information application.

## Target Website

- **Base URL**: https://www.bccancer.bc.ca/health-info
- **Content Type**: Health information articles organized in a hierarchical structure
- **Update Frequency**: Articles are periodically updated with revision dates

## Core Requirements

### 1. Web Scraping
- Crawl all articles under the `/health-info` section of bccancer.bc.ca
- Navigate through the hierarchical article structure
- Follow internal links to discover all available articles

### 2. Markdown Conversion
- Convert HTML articles to Markdown format
- Preserve the original HTML information hierarchy (headings, lists, tables, etc.)
- Maintain content structure and formatting as closely as possible

### 3. Metadata Capture
Each scraped article must capture the following metadata:
- **URL**: Original article URL
- **Date of Last Update**: When the article was last modified
- **Date of Next Review**: When the article is scheduled for review
- **Sidebar Links**: Links to related articles found in sidebars
- **Images**: URLs of all images in the article
- **Additional metadata**: Any other relevant fields found in the article

### 4. Change Detection & Scheduling
- Run scraper on a schedule (frequency TBD)
- Detect new articles that have been added
- Detect updates to existing articles (based on last update date or content changes)
- Maintain a library of the most up-to-date content

### 5. Storage
- Store markdown files in an organized local filesystem structure
- Mirror or reflect the hierarchical organization of the source website
- Include metadata in frontmatter or separate metadata files

## Technology Stack

- **Language**: Python
- **Scraping Framework**: Scrapy and/or BeautifulSoup (with requests/httpx)
- **HTML to Markdown**: html2text, markdownify, or similar libraries
- **Scheduling**: APScheduler, Celery, or cron jobs
- **Storage**: Local filesystem with organized directory structure

## Downstream Use Case

The scraped markdown files and metadata will feed into a RAG (Retrieval-Augmented Generation) pipeline to power an AI-based health information application. The quality and structure of the markdown conversion is critical for:
- Effective document chunking
- Semantic search and retrieval
- Maintaining context and hierarchy in AI responses

## Success Criteria

1. All articles from the health-info section are successfully scraped
2. Markdown output accurately represents the original HTML structure
3. All required metadata fields are captured
4. The scraper can run on a schedule and detect changes
5. The markdown files are suitable for RAG pipeline ingestion

## Development Approach

- Ask clarification questions whenever requirements are unclear
- Ensure 100% certainty of intention before implementing features
- Build incrementally with testing at each stage
- Prioritize data quality and accuracy over speed

## Notes

- The BC Cancer website may have terms of service or robots.txt that should be respected
- Rate limiting should be implemented to avoid overwhelming the source server
- Error handling should be robust to handle network issues, page structure changes, etc.
