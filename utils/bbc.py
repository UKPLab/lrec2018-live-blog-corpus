import re
from requests import get
from lxml import html
from nltk.tokenize import sent_tokenize
from bs4 import BeautifulSoup
import itertools

def get_summary(tree):
    
    summary_block = tree.xpath('//ol[@class="lx-c-summary-points gel-long-primer"]')
    if len(summary_block) == 1:
        summary = [line + "." for line in summary_block[0].xpath(".//li/text()")]
    else:
        summary = [""]
    return summary

def get_documents_bbc(tree):
    documents = []
    prev_hour = ['00:00']
    articles = tree.xpath(".//article")
    for article in articles:
        # source title
        source_title = article.xpath('.//header[@class="lx-stream-post__header gs-o-media"]')
        if len(source_title) == 1:
            source_title = text_normalization(BeautifulSoup(html.tostring(source_title[0]), "html.parser").get_text())
        # hour
        hour = re.findall(r"[0-9]{2}:[0-9]{2}", html.tostring(article))  # get the hour linked to the article
        if not hour:
            hour = prev_hour
        # lines
        lines = article.xpath('.//div[@class="lx-stream-post-body"]//p')
        
        # text
        text_lines = []
        if len(lines) >= 1:
            for line in lines:
                text_lines.append(BeautifulSoup(html.tostring(line), "html.parser").get_text())
        # author
        author = article.xpath('.//div[@class="lx-stream-post__contributor gs-o-media"]')
        if len(author) == 1:
            author = author[0].xpath(".//p/text()")  # get the description of the author of the article
        else:
            author = ''
        # extract the links form the block
        
        lines = article.xpath('.//div[@class="lx-stream-post-body"]')
        if len(lines) == 1:
            cont = html.tostring(lines[0])
            links = set(re.findall(r'https?://[a-z\.]+/[a-z\-_0-9/]+\.[a-z]{2,4}', cont))
            links = links.union(re.findall(r'https?://[A-Za-z\.]+/[A-Za-z\-_0-9/]+', cont))
        else:
            cont = html.tostring(article)
            links = set(re.findall(r'https?://[a-z\.]+/[a-z\-_0-9/]+\.[a-z]{2,4}', cont))
            links.union(re.findall(r'https?://[A-Za-z\.]+/[A-Za-z\-_0-9/]+', cont))

        try:
            for link in links:
                # print link
                if "https://twitter.com/" in link and "status" in link:
                    # we extract the content from the twitter status
                    twi_page = get(link).text
                    twi_tree = html.fromstring(twi_page)
                    tweets = twi_tree.xpath('//p[contains(@class, "tweet-text")]')
                    if len(tweets) >= 1:
                        for tweet in tweets: 
                            twi_text = BeautifulSoup(html.tostring(tweet), "html.parser").get_text()
                            text_lines.append(twi_text)
        except:
            pass
        
        # retrieving of links in the text
        block_id = article.get("id")
        
        block_text = [sent_tokenize(text_normalization(line.strip())) for line in text_lines if line.strip() != u""]
        block_text = list(itertools.chain.from_iterable(block_text))
        
        if len(block_text) == 1:
            if block_text[0] == '':
                block_text = [source_title]
        if len(block_text) == 0: 
            block_text = [source_title]
        
        
        d_block = {"time": hour[0], "text": block_text, "block_id": block_id,
                    "author": author, "title": source_title}
        prev_hour = hour
        documents.append(d_block)
    return documents


def process_html_bbc(blog_id, url, WEBPAGE_content, id_=-1):
    """
    That's the best extractor for BBC articles !!!
    use of lxml fo tes
    :param url: simple url
    :param WEBPAGE_content: retrieved from a database
    :param id_: the id of the live blog in the database, it's essential because the url should (maybe) change
    to a normalized form
    :return:
    """
    tree = html.fromstring(WEBPAGE_content)

    title = tree.xpath("//title/text()")
    summary = get_summary(tree)

    documents = get_documents_bbc(tree)
    genre = get_genre_bbc(url)
    if len(summary) > 2 and not re.search('sport|football|cricket', genre):
        quality = 'high'
    else:
        quality = 'low'

    summary_text = [summary_normalization(sent) for sent in summary]

    data = {'blog_id': blog_id, 'url': url, 'genre': genre,
            'title': title[0], 'summary': summary_text, 'documents': documents, 'quality': quality}

    return data

def get_genre_bbc(url):
    """
    Extract the "genre" from the bbc links. It can give an idea of the category of the live blgos, nevertheless the
    usage of this information depends on when the live blog was made.
    :param url: string
    :return: a genre !
    """
    url = remove_question_mark_and_point(url)
    url = url.split("/")[5]
    url = re.sub("[0-9]", "", url)
    url = re.sub("-$", "", url)
    return url

def remove_question_mark_and_point(url):
    """
    Used by the BBC links
    :param url:
    :return:
    """
    if url != "":
        pos = url.find("?")
        if pos != -1:
            url = url[:pos]
        poi = url.find(".app")
        if poi != -1:
            url = url[:poi]
    return url

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
    
    text = re.sub(u" @[^ ]+", u' @twitterid', text)
    text = re.sub(u"^@[^ ]+", u'@twitterid', text)
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
    text = re.sub(u'View more on twitter', u'', text)
    text = re.sub(u'\^CT', u'', text)
    text = re.sub(u'http[^ ]+', u'', text)
    text = re.sub(u'[^ ]+twitter.com[^ ]+', u'', text)
    return text
