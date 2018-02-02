
import re
from nltk.tokenize import sent_tokenize
from lxml import html
from bs4 import BeautifulSoup

def get_timeline(timeline_section):
    timeline = []
    if len(timeline_section) == 1:
        timeline_blocks = timeline_section[0]
        for a in timeline_blocks.xpath(".//ul/li"):
            b = a.xpath("a")[0]
            timeline.append({"block": b.get('data-event-id'), "text": sent_tokenize(summary_normalization(b.text_content()))})
    return timeline

def get_keypoints(keypoints_section):
    keypoints = []
    if len(keypoints_section) != 0:
        for i in keypoints_section[0].getchildren():
            if i.tag == "p":
                sum_now = {"text": summary_normalization(i.text_content()), "link": []}
                for k in i.xpath(".//a"):
                    sum_now["link"].append(k.get("href"))
                keypoints.append(sum_now)
            elif i.tag == "ul":
                for j in i.xpath(".//li"):
                    sum_now = {"text": summary_normalization(j.text_content()), "link": []}
                    for k in j.xpath(".//a"):
                        sum_now["link"].append(k.get("href"))
                    keypoints.append(sum_now)
    return keypoints

def get_summary(tree):
    summary = {"head_summary": [], "key_events_text": [], "key_events": []}
    if len(tree.xpath('//div[@class="content__standfirst"]')) != 0:
        timeline_links = []
        timeline_block = tree.xpath('//div[@data-component="timeline"]')
        if len(timeline_block) == 1:
            timeline = timeline_block[0]
            for a in timeline.xpath(".//ul/li"):
                b = a.xpath("a")[0]
                timeline_links.append({"block": b.get('data-event-id'), "text": b.text_content()})
        for i in tree.xpath('//div[@class="content__standfirst"]')[0].getchildren():
            type_ = i.tag
            if i.tag == "p":
                sum_now = {"text": [], "link": [], "key_points": [], "time": "", "type": type_}
                sum_now["text"] = summary_normalization(i.text_content())
                # sum_now["link"].extend(re.findall(r'https?://[A-Za-z\.]+/[A-Za-z\-_0-9/]+', html.tostring(i)))
                for k in i.xpath(".//a"):
                    sum_now["link"].append(k.get("href"))
                summary["head_summary"].append(sum_now)
            elif i.tag == "ul":
                for j in i.xpath(".//li"):
                    sum_now = {"text": [], "link": [], "key_points": [], "time": "", "type": type_}
                    sum_now["text"] = summary_normalization(j.text_content())
                    for k in j.xpath(".//a"):
                        sum_now["link"].append(k.get("href"))
                    summary["head_summary"].append(sum_now)
        summary["key_events_text"].extend(timeline_links)
    return summary 

def extraction_date_hour(date_hour):
    """
    From a string whose structure is : ...
    :param date_hour:
    :return: [year, month, day, hour, minute] and each elements are integer
    """
    slash = date_hour.split('-')
    year = slash[0]
    month = slash[1]
    t = slash[2].split("T")
    day = t[0]
    two_points = t[1].split(":")
    hour = two_points[0]
    minute = two_points[1]
    return int(year), int(month), int(day), int(hour), int(minute)

def extract_documents(articles):
    body =[]
    if len(articles) != 0:
        for article in articles:
            block_time = article.xpath('.//p[@class="block-time published-time"]')
            if len(block_time) != 0:
                cc = block_time[0].xpath(".//time")
                for c in cc:
                    datetime = c.get("datetime")
                    if datetime is not None:  # "2014-07-23T12:02:45.546Z"
                        time_creation = extraction_date_hour(datetime)

            # extract the text from the block
            text_lines = []
            block_lines = article.xpath('.//div[@itemprop="articleBody"]')
            for lines in block_lines:
                text_lines.append(text_normalization(BeautifulSoup(html.tostring(lines), "html.parser").get_text()))

            """
            # Get the links inside the block
            links = re.findall(r'https?://[a-z\.]+/[a-z\-_0-9/]+\.[a-z]{2,4}',
                               html.tostring(article))  # retrieving of links in the text
            links = [link for link in links if link.split('.')[-1] not in ["jpg", "jpeg", "png"]]
            links.extend(re.findall(r'https?://[a-z\.]+/[a-z\-_0-9/]+',
                                    html.tostring(article)))
            """
            
            # Get the title of the block
            part_title = article.xpath('.//h2[@class="block-title"]')
            if len(part_title) != 0:
                block_title = part_title[0].text_content()
            
            block_id = article.get("id")
            if block_id is None:
                continue
            
            block_kind = article.get("class")
            is_key = False
            
            # Check if the block is a summary point
            section = article.get("class")
            if re.search('is-key-event'|'is-summary', section):
                is_key = True
            
            block_text = [line.strip() for line in text_lines if line.strip() != u""]
            
            d_block = {"time": time_creation, "text": block_text, "block_id": block_id,
                        "doc_title": unicode(block_title), "block_kind": block_kind,
                         'key_event': is_key}
            body.append(d_block)
                       
    return body       
    

def get_documents(tree):
    article = tree.xpath('.//div[@itemprop="liveBlogUpdate"]')
    documents = extract_documents(article)
    if not documents:
        article = tree.xpath('.//div[@itemprop="articleBody"]')
        documents = extract_documents(article)

def process_html(blog_id, url, html_content):
    
    tree = html.fromstring(html_content)
    # the title
    title = tree.xpath("//title/text()")

    # Get the category
    if len(tree.xpath('//div[@class="content__labels "]')) != 0:
        category = tree.xpath('//div[@class="content__labels "]')[0].xpath(".//a/text()")
    elif len(tree.xpath('//div[@class="content__section-label"]')) != 0 and len(
            tree.xpath('//div[@class="content__series-label"]')) != 0:
        category = {"section_text": tree.xpath('//div[@class="content__section-label"]')[0].xpath(".//a/text()"),
                    "section_link": tree.xpath('//div[@class="content__section-label"]')[0].xpath(".//a")[0].get(
                        "href"),
                    "series_text": tree.xpath('//div[@class="content__series-label"]')[0].xpath(".//a/text()"),
                    "series_link": tree.xpath('//div[@class="content__series-label"]')[0].xpath(".//a")[0].get("href")}
    elif len(tree.xpath('//div[@class="content__section-label"]')) != 0:
        category = {"section_text": tree.xpath('//div[@class="content__section-label"]')[0].xpath(".//a/text()"),
                    "section_link": tree.xpath('//div[@class="content__section-label"]')[0].xpath(".//a")[0].get(
                        "href")}

    elif len(tree.xpath('//div[@class="content__series-label"]')) != 0:
        category = {"series_text": tree.xpath('//div[@class="content__series-label"]')[0].xpath(".//a/text()"),
                    "series_link": tree.xpath('//div[@class="content__series-label"]')[0].xpath(".//a")[0].get("href")}

    else:
        category = ""
    
    documents = get_documents(tree)
    summary = get_summary(tree)
    
    data = {'blog_id': blog_id, 'url': url, 'category': category, 'genre': get_genre(url),
            'title': title, 'summary': summary, 'documents': documents}
    
    return data


def summary_normalization(summary):
    try:
        summary = unicode(summary)
    except:
        pass
    summary = text_normalization(summary)
    summary = re.sub(u" {2,10}", u". ", summary)
    if summary != u"":
        summary = re.sub(u'[a-zA-Z]$', summary[-1] + ".", summary)       
        
    return summary

def text_normalization(text):
    '''
    Normalize text
    Remove & Replace unnessary characters
    Parameter argument:
    text: a string (e.g. '.... *** New York N.Y is a city...')
    
    Return:
    text: a string (New York N.Y is a city.)
    '''
    text = re.sub(u'\u201e|\u201c',u'', text)
    text = re.sub(u"\u2022",u'. ', text)  
    text = re.sub(u"([.?!]);",u"\\1", text)
    text = re.sub(u'``', u'``', text)
    text = re.sub(u"\.\.+",u" ", text)
    text = re.sub(u"\s+\.",u".", text)
    text = re.sub(u"\?\.",u"?", text)
    #Dash to remove patterns like NAME (Twitter id)
    text = re.sub(u"\u2014[^\n]+", u'', text)
    
    #Line of format Month day, year (ex:March 7, 2017)
    text = re.sub(u"\n[a-zA-Z]+\s+\d+,\s+\d{4}", u'', text)
    
    #Line of format Time GMT (ex:6.20pm GMT)
    text = re.sub(u"\d+\.\d+(am|pm) (GMT|BST)\n", u'', text)
    #Line of format 15:35
    text = re.sub(u"\d+:\d+\n", u'', text)
    
    text = re.sub(u"pic[^ \n]+", u'', text)
    text = re.sub(u"Photograph: [a-zA-Z]+", u'', text)

    #BBC specific twitter:
    text = re.sub(u"twitter: [^\s]+\s", u'', text)
    text = re.sub(u"twitter: ", u'', text)  
    text = re.sub(u"http[^ \n]+", u'', text)
    
    text = re.sub(u" @[a-zA-Z]+", u' @twitterid', text)
    text = re.sub(u'^[\n_]+',u'', text)
    #text = re.sub(u'[\s\t]+',u' ', text)
    text = re.sub(u'[\n_]+',u'\n', text)
    text = re.sub(u"[*]",u"", text)
    text = re.sub(u"\-+",u"-", text)
    text = re.sub(u'^ ',u'', text)
    text = re.sub(u'\u00E2',u'', text)
    text = re.sub(u'\u00E0',u'a', text)
    text = re.sub(u'\u00E9',u'e', text)
    text = re.sub(u'\u2019',u"'", text)
    text = re.sub(u'\u2018',u"'", text)
    text = re.sub(u'\u201d',u'"', text)
    text = re.sub(u'\u201c',u'"', text)
    text = re.sub(u'\u2013',u'-', text)
    text = re.sub(u'\u2026',u'', text)
    text = re.sub(u"\u00A3",u"\u00A3 ", text)
    text = re.sub(u"\nBBC ",u"", text)
    text = re.sub(u"^BBC ",u"", text)
    text = re.sub(u"\. BBC ",u". ", text)
    text = re.sub(u"([.?!]);",u"\\1", text)
    text = re.sub(u'[\n\s\t\r_]+', u' ', text)
    text = re.sub(u"\\u00A0", u" ", text)
    text = re.sub(u"\u00A0", u" ", text) 
    text = re.sub(u' +$', u'', text)  
    text = re.sub(u" {2,10}", u". ", text)
    text = re.sub(u'\xa0', u' ', text)
    text = re.sub(u' +$', u'', text)  
    return text
    
def get_genre(url):
    """
    Extract the "genre" from the Guardian links. It can give an idea of the category of the live blgos, nevertheless the
    usage of this information depends on when the live blog was made.
    :param url: a url struction
    :return: the genre
    """
    return url.split("/")[3]