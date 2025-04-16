from zipfile import ZipFile
from pathlib import Path
from io import BytesIO
import shutil
import scrapy
import re
import os


class Website1Spider(scrapy.Spider):
    name = "website_1"

    custom_settings = {
        # "DOWNLOAD_DELAY": 2,
        # "CONCURRENT_REQUESTS": 1,
        "RETRY_TIMES": 2,
        'DOWNLOAD_TIMEOUT': 15,
        'RETRY_ENABLED': True,
        
        "DEFAULT_REQUEST_HEADERS": {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate, br, zstd"
        },
    }

    start_urls = [
        "https://www.uvp-verbund.de/freitextsuche?rstart=0&currentSelectorPage=1",
    ]

    # import settings of page range param
    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        spider.page_limit = crawler.settings.getint("PAGE_LIMIT", default=5)
        return spider


    # get pagination URL and eia report URL
    def parse(self, response):
        
        # get pagination links
        buttons = response.css(".paging.caption > a.icon.small-button")
        pagination_links = []
        current_page_number = 1
        for button in buttons:
            button_name = button.css("a span::text").get()
            button_href = button.css("a::attr(href)").get()
            if button_name and button_href and button_name.isdigit() and 1 < int(button_name)<=self.page_limit:
                pagination_links.append(button_href)
            else:
                if button_name and not button_href and button_name.isdigit() and 1 < int(button_name)<=self.page_limit:
                    current_page_number = int(button_name)
        print("Pagination links:", pagination_links)

        yield from response.follow_all(pagination_links, self.parse)

        # get eia report links
        eia_report_links = list(dict.fromkeys(response.css(".data > .teaser-data.search > a::attr(href)").getall()))

        # cleaned_eia_links = []
        # for link in eia_report_links:
        #     if "?" in link and ";" in link:
        #         cleaned_link = f"{link.split(';')[0]}?{link.split('?')[1]}"
        #         cleaned_eia_links.append(cleaned_link) 

        for i, link in enumerate(eia_report_links, start=1):
            eia_report_index = (current_page_number - 1)*len(eia_report_links) + i
            meta = response.meta.copy()
            meta["eia_report_index"] = eia_report_index
            meta["source_page"] = current_page_number
            yield response.follow(link, callback=self.parse_metadata, meta=meta)     
        # yield from response.follow_all(cleaned_eia_links, self.parse_metadata)   


    # extract the metadata of the page                                     
    def parse_metadata(self, response):

        eia_report_index = response.meta["eia_report_index"]
        source_page = response.meta["source_page"]
        report_type = response.xpath('//div[@class="helper text"]/span/text()').get()
        if report_type:
            report_type = report_type.strip()

        # self.logger.debug(f"Page {source_page} (index {eia_report_index}) - report_type = {report_type}")


        if report_type == "Negative Vorprüfungen":
            yield from self.parse_negative_vorpruefung(response, eia_report_index, source_page, report_type)

        elif report_type == "Zulassungsverfahren":
            yield from self.parse_zulassungsverfahren(response, eia_report_index, source_page, report_type)


    # info extraction for "Negative Vorprüfungen"
    def parse_negative_vorpruefung(self, response, eia_report_index, source_page, report_type):

        
        # if report_type == "Negative Vorprüfungen":
        title = response.xpath('//div[@class="columns"]/h1/text()').get()
        if title:
            title = title.strip()
        last_updated = response.xpath('//div[@class="helper text date"]/span/text()').get()
        last_updated_title = "Zuletzt geändert"
        if last_updated:
            last_updated_title = f"{last_updated.split(' ')[0]} {last_updated.split(' ')[1]}"
            last_updated = last_updated.split(" ")[2]
        project_description_title = response.xpath('//div[@class="columns"]/h3[@class="title-font"]/text()').get()
        if project_description_title:
            project_description_title = project_description_title.strip()
        project_description = response.xpath('//div[@class="columns"]/p/text()').get()
        if project_description:
            project_description = project_description.strip()
        
        if response.xpath('//div[@class="columns"]/h3[@class="title-font"]/text()')[1].get():
            uvp_category_title = response.xpath('//div[@class="columns"]/h3[@class="title-font"]/text()')[1].get()
        else:
            uvp_category_title = "UVP-Kategorie"
        uvp_category = response.xpath('//div[@class="list-item"]/div/span[@class="text"]/text()').getall()
        adressen_title = "Adressen"
        if response.xpath('//div[@class="columns form"]/h3/text()').get():
            adressen_title = response.xpath('//div[@class="columns form"]/h3/text()').get()
        ansprechpartner_title = "Ansprechpartner"
        if response.xpath('//div[@class="columns form"]/h4[@class="no-margin"]/text()').get():
            ansprechpartner_title = response.xpath('//div[@class="columns form"]/h4[@class="no-margin"]/text()').get()
        location = response.xpath('//div[@class="columns form"]/p/text()').getall()
        cleaned_location = []
        if location:
            for value in location:
                value = value.strip()
                value = re.sub(r'\s+', ' ', value).strip()
                cleaned_location.append(value)
        email = response.xpath('//td/a/@href').get()
        if email:
            if isinstance(email, str):
                if ":" in email:
                    email = email.split(":")[1].strip()
        
        phone = response.xpath('//tr[td[contains(text(), "Telefon")]]/td[2]/text()').get()
        if phone:
            phone = phone.strip()
        website = ""
        if len(response.xpath('//td/a/@href').getall()) > 1:
            website = response.xpath('//td/a/@href').getall()[1]
        decision_date_title = "Datum der Entscheidung"
        if response.xpath('//div[@class="columns form"]/h4[@class="no-margin"]/text()')[1].get():
            decision_date_title = response.xpath('//div[@class="columns form"]/h4[@class="no-margin"]/text()')[1].get().strip()
        decision_date = cleaned_location[-1]
        attachment_title = "Ergebnis der UVP-Vorprüfung"
        if response.xpath('//div[@class="columns form"]/h4[@class="title-font"]/text()').get():
            attachment_title = response.xpath('//div[@class="columns form"]/h4[@class="title-font"]/text()').get()
            if attachment_title:
                attachment_title = attachment_title.strip()
        zip_url = response.xpath('//div[@class="zip-download"]/a/@href').get()

        metadata = {
            "Detail_URL": response.url,
            "Eia_report_index" : eia_report_index,
            "Source_page" : source_page,
            "report_type" : report_type,
            "Title" : title,
            last_updated_title: last_updated,
            project_description_title: project_description,
            uvp_category_title: uvp_category,
            adressen_title:{
                ansprechpartner_title:{
                    "location": cleaned_location[:-1],
                    "E-Mail": email,
                    "Telefon": phone,
                    "URL": website,
                },
            },
            decision_date_title: decision_date,
            # attachment_title: {
            #     "Title": eia_report_pdf_title,
            #     "URL": eia_report_pdf_url,
            #     "ZIP_URL": zip_url,
            # },
        }
        attachment_metadata = Website1Spider.attachment_metadata_negative_vorpruefung(response)
        metadata[attachment_title] = attachment_metadata

        yield metadata

        # scrapy.Request() to download zipfile
        if zip_url:
            yield scrapy.Request(
                url=zip_url,
                callback=self.save_zip,
                meta={
                    "eia_report_index": eia_report_index,
                    "source_page": source_page,
                },
            
            )
    

    # info extraction for "Zulassungsverfahren"
    def parse_zulassungsverfahren(self, response, eia_report_index, source_page, report_type):

        # if report_type == "Zulassungsverfahren":
        title = response.xpath('//div[@class="columns"]/h1/text()').get()
        if title:
            title = title.strip()
        last_updated = response.xpath('//div[@class="helper text date"]/span/text()').get()
        last_updated_title = "Zuletzt geändert"
        if last_updated:
            last_updated_title = f"{last_updated.split(' ')[0]} {last_updated.split(' ')[1]}"
            last_updated = last_updated.split(" ")[2]
        project_description_title = response.xpath('//div[@class="columns"]/h3[@class="title-font"]/text()').get()
        if project_description_title:
            project_description_title = project_description_title.strip()
        project_description = response.xpath('//div[@class="columns"]/p/text()').get()
        if project_description:
            project_description = project_description.strip()
        
        if response.xpath('//div[@class="columns"]/h3[@class="title-font"]/text()')[1].get():
            uvp_category_title = response.xpath('//div[@class="columns"]/h3[@class="title-font"]/text()')[1].get()
        else:
            uvp_category_title = "UVP-Kategorie"
        uvp_category = response.xpath('//div[@class="list-item"]/div/span[@class="text"]/text()').getall()
        adressen_title = "Adressen"
        if response.xpath('//div[@class="columns form"]/h3/text()').get():
            adressen_title = response.xpath('//div[@class="columns form"]/h3/text()').get()
        ansprechpartner_title = "Ansprechpartner"
        if response.xpath('//div[@class="columns form"]/h4[@class="no-margin"]/text()').get():
            ansprechpartner_title = response.xpath('//div[@class="columns form"]/h4[@class="no-margin"]/text()').get()
        location = response.xpath('//div[@class="columns form"]/p/text()').getall()
        cleaned_location = []
        if location:
            for value in location:
                value = value.strip()
                value = re.sub(r'\s+', ' ', value).strip()
                cleaned_location.append(value)
        email = response.xpath('//td/a/@href').get()
        if email:
            if isinstance(email, str):
                if ":" in email:
                    email = email.split(":")[1].strip()
        phone = response.xpath('//tr[td[contains(text(), "Telefon")]]/td[2]/text()').get()
        if phone:
            phone = phone.strip()
        website = ""
        if len(response.xpath('//td/a/@href').getall()) > 1:
            website = response.xpath('//td/a/@href').getall()[1]
        metadata = {
            "Detail_URL": response.url,
            "Eia_report_index" : eia_report_index,
            "Source_page" : source_page,
            "report_type" : report_type,
            "Title" : title,
            last_updated_title: last_updated,
            project_description_title: project_description,
            uvp_category_title: uvp_category,
            adressen_title:{
                ansprechpartner_title:{
                    "location": cleaned_location,
                    "E-Mail": email,
                    "Telefon": phone,
                    "URL": website,
                },
            },
        }
        attachment_title = response.xpath('//div[@id="timeline"]/div[@class="columns"]/h1/text()').get()
        if attachment_title:
            attachment_title = attachment_title.strip()
        attachment_metadata = Website1Spider.attachment_metadata_zulassungsverfahren(response)
        metadata[attachment_title] = attachment_metadata[attachment_title]
        yield metadata

        # scrapy.Request() to download zipfile
        zip_url = metadata[attachment_title]["ZIP-URL"]
        print(f"***ZIP_URL***: {zip_url}")
        if zip_url:
            yield scrapy.Request(
                url=zip_url,
                callback=self.save_zip,
                meta={
                    "eia_report_index": eia_report_index,
                    "source_page": source_page,
                },
            
            )


    # recursively unzip attachments
    def recursive_unzip(self, root_dir):

        for current_root, _, files in os.walk(root_dir):
            for f in files:
                if f.lower().endswith('.zip'):
                    zip_path = Path(current_root) / f
                    extract_dir = zip_path.with_suffix('')

                    try:

                        with ZipFile(zip_path, 'r') as z:
                            z.extractall(path=extract_dir)
                        zip_path.unlink()
                        self.logger.info(f"Extracted ZIP to {extract_dir}")

                        self.recursive_unzip(extract_dir)

                    except Exception as e:
                        self.logger.error(f"Failed to UNZIP nested zip {zip_path}: {e}")


    # unzip attachments
    def save_zip(self, response):

        eia_report_index = response.meta["eia_report_index"]
        page_id = response.meta["source_page"]

        dir_path = Path("./data") / f"page_{page_id}" / f"project_{eia_report_index}"
        dir_path.mkdir(parents=True, exist_ok=True)

        try:

            with ZipFile(BytesIO(response.body)) as z:
                z.extractall(path=dir_path / "attachment")
            self.logger.info(f"Extracted ZIP to {dir_path / 'attachment'}")

            self.recursive_unzip(dir_path / "attachment")

        except Exception as e:
            self.logger.error(f"Failed to unzip: {e}")


    # get attachment metadata for "negative_vorpruefung"
    @staticmethod
    def attachment_metadata_negative_vorpruefung(response):
        attachment_metadata = {}
        attachment_title = response.xpath('//div[@class="columns form"]/h4[@class="title-font"]/text()').get()
        if attachment_title:
            attachment_title = attachment_title.strip()
        eia_report_pdf_title = response.xpath('//a[@class="link download"]/@title').getall()
        eia_report_pdf_url = response.xpath('//a[@class="link download"]/@href').getall()
        zip_url = response.xpath('//div[@class="zip-download"]/a/@href').get()
        attachment_metadata["ZIP_URL"] = zip_url
        if eia_report_pdf_url:
            for id, pdf_url in enumerate(eia_report_pdf_url, start=0):
                attachment_metadata[str(id+1)] = {
                    'Document-title': eia_report_pdf_title[id],
                    'Document-URL': eia_report_pdf_url[id],
                }

        return attachment_metadata


    # get attachment metadata for "zulassungsverfahren"
    @staticmethod
    def attachment_metadata_zulassungsverfahren(response):
        timeline_text = response.xpath('//div[@class="timeline-text"]')
        attachment_title = response.xpath('//div[@id="timeline"]/div[@class="columns"]/h1/text()').get()
        zip_link_title = "ZIP-URL"# response.xpath('.//div[@class="zip-download"]/a/@title').get()
        zip_url = response.xpath('.//div[@class="zip-download"]/a/@href').get()
        if attachment_title:
            attachment_title = attachment_title.strip()
        attachment_metadata = {}
        # icon-dot
        attachment_metadata[attachment_title] = {}
        attachment_metadata[attachment_title][zip_link_title] = zip_url

        if timeline_text:
            icon_dots = timeline_text.xpath('.//h2[@class="icon-dot" or @class="icon-check"]')
            if icon_dots:
                icon_count = 1
                num_icon_dot = len(icon_dots)
                
                for dot in icon_dots:

                    siblings = dot.xpath('following-sibling::*')
                    local_scope = []
                    for sib in siblings:
                        cls = sib.attrib.get("class", "")
                        tag = sib.root.tag
                        # if tag == "h4" and ("title-font" in cls):
                        if tag == "h2" and ("icon-dot" in cls or "icon-check" in cls):
                            break
                        local_scope.append(sib)
                    
                    dot_title = dot.xpath('text()').get()

                    if dot_title:
                        dot_title = dot_title.strip()
                    print(f"dot_title: {dot_title}")

                    # no-margin
                    decision_date_title = dot.xpath('following-sibling::h4[@class="no-margin"][1]/text()').get()
                    if decision_date_title:
                        decision_date_title = decision_date_title.strip()
                    print(f"decision_date_title: {decision_date_title}")

                    decision_date = dot.xpath('following-sibling::p[1]/text()').get()
                    if decision_date:
                        decision_date = decision_date.strip()
                    if "-" in decision_date:
                        decision_date = f"{decision_date.split('-')[0].strip()} - {decision_date.split('-')[1].strip()}"
                    print(f"decision_date: {decision_date}")

                    # title-font
                    file_group_title = [node for node in local_scope if node.root.tag == "h4" and "title-font" in node.attrib.get("class", "")]

                    attachment_metadata[attachment_title][f"{str(icon_count)}-{dot_title}"] = {}
                    attachment_metadata[attachment_title][f"{str(icon_count)}-{dot_title}"][decision_date_title] = decision_date
                    if file_group_title:

                        num_file_group = len(file_group_title)
                        for group in file_group_title:
                            
                            siblings = group.xpath('following-sibling::*')
                            title_scope = []
                            for sib in siblings:
                                cls = sib.attrib.get("class", "")
                                tag = sib.root.tag
                                if tag == "h4" and ("title-font" in cls):
                                # if tag == "h2" and ("icon-dot" in cls or "icon-check" in cls):
                                    break
                                title_scope.append(sib)

                            file_group_title_text = group.xpath('text()').get()
                            if file_group_title_text:
                                file_group_title_text = file_group_title_text.strip()
                            print(f"file_group_title_text: {file_group_title_text}")
                            
                            document_lists = [node for node in title_scope if node.root.tag == "div" and "document-list" in node.attrib.get("class", "")]
                            docs_metadata = {}
                            list_id = 1
                            if document_lists:
                                for dl in document_lists:
                                    documents = dl.xpath('div[@class="list-item"]')
                                    if documents:
                                        num_documents = len(documents)
                                        for doc in documents:
                                            doc_metadata = {}
                                            doc_url = doc.xpath('a[@class="link download"]/@href').get()
                                            if doc_url:
                                                doc_url = doc_url.strip()
                                            doc_title = doc.xpath('a[@class="link download"]/@title').get()
                                            if doc_title:
                                                doc_title = doc_title.strip()
                                            print(f"doc_title: {doc_title}")
                                            print(f"doc_url: {doc_url}")
                                            doc_metadata = {
                                                'Document-title': doc_title,
                                                'Document-URL': doc_url,
                                            }
                                            docs_metadata[str(list_id)] = doc_metadata
                                            list_id += 1
                            attachment_metadata[attachment_title][f"{str(icon_count)}-{dot_title}"][file_group_title_text] = docs_metadata
                    icon_count += 1
        return attachment_metadata 