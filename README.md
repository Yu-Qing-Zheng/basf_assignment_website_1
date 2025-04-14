# website_1_crawler

A Scrapy-based crawler that extracts metadata, attachments, and geospatial visualizations from project pages on [uvp-verbund.de](https://www.uvp-verbund.de/).  
Designed as part of the BASF assignment for structured document scraping.

## Features

- Crawls project reports from paginated search results
- Extracts:
  - Metadata (title, description, dates, categories)
  - All PDF / ZIP attachments (with optional unzip)
  - Geolocation map (screenshot)
  - Full HTML source per project
- Organizes data in a clear directory structure:
  ```
  project_<index>/
  ├── metadata.json
  ├── Source.html
  ├── Raumbezug.jpg
  └── attachment/
      └── *.pdf / *.zip / ...
  ```

## Setup

Create a virtual environment and install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

To run the crawler:

```bash
scrapy crawl website_1
```

To output metadata as JSONL:

```bash
scrapy crawl website_1 -o output.jsonl
```

## Project Structure

- `spiders/website_1_spider.py` — main crawling logic
- `pipelines.py` — handles metadata saving, html and screenshot generation
- `settings.py` — Scrapy configuration settings

## Notes

- This crawler uses Selenium to capture geospatial map screenshots.
- ZIP files are extracted automatically unless empty or malformed.
- Currently supports "Zulassungsverfahren" and "Negative Vorprüfung" report types.
