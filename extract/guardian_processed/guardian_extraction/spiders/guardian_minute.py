import os.path as path
base_dir = path.dirname(path.dirname(path.dirname(path.dirname(path.dirname(path.abspath(__file__))))))

import scrapy
import guardian_extraction.items

class GuardianMinuteSpider(scrapy.Spider):
    """
    retrieve all the web pages from the urls stored in the file
    """
    name = "guardian_extraction"
    allowed_domains = ["www.theguardian.com"]
    urls_file = '%s/data/processed/urls/Guardian.txt' % (base_dir)

    with open(urls_file, 'r') as fp:
        start_urls = fp.read().splitlines()

    def __init__(self):
        pass

    def parse(self, response):
        """
        Fetch the links of potential live blogs and their link
        :param response:
        :return:
        """
        item = guardian_extraction.items.GuardianExtractionItem()
        # theoretically, there should be only one link in the list links
        item["url"] = response.url
        item["content"] = response.body.decode("utf-8")

        yield item

        # to fetch the following pages of one live blog
        older_part = response.xpath('//a[@data-link-name="older page"]')
        if len(older_part) >= 1:
            older_part_link = older_part[0].xpath('.//@href').extract()
            if len(older_part_link) >= 1:
                yield scrapy.Request("http://www.theguardian.com" + older_part_link[0], self.parse)
