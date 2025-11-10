#!/bin/bash

# Run Canadian Cancer Society scraper
# Usage: ./run_canadian_cancer_society.sh [URL] [scrapy options]
#   URL: Optional starting URL (overrides default start_urls)
#   Example: ./run_canadian_cancer_society.sh https://cancer.ca/en/cancer-information/resources/glossary

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Canadian Cancer Society Web Scraper ===${NC}"
echo ""

# Get the script's directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to project directory
cd "$SCRIPT_DIR/vital_atlas"

# Parse URL argument if provided
URL_ARG=""
SCRAPY_ARGS=()

# Check if first argument is a URL
if [[ $1 =~ ^https?:// ]]; then
    URL_ARG="-a url=$1"
    echo -e "${GREEN}Starting from custom URL: $1${NC}"
    shift  # Remove URL from arguments
fi

# Collect remaining arguments
SCRAPY_ARGS=("$@")

echo -e "${GREEN}Starting Canadian Cancer Society scraper...${NC}"
echo ""

# Run the scraper using python -m scrapy
/opt/anaconda3/envs/vital-atlas/bin/python -m scrapy crawl canadian_cancer_society $URL_ARG "${SCRAPY_ARGS[@]}"

echo ""
echo -e "${GREEN}Scraping complete!${NC}"
echo "Articles saved to: ../scraped_data/canadian-cancer-society/articles/"
echo "Metadata saved to: ../scraped_data/canadian-cancer-society/metadata/"
