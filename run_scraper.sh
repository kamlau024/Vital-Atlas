#!/bin/bash

# Activate conda environment and run the scraper

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Vital Atlas Web Scraper ===${NC}"
echo ""

# Get the script's directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to project directory
cd "$SCRIPT_DIR/vital_atlas"

echo -e "${GREEN}Starting scraper...${NC}"
echo ""

# Run the scraper using python -m scrapy
/opt/anaconda3/envs/vital-atlas/bin/python -m scrapy crawl bc_cancer "$@"

echo ""
echo -e "${GREEN}Scraping complete!${NC}"
echo "Articles saved to: ../scraped_data/articles/"
echo "Metadata saved to: ../scraped_data/metadata/"
