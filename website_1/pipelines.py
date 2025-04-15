# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
from urllib.parse import urlparse
from pathlib import Path
import json

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service


class SaveJsonlPipeline:

    # def open_spider(self, spider):
    #     print(f"Starting crawling urls = '{spider.start_urls}'")

    # def close_spider(self, spider):
    #     print(f"Crawling finished.")

    def process_item(self, item, spider):

        try:
            # create page folder
            main_dir = Path('./data')
            page_id = item['Source_page']
            page_dir = main_dir / Path(f"page_{str(page_id)}")
            index = item['Eia_report_index']
            eia_report_index_dir = page_dir / Path(f"project_{str(index)}")
            eia_report_index_dir.mkdir(parents=True, exist_ok=True)

            # save metadata to json
            file_path = eia_report_index_dir / "metadata.json"
            with open (file_path, mode="w", encoding='utf-8') as f:
                json.dump(item, f, ensure_ascii=False, indent=2)
            spider.logger.info(f"Saved to {file_path}")
        except Exception as e:
            spider.logger.error(f"Failed to save JSON: {e}")

        return item
    
class SaveHtmlPipeline:

    @classmethod
    def from_crawler(cls, crawler):

        settings = crawler.settings
        executable_path = settings.get("SELENIUM_DRIVER_EXECUTABLE_PATH")
        driver_args = settings.getlist("SELENIUM_DRIVER_ARGUMENTS")
        timeout = settings.getint("SELENIUM_PAGELOAD_TIMEOUT", 10)
    
        return cls(executable_path, driver_args, timeout)
    
    def __init__(self, executable_path, driver_args, timeout):
        self.executable_path = executable_path
        self.driver_args = driver_args
        self.timeout = timeout
        options = Options()
        for arg in self.driver_args:
            options.add_argument(arg)
        
        service = Service(executable_path=self.executable_path)
        self.driver = webdriver.Chrome(
            options=options,
            service=service,
        )
    
    def close_spider(self, spider):
        self.driver.quit()
        
    def process_item(self, item, spider):
        detail_url = item['Detail_URL']
        self.driver.get(detail_url)
        wait = WebDriverWait(self.driver, self.timeout)
        try:
            wait.until(EC.presence_of_element_located((By.ID, "map")))
            map_element = self.driver.find_element(By.ID, "map")
            self.driver.execute_script("arguments[0].scrollIntoView();", map_element)
            wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "path.leaflet-interactive")
                )
            )

            # create page folder
            main_dir = Path('./data')
            page_id = item['Source_page']
            page_dir = main_dir / Path(f"page_{str(page_id)}")
            index = item['Eia_report_index']
            eia_report_index_dir = page_dir / Path(f"project_{str(index)}")

            image_name = "Raumbezug.jpg"
            html_name = "Source.html"

            image_path = eia_report_index_dir / image_name
            html_path = eia_report_index_dir / html_name

            map_element.screenshot(str(image_path))

        except Exception as e:
            spider.logger.error(f"Failed to save IMAGE: {e}")

        try:
            html = self.driver.page_source
            f = open(html_path, mode="w", encoding="UTF-8")
            f.write(html)
            f.close()

        except Exception as e:
            spider.logger.error(f"Failed to save HTML: {e}")

        return item
