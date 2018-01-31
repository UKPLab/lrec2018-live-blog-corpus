import scrapy
import guardian_urls_fetch.items

class GuardianMinuteSpider(scrapy.Spider):
    """
    Retrieve all the Guardian live blog urls
    """
    name = "guardian_urls_fetch"
    allowed_domains = ["www.theguardian.com"]
    start_urls = ['http://www.theguardian.com/tone/minutebyminute/?page=1']

    def __init__(self):
        self.curr_page = 1
        self.max_page = 10000

    def parse(self, response):
        """
        Fetch the links of potential live blogs and their link
        :param response:
        :return:
        """
        for i in response.xpath("//a"):
            href = i.xpath(".//@href").extract()
            text = i.xpath(".//text()").extract()
            if keep_live_blogs(text, href):
                item = guardian_urls_fetch.items.GuardianSiteFecthingItem()
                item["url"] = href[0]
                yield item

        self.curr_page += 1
        next_present = response.css(".pagination__list").xpath(".//a/@rel").extract()
        if "next" in next_present and self.curr_page <= self.max_page:
            page_links = response.css(".pagination__list").xpath(".//a/@href").extract()
            link_to_next_page = page_links[-1]
            url = response.urljoin(link_to_next_page)
            yield scrapy.Request(url, self.parse)


def keep_live_blogs(text, links):
    """
    :param text: Reject all the links which are only categories
    :param links: We can sort out the sports live blogs from the others
    :return: True if the couple (text, links) should be kept.
    """
    if len(text) == 1:
        sep_text = text[0].split()

        if len(links) == 1:
            return len(sep_text) > 4 and "\n" not in text[0]
    else:
        return False
