#!/bin/bash

# Activate conda environment and run the scraper

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Vital Atlas Web Scraper ===${NC}"
echo ""

# Check if conda environment is activated
if [[ "$CONDA_DEFAULT_ENV" != "vital-atlas" ]]; then
    echo "Activating conda environment..."
    source "$(conda info --base)/etc/profile.d/conda.sh"
    conda activate vital-atlas
fi

# Change to project directory
cd vital_atlas

echo -e "${GREEN}Starting scraper...${NC}"
echo ""

# Run the scraper
scrapy crawl bc_cancer "$@"

echo ""
echo -e "${GREEN}Scraping complete!${NC}"
echo "Articles saved to: ../scraped_data/articles/"
echo "Metadata saved to: ../scraped_data/metadata/"
