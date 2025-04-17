# website_1_crawler

A Scrapy-based crawler that extracts metadata, attachments, html, and geospatial visualizations from project pages on [uvp-verbund.de](https://www.uvp-verbund.de/).  
Designed as the first part of the BASF assignment for crawling.

## Features

- Crawls project reports from paginated search results
- Extracts:
  - Metadata (title, description, dates, categories ...)
  - All PDF attachments (unzipped from ZIP attachments)
  - Raumbezug map (screenshot of project geolocation)
  - Full HTML source per project
- Organizes data in a clear directory structure:
  ```
  data/
  ├──page_<index>/
     ├── project_<index>/
         ├── metadata.json
         ├── Source.html
         ├── Raumbezug.jpg
         └── attachment/
             └── *.pdf / ...
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

- `spiders/website_1_spider.py` — main crawling logic and attachment downloading
- `pipelines.py` — handles metadata saving, html and screenshot generation
- `settings.py` — Scrapy configuration settings

## Notes

- This crawler uses Selenium to capture geospatial map screenshots and full html content.
- ZIP files are extracted automatically unless empty or malformed.
- Currently supports "Zulassungsverfahren", "Negative Vorprüfung", "Linienbestimmungen nach § 16 Bundesfernstraßengesetz oder Landesstraßenrecht", "Raumordnungsverfahren nach ROG mit UVP", and "Ausländische Vorhaben" report types.
- Make sure to update the `SELENIUM_DRIVER_EXECUTABLE_PATH` in `settings.py` to match the path of your own ChromeDriver installation (default is `/usr/local/bin/chromedriver`).