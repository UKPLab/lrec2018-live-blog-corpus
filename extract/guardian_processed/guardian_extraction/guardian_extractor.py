import os
import json
from lxml import html
import codecs
import sqlite3
import re
from requests import get
import pickle
import time
from extraction_tools import *
from bs4 import BeautifulSoup
from nltk.tokenize import sent_tokenize, word_tokenize
import matplotlib.pyplot as plt
from datetime import date
from live_blog_retrieval_statistics import keep_clean_parsed_liveblogs, gua_keep_good_liveblogs
import numpy

def new_gua_extractor(url, webpage_content, id_=-1):
    """
    That's the best extractor for the Guardian articles !!!
    use of lxml fo tes
    :param url: simple url
    :param webpage_content: retrieved from a database
    :param id_:
    :return:
    """
    def get_summary_block_with_bullet_points(article):
        classe_sections = ["block block--content is-summary", "block is-summary"]
        classe = article.get("class")
        if classe in classe_sections:
            lis = article.xpath('.//li')
            for_summary = []
            for li in lis:
                sentence = sent_tokenize(text_normalization(li.text_content()))
                if len(sentence) != 0:
                    for_summary.append(sentence[0])
            return for_summary
        else:
            return None

    def get_key_point_block_with_bullet_points(article):
        key_point_sections = ["block is-key-event", "block block--content is-key-event"]
        section = article.get("class")
        if section in key_point_sections:
            lis = article.xpath('.//li')
            for_summary = []
            for li in lis:
                sentence = sent_tokenize(text_normalization(li.text_content()))
                if len(sentence) != 0:
                    for_summary.append(sentence[0])
            return for_summary
        else:
            return None

    tree = html.fromstring(webpage_content)
    # Get the title
    title = unicode(tree.xpath("//title/text()"))

    # Get the category
    if len(tree.xpath('//div[@class="content__labels "]')) != 0:
        category = [unicode(item) for item in tree.xpath('//div[@class="content__labels "]')[0].xpath(".//a/text()")]
    # elif len(tree.xpath('//div[@class="content__section-label"]')) != 0 and len(
    #         tree.xpath('//div[@class="content__series-label"]')) != 0:
    #     category = {"section_text": tree.xpath('//div[@class="content__section-label"]')[0].xpath(".//a/text()"),
    #                 "section_link": tree.xpath('//div[@class="content__section-label"]')[0].xpath(".//a")[0].get(
    #                     "href"),
    #                 "series_text": tree.xpath('//div[@class="content__series-label"]')[0].xpath(".//a/text()"),
    #                 "series_link": tree.xpath('//div[@class="content__series-label"]')[0].xpath(".//a")[0].get("href")}
    # elif len(tree.xpath('//div[@class="content__section-label"]')) != 0:
    #     category = {"section_text": tree.xpath('//div[@class="content__section-label"]')[0].xpath(".//a/text()"),
    #                 "section_link": tree.xpath('//div[@class="content__section-label"]')[0].xpath(".//a")[0].get(
    #                     "href")}
    #
    # elif len(tree.xpath('//div[@class="content__series-label"]')) != 0:
    #     category = {"series_text": tree.xpath('//div[@class="content__series-label"]')[0].xpath(".//a/text()"),
    #                 "series_link": tree.xpath('//div[@class="content__series-label"]')[0].xpath(".//a")[0].get("href")}

    else:
        category = []

    # Timeline
    timeline = []
    timeline_section = tree.xpath('//div[@data-component="timeline"]')
    if len(timeline_section) == 1:
        timeline_blocks = timeline_section[0]
        for a in timeline_blocks.xpath(".//ul/li"):
            b = a.xpath("a")[0]
            timeline.append({"block": b.get('data-event-id'), "text": summary_normalization(b.text_content())})

    # Get the key point section
    key_point_section = []
    stand_first = tree.xpath('//div[@class="content__standfirst"]')
    if len(stand_first) != 0:
        for i in stand_first[0].getchildren():
            if i.tag == "p":
                sum_now = {"text": summary_normalization(i.text_content()), "link": []}
                for k in i.xpath(".//a"):
                    sum_now["link"].append(k.get("href"))
                key_point_section.append(sum_now)
            elif i.tag == "ul":
                for j in i.xpath(".//li"):
                    sum_now = {"text": summary_normalization(j.text_content()), "link": []}
                    for k in j.xpath(".//a"):
                        sum_now["link"].append(k.get("href"))
                    key_point_section.append(sum_now)

    body = []
    summary_with_bullets = []
    summary_without_bullets = []
    key_point_with_bullets = []
    key_point_without_bullets = []
    articles = tree.xpath('.//div[@itemprop="liveBlogUpdate"]')
    if len(articles) != 0:
        extraction_kind = 1
        for article in articles:
            # print "----------------------------------------------------------------------------"
            # print html.tostring(article)
            # print "\n"
            # Get the time of the block
            # time_creation = {"complete": "", "day": "", "hour": ""}
            time_creation = []
            block_time = article.xpath('.//p[@class="block-time published-time"]')
            if len(block_time) != 0:
                cc = block_time[0].xpath(".//time")
                for c in cc:
                    datetime = c.get("datetime")
                    if datetime is not None:  # "2014-07-23T12:02:45.546Z"
                        # time_creation["complete"] = datetime
                        # year, month, day, hour, minute = extraction_date_hour(datetime)
                        time_creation = extraction_date_hour(datetime)
                        # time_creation["day"] = year, month, day
                        # time_creation["hour"] = hour, minute

            # extract the text from the block
            text_lines = []
            block_lines = article.xpath('.//div[@itemprop="articleBody"]')
            for lines in block_lines:
                # print lines.text_content(), type(lines.text_content())
                text_lines.append(text_normalization(BeautifulSoup(html.tostring(lines), "html.parser").get_text()))

            # Get the links inside the block
            links = re.findall(r'https?://[a-z\.]+/[a-z\-_0-9/]+\.[a-z]{2,4}',
                               html.tostring(article))  # retrieving of links in the text
            links = [link for link in links if link.split('.')[-1] not in ["jpg", "jpeg", "png"]]
            links.extend(re.findall(r'https?://[a-z\.]+/[a-z\-_0-9/]+',
                                    html.tostring(article)))
            # Get the title of the block
            part_title = article.xpath('.//h2[@class="block-title"]')
            pa_title = ''
            if len(part_title) != 0:
                pa_title = part_title[0].text_content()
            block = article.get("id")
            if block is None:
                continue
            block_kind = article.get("class")

            is_summary_or_key_event = False
            # Get a block if it is a summary block (just the bullet points)
            summary_block_with_bullet_points = get_summary_block_with_bullet_points(article)
            if summary_block_with_bullet_points is not None:
                if len(summary_block_with_bullet_points) != 0:
                    is_summary_or_key_event = True
                    summary_with_bullets.append({"text": summary_block_with_bullet_points, "time": time_creation,
                                                 'links': links, "block_id": block, "doc_title": unicode(pa_title),
                                                 "block_kind": block_kind})

            # Get a block if it is a summary block
            classe_sections = ["block block--content is-summary", "block is-summary"]
            classe = article.get("class")
            if classe in classe_sections:
                if len(text_lines) != 0:
                    is_summary_or_key_event = True
                    summary_without_bullets.append({"text": text_lines, "time": time_creation, 'links': links,
                                                    "block_id": block, "doc_title": unicode(pa_title),
                                                    "block_kind": block_kind})

            # Get a block if it is a key-point block (just the bullet points)

            key_point_block_with_bullets = get_key_point_block_with_bullet_points(article)
            if key_point_block_with_bullets is not None:
                if len(key_point_block_with_bullets) != 0:
                    is_summary_or_key_event = True
                    key_point_with_bullets.append({"text": key_point_block_with_bullets, "time": time_creation,
                                                   'links': links, "block_id": block, "doc_title": unicode(pa_title),
                                                   "block_kind": block_kind})

            # Get a block if it is a key-point block
            key_point_sections = ["block is-key-event", "block block--content is-key-event"]
            section = article.get("class")
            if section in key_point_sections:
                if len(text_lines) != 0:
                    is_summary_or_key_event = True
                    key_point_without_bullets.append({"text": text_lines, "time": time_creation, 'links': links,
                                                      "block_id": block, "doc_title": unicode(pa_title),
                                                      "block_kind": block_kind})
            if not is_summary_or_key_event:
                d_block = {"time": time_creation, "text": [line.strip() for line in text_lines if line.strip() != u""],
                           'links': links, "block_id": block, "doc_title": unicode(pa_title), "block_kind": block_kind}
                body.append(d_block)

    else:
        extraction_kind = 2
        article_body = tree.xpath('.//div[@itemprop="articleBody"]')

        if len(article_body) == 1:

            body_parts = article_body[0].xpath('.//div[starts-with(@id, "block")]')
            for part in body_parts:
                # print "----------------------------------------------------------------------------"
                # print html.tostring(part)
                # print "\n"
                # hours = part.xpath('.//p/time/text()')
                # Get the time of the block
                # time_creation = {"complete": "", "day": "", "hour": ""}
                time_creation = []  #if it remains void, there is a problem
                block_time = part.xpath('.//p[@class="block-time published-time"]')
                if len(block_time) != 0:
                    cc = block_time[0].xpath(".//time")
                    for c in cc:
                        datetime = c.get("datetime")
                        if datetime is not None:  # "2014-07-23T12:02:45.546Z"
                            # time_creation["complete"] = datetime
                            time_creation = extraction_date_hour(datetime)
                            # year, month, day, hour, minute = extraction_date_hour(datetime)
                            # time_creation["day"] = year, month, day
                            # time_creation["hour"] = hour, minute
                            # time_creation = [year]

                part_title = part.xpath('.//h2[@class="block-title"]')
                if len(part_title) != 0:
                    pa_title = part_title[0].text_content()
                else:
                    pa_title = ""
                # Get the links inside the block
                links = re.findall(r'https?://[a-z\.]+/[a-z\-_0-9/]+\.[a-z]{2,4}',
                                   html.tostring(part))  # retrieving of links in the text
                links = [link for link in links if link.split('.')[-1] not in ["jpg", "jpeg", "png"]]
                links.extend(re.findall(r'https?://[a-z\.]+/[a-z\-_0-9/]+',
                                        html.tostring(part)))
                text_lines = []
                for line in part.xpath('.//div[@class="block-elements"]'):
                    text_lines.append(text_normalization(line.text_content()))
                block = part.get("id")

                # If the block has no block id, we don't take it
                if block is None:
                    continue
                block_kind = part.get("class")



                is_summary_or_key_event = False
                # Get a block if it is a summary block (just the bullet points)
                summary_block_with_bullet_points = get_summary_block_with_bullet_points(part)
                if summary_block_with_bullet_points is not None:
                    if len(summary_block_with_bullet_points) != 0:
                        is_summary_or_key_event = True
                        summary_with_bullets.append({"text": summary_block_with_bullet_points, "time": time_creation,
                                                     'links': links, "block_id": block, "doc_title": unicode(pa_title),
                                                     "block_kind": block_kind})

                # Get a block if it is a summary block
                classe_sections = ["block block--content is-summary", "block is-summary"]
                classe = part.get("class")
                if classe in classe_sections:
                    if len(text_lines) !=0:
                        is_summary_or_key_event = True
                        summary_without_bullets.append({"text": text_lines, "time": time_creation, 'links': links, "block_id": block, "doc_title": unicode(pa_title),
                                                       "block_kind": block_kind})

                # Get a block if it is a key-point block (just the bullet points)

                key_point_block_with_bullets = get_key_point_block_with_bullet_points(part)
                if key_point_block_with_bullets is not None:
                    if len(key_point_block_with_bullets) != 0:
                        is_summary_or_key_event = True
                        key_point_with_bullets.append({"text": key_point_block_with_bullets, "time": time_creation,
                                                       'links': links, "block_id": block, "doc_title": unicode(pa_title),
                                                      "block_kind": block_kind})

                # Get a block if it is a key-point block
                key_point_sections = ["block is-key-event", "block block--content is-key-event"]
                section = part.get("class")
                if section in key_point_sections:
                    if len(text_lines) != 0:
                        is_summary_or_key_event = True
                        key_point_without_bullets.append({"text": text_lines, "time": time_creation,
                                                          'links': links, "block_id": block, "doc_title": unicode(pa_title),
                                                         "block_kind": block_kind})
                if not is_summary_or_key_event:
                    d_block = {"time": time_creation, "text": [line.strip() for line in text_lines if line.strip() != u""],
                               'links': links, "block_id": block, "doc_title": unicode(pa_title),
                               "block_kind": block_kind}
                    body.append(d_block)


    one_live_blog = {}
    one_live_blog["url"] = url
    one_live_blog["database_id"] = id_
    one_live_blog["category"] = category
    one_live_blog["genre"] = get_genre_gua(url)
    one_live_blog["title"] = title
    one_live_blog["timeline"] = timeline
    one_live_blog["key-point-section"] = key_point_section
    one_live_blog["summary"] = {"summary_with_bullets": summary_with_bullets,
                                "summary_without_bullets": summary_without_bullets,
                                "key_point_with_bullets": key_point_with_bullets,
                                "key_point_without_bullets": key_point_without_bullets}
    one_live_blog["documents"] = body
    one_live_blog["extraction_kind"] = extraction_kind
    return one_live_blog  # , next_url


def the_guardian_extractor(url, WEBPAGE_content, id_=-1):
    """
    That's the best extractor for the Guardian articles !!!
    use of lxml fo tes
    :param url: simple url
    :param WEBPAGE_content: retrieved from a database
    :return:
    """

    tree = html.fromstring(WEBPAGE_content)
    # the title
    title = tree.xpath("//title/text()")

    # the category
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

    # contains the key points or the summary
    # the advantage with BeautifulSoup is that he takes all the text in the right order,
    # however he does not associate the content with links, but for what we want (summarize text and use summaries),
    # does not matter.
    # resum = tree.xpath('//div[@class="content__standfirst"]')
    # if len(resum) == 1:
    #     summary = BeautifulSoup(html.tostring(resum[0]), "html.parser").get_text()
    # summary = []
    summary = {"complete_summary": [], "head_summary": [], "key_events_links_and_text": [], "key_events": []}
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
        summary["key_events_links_and_text"].extend(timeline_links)

        # we take the text
        # for j in i.xpath(".//p/text()"):
        #     # print "euh"
        #     if j.strip() != "":
        #         sum_now["text"].append(j.strip())
        # then the links
        # for k in i.xpath(".//li/a"):
        #     # print "non"
        #     # d = {"link": k.get("href")}
        #     # print html.tostring(k)
        #     sum_now["link"].append(k.get("href"))
        #     # print html.tostring(k))
        #     if len(k.xpath(".//text()")) != 0:
        #         # print k.xpath(".//text()")
        #         # print k.xpath(".//text()")[0]
        #         # d["text"] = k.xpath(".//text()")[0].strip()
        #         sum_now["text"].append(k.xpath(".//text()")[0].strip())
        # and what's inside the text
        # for l in i.xpath(".//li"):
        #     # print "peut-etre"
        #     for text in l.xpath(".//text()"):
        #         sum_now["text"].append(text)

    # summary["complete_summary"].append({"text": "", "key_point": "", "link": "", time: ""})
    # summary["complete_summary"] = " ".join(summary["complete_summary"])
    # should we keep it?




    # A RAJOUTER POUR FAIRE DE MEILLEURS RESUMES
    # if len(tree.xpath('//meta[@itemprop="description"]')) == 1:
    #     sum_now = {"text": [], "link": [], "key_points": [], "time": ""}
    #     if len(summary["text"]) == 0:
    #         summary["text"].append(tree.xpath('//meta[@itemprop="description"]')[0].xpath('.//@content')[0])
    #     if len(summary["text"]) == 1:
    #         if summary["text"][0].strip() == "":
    #             summary["text"].append(tree.xpath('//meta[@itemprop="description"]')[0].xpath('.//@content')[0])
    #     summary["head_summary"].append(sum_now)
    # elif len(tree.xpath('//div[@class="score-container"]')) != 0:
    #     print "ok"
    # ------------------------------------------------

    body = []
    articles = tree.xpath('.//div[@itemprop="liveBlogUpdate"]')
    if len(articles) != 0:
        for article in articles:
            hour = re.findall(r"[0-9]{2}:[0-9]{2}", html.tostring(article))  # get the hour linked to the article
            lines = article.xpath('.//div[@itemprop="articleBody"]')
            # if len(lines) == 1:
            #     lines = lines[0].xpath(".//p/text()")

            text_lines = []
            if len(lines) == 1:
                results = lines[0].xpath(".//p")
                for result in results:
                    text_lines.append(BeautifulSoup(html.tostring(result), "html.parser").get_text())
            links = re.findall(r'https?://[a-z\.]+/[a-z\-_0-9/]+\.[a-z]{2,4}',
                               html.tostring(article))  # retrievnig of links in the text
            links = [link for link in links if link.split('.')[-1] not in ["jpg", "jpeg", "png"]]
            links.extend(re.findall(r'https?://[a-z\.]+/[a-z\-_0-9/]+',
                                    html.tostring(article)))
            part_title = article.xpath('.//h2[@class="block-title"]')
            pa_title = ''
            if len(part_title) != 0:
                a = part_title[0].xpath(".//text()")
                if len(a) != 0:
                    pa_title = a[0]
            try:
                block = article.get("id")
            except:
                block = None
            body.append({"time": hour[0], "text": [line.strip() for line in text_lines if line.strip() != u""]
                        , 'links': links, "block_id": block, "doc_title": pa_title})
    else:
        article_body = tree.xpath('.//div[@itemprop="articleBody"]')
        if len(article_body) == 1:
            body_parts = article_body[0].xpath('.//div[starts-with(@class, "block")]')
            for part in body_parts:
                hours = part.xpath('.//p/time/text()')
                part_title = part.xpath('.//h2[@class="block-title"]')
                if len(part_title) != 0:
                    a = part_title[0].xpath(".//text()")
                    if len(a) != 0:
                        part_title = a[0]
                links = re.findall(r'http://[a-z\.]+/[a-z\-_0-9/]+\.[a-z]{2,4}', html.tostring(part))
                lines = []
                for line in part.xpath('.//div[@class="block-elements"]'):
                    for li in line.xpath(".//text()"):
                        if li.strip() != "" or li.strip() != "":
                            lines.append(li.strip())
                try:
                    block = article_body.get("id")
                except:
                    block = None
                if len(hours) == 0:
                    hours = ['']
                d = {"time": hours[0], "doc_title": part_title, "links": links,
                     "text": lines, "block_id": block}  # "hours_datetime": hours_datetime
                body.append(d)
    one_live_blog = {}
    one_live_blog["url"] = url
    one_live_blog["database_id"] = id_
    one_live_blog["category"] = category
    one_live_blog["genre"] = get_genre_gua(url)
    one_live_blog["title"] = title
    one_live_blog["summary"] = summary
    one_live_blog["documents"] = body
    return one_live_blog  # , next_url


def script_extract_one_the_guardian_live_blog_content(extractor, json_filename, id_=-1, url=""):
    """
    opens the database, THE_GUARDIAN_COMPLETE_live_blogs.db, stores one url and the parsed contents inside a json file
    for the correspondant id or url
    Used only to check how an extraction is done
    :param extractor:
    :param json_filename: must finish with ".json
    :param id_:
    :param url:
    :return:
    """
    # it's to check the correctness of the json_filename
    assert json_filename[len(json_filename) - 5:] == ".json"
    if id_ >= 1:
        # connection to the database and retrieval of the webpage and url
        conn = sqlite3.connect(os.path.join(".", FOLDER, DATABASE))
        cursor = conn.cursor()
        cursor.execute("""SELECT id FROM THE_GUARDIAN_WEB_PAGES""")
        ids = cursor.fetchall()
        assert id_ < len(ids)
        reparsed_live_blogs = codecs.open(os.path.join('.', FOLDER, "f_" + str(id_) + json_filename),
                                          'w', encoding="utf-8")  # file where the results is going to be stored
        reparsed_live_blogs.write("[")
        cursor.execute("""SELECT webpage, url FROM THE_GUARDIAN_WEB_PAGES WHERE id=?""", (str(id_),))
        webpage, url = cursor.fetchone()
        print url
        if len(webpage) == 1:
            webpage = webpage[0]
        one_live_blog = extractor(url, webpage)
        line = json.dumps(one_live_blog, ensure_ascii=False) + ",\n"
        reparsed_live_blogs.write(line)
        reparsed_live_blogs.write("{}]")
        reparsed_live_blogs.close()
        conn.close()
    else:
        webpage = get(url)
        reparsed_live_blogs = codecs.open(os.path.join('.', FOLDER, "f_" + str(id) + json_filename),
                                          'w')  # file where the results is going to be stored
        reparsed_live_blogs.write("[")
        one_live_blog = extractor(url, webpage.content)
        line = json.dumps(one_live_blog, ensure_ascii=False) + ",\n"
        reparsed_live_blogs.write(line)
        reparsed_live_blogs.write("{}]")
        reparsed_live_blogs.close()


def script_extract_the_guardian_content(extractor, folder, database, json_filename, problem_file):
    """
    opens the database, THE_GUARDIAN_COMPLETE_live_blogs.db, stores the urls and parsed contents inside a json file.
    :param extractor:
    :param folder:
    :param database:
    :param json_filename: must finish with ".json
    :param problem_file: file where we store the urls which gave problems
    :return:
    """
    # it's to check the correctness of the json_filename
    assert json_filename[len(json_filename) - 5:] == ".json"

    # connection to the database and retrieval of the webpage and url
    conn = sqlite3.connect(os.path.join(".", folder, database))
    cursor = conn.cursor()
    cursor.execute("""SELECT id FROM THE_GUARDIAN_WEB_PAGES""")
    ids = cursor.fetchall()
    ids = [id_[0] for id_ in ids]
    print len(ids)
    a = open(problem_file, "w")
    # variable used to see the number of webpages processed
    azerty = 0
    parsed_live_blogs = codecs.open(os.path.join('.', folder, json_filename),
                                    'w',
                                    encoding="utf-8")  # file where the results are going to be stored
    list_text_json = []

    # is it useful ???
    def remove_items(l, m):
        for i in l:
            del m[m.index(i)]
        return m

    ind_to_delete = [227, 714, 834]  # debug
    ids = remove_items(ind_to_delete, ids)
    one_live_blog = {}
    for id_ in ids:
        cursor.execute("""SELECT webpage, url FROM THE_GUARDIAN_WEB_PAGES WHERE id=?""", (str(id_),))
        webpage, url = cursor.fetchone()
        if len(webpage) == 1:
            webpage = webpage[0]
        try:
            one_live_blog = extractor(url, webpage, id_)
            if accept_extraction(one_live_blog):
                line = json.dumps(one_live_blog, ensure_ascii=False) + "\n"
                parsed_live_blogs.write(line)
        except TypeError:
            print "erreur"
            print one_live_blog
            a.write(str(id_) + "\n" + url + "\n")
            print id_
            print url

        if azerty % 100 == 0:
            print "we're here : ", azerty
        azerty += 1
    parsed_live_blogs.close()
    a.close()
    conn.close()


def new_script_extract_the_guardian_content(extractor, folder, database, json_filename, problem_file):
    """
    opens the database, THE_GUARDIAN_COMPLETE_live_blogs.db, stores the urls and parsed contents inside a json file.
    :param extractor:
    :param folder:
    :param database:
    :param json_filename: must finish with ".json
    :param problem_file: file where we store the urls which gave problems
    :return:
    """
    # it's to check the correctness of the json_filename
    assert json_filename[len(json_filename) - 5:] == ".json"

    # connection to the database and retrieval of the webpage and url
    conn = sqlite3.connect(os.path.join(".", folder, database))
    cursor = conn.cursor()
    cursor.execute("""SELECT id FROM THE_GUARDIAN_WEB_PAGES""")
    ids = cursor.fetchall()
    ids = [id_[0] for id_ in ids]
    print len(ids)
    # variable used to see the number of webpages processed
    azerty = 0
    parsed_live_blogs = codecs.open(os.path.join('.', folder, json_filename),
                                    'w',
                                    encoding="utf-8")  # file where the results are going to be stored
    one_live_blog = {}
    for id_ in ids:
        cursor.execute("""SELECT webpage, url FROM THE_GUARDIAN_WEB_PAGES WHERE id=?""", (str(id_),))
        webpage, url = cursor.fetchone()
        if len(webpage) == 1:
            webpage = webpage[0]
        try:
            one_live_blog = extractor(url, webpage, id_)
            if accept_extraction(one_live_blog):
                line = json.dumps(one_live_blog, ensure_ascii=False) + "\n"
                parsed_live_blogs.write(line)
        except TypeError:
            print "erreur"
            print one_live_blog
            print id_
            print url
        # except IndexError:
        #     print url, id_


        if azerty % 100 == 0:
            print "we're here : ", azerty
        azerty += 1
    parsed_live_blogs.close()
    conn.close()


def get_d_next_urls(folder, database, json_filename):
    """
    USELESS (for now)
    :param folder:
    :param database:
    :param json_filename:
    :return:
    """
    urls_whose_page_correctly_parsed = []
    parsed_webpages = open_converted_json_data(os.path.join(folder, json_filename))

    for item in parsed_webpages:
        if "url" in item:
            urls_whose_page_correctly_parsed.append(item["url"])

    print "number of urls whose pages were correctly parsed", len(urls_whose_page_correctly_parsed)
    conn = sqlite3.connect(os.path.join(".", folder, database))
    cursor = conn.cursor()
    cursor.execute("""SELECT id FROM THE_GUARDIAN_WEB_PAGES""")
    ids = cursor.fetchall()
    ids = [id_[0] for id_ in ids]
    d_next_urls = {}
    azerty = 0
    print len(ids)
    for id_ in ids:
        cursor.execute("""SELECT webpage, url FROM THE_GUARDIAN_WEB_PAGES WHERE id=?""", (str(id_),))
        webpage, url = cursor.fetchone()
        if len(webpage) == 1:
            webpage = webpage[0]
        tree = html.fromstring(webpage)
        del webpage
        next_url = ""
        older_part = tree.xpath('//a[@data-link-name="older page"]')
        if len(older_part) >= 1:
            older_part_link = older_part[0].xpath('.//@href')
            if len(older_part_link) >= 1:
                next_url = "http://www.theguardian.com" + older_part_link[0]
        if azerty % 100 == 0:
            print "number of url processed", azerty
        azerty += 1
        if remove_number_sign(url) in urls_whose_page_correctly_parsed and remove_number_sign(next_url) \
                in urls_whose_page_correctly_parsed:  # The big problem est ici
            d_next_urls[remove_number_sign(url)] = remove_number_sign(next_url)
    return d_next_urls


def check_url_in_json_file(folder, json_filename, url="http://www.theguardian.com/football/live/2016/feb/28/"):
    """
    checks if a url is present in a live blog inside the json file
    :param folder:
    :param json_filename:
    :param url:
    :return:
    """
    # tottenham-hotspur-v-swansea-city-premier-league-live
    # with open(os.path.join(folder, json_filename), "rb") as f:
    #     res = f.read()
    # parsed_webpages = json.loads(res, encoding="utf-8")
    parsed_webpages = open_converted_json_data(os.path.join(folder, json_filename))
    for item in parsed_webpages:
        if "url" in item:
            if url in remove_number_sign(item["url"]):
                print item["url"]


def script_merge_webpages_to_liveblogs(folder, json_filename_first_parsed, json_filename_second_parsed):
    """

    :param folder: where we get and store data
    :param json_filename_first_parsed: the name of the file where the unmerged live blogs are
    :param json_filename_second_parsed: the name of the file where the new json file must be stored
    :return: NOTHING
    """
    parsed_webpages = open_converted_json_data(os.path.join(folder, json_filename_first_parsed))
    res = []  # the result !

    d_url_ind = get_d_url_ind(parsed_webpages)
    type_problem = 0
    l_webpage_to_keep = set()
    print "dictionnaire d_url_ind construit"
    for item in parsed_webpages:
        if "url" in item:
            url = item["url"]
            database_id = item["database_id"]
            rurl = remove_question_mark(item["url"])
            if rurl != url:  # it means that it's not a first page of something, if it's an other page of a main page
                if rurl in d_url_ind.keys():
                    d_first_page = parsed_webpages[d_url_ind[rurl]]
                    d_other_page = parsed_webpages[d_url_ind[url]]
                if "documents" in d_first_page and "documents" in d_other_page:
                    # it's due to a bad parsing
                    if d_first_page["documents"] is not None and d_other_page['documents'] is not None:
                        d_first_page["documents"].extend(d_other_page["documents"])
                        parsed_webpages[d_url_ind[rurl]]["documents"] = d_first_page["documents"]
                        if "other-urls" not in parsed_webpages[d_url_ind[rurl]]:
                            parsed_webpages[d_url_ind[rurl]]["other-urls"] = [{"url": url, "database_id": database_id}]
                        else:
                            parsed_webpages[d_url_ind[rurl]]["other-urls"].append({"url": url, "database_id": database_id})
                    else:
                        type_problem += 1
                else:
                    type_problem += 1
            else:
                l_webpage_to_keep.add(d_url_ind[rurl])
    for i in l_webpage_to_keep:
        res.append(parsed_webpages[i])
    print "merging achieved"
    # Text Normalisation
    for lb in res:
        for doc in lb["documents"]:
            if type(doc["text"]) == list:
                text = ""
                for part in doc["text"]:
                    text += " " + part
                doc["text"] = text_normalization(text)
            elif type(doc["text"]) == unicode:
                lb["documents"]["text"] = text_normalization(lb["documents"]["text"])
            else:
                print "PROBLEM !!!!!!!!!!!"
    print "text normalisation done"
    store_converted_json_data(os.path.join(folder, json_filename_second_parsed), res)


def new_new_script_merge_webpages_to_liveblogs(folder, json_filename_first_parsed, json_filename_second_parsed):
    """

    :param folder: where we get and store data
    :param json_filename_first_parsed: the name of the file where the unmerged live blogs are
    :param json_filename_second_parsed: the name of the file where the new json file must be stored
    :return: NOTHING
    """
    temp = "temp.json"
    print "little cleaning"
    pw = new_open_converted_json_data_with_exception(json_filename_first_parsed, folder=folder)
    l = []
    for lb in pw:
        l.append(lb)
    store_converted_json_data(temp, l, folder)

    print "end of cleaning, beginning of merging"
    pw1 = new_open_converted_json_data(temp, folder=folder)
    lb_list = []
    for main_lb in pw1:
        url1 = main_lb["url"]
        rurl1 = remove_question_mark(url1)
        if url1 == rurl1:
            pw2 = new_open_converted_json_data(temp, folder=folder)
            for other_page_lb in pw2:
                url2 = other_page_lb["url"]
                rurl2 = remove_question_mark(url2)
                if url1 == rurl2 and url2 != rurl2:
                    if main_lb["documents"] is not None and other_page_lb['documents'] is not None:
                        main_lb["documents"].extend(other_page_lb["documents"])
                        # what is added to the first page !

                        main_lb["summary"]["summary_with_bullets"].extend(other_page_lb["summary"]["summary_with_bullets"])

                        main_lb["summary"]["summary_without_bullets"].extend(other_page_lb["summary"]["summary_without_bullets"])
                        main_lb["summary"]["key_point_with_bullets"].extend(other_page_lb["summary"]["key_point_with_bullets"])
                        main_lb["summary"]["key_point_without_bullets"].extend(other_page_lb["summary"]["key_point_without_bullets"])
                        if "other-urls" not in main_lb:
                            main_lb["other-urls"] = [{"url": other_page_lb["url"], "database_id": other_page_lb["database_id"]}]
                        else:
                            main_lb["other-urls"].append({"url": other_page_lb["url"], "database_id": other_page_lb["database_id"]})
            lb_list.append(main_lb)
    print "merging achieved"
    # Text Normalisation
    for lb in lb_list:
        for doc in lb["documents"]:
            if type(doc["text"]) == list:
                text = ""
                for part in doc["text"]:
                    text += " " + part
                doc["text"] = text_normalization(text)
            elif type(doc["text"]) == unicode or type(doc["text"]) == str:
                lb["documents"]["text"] = text_normalization(lb["documents"]["text"])
            else:
                print "PROBLEM !!!!!!!!!!!"
    print "text normalisation done"
    store_converted_json_data(os.path.join(folder, json_filename_second_parsed), lb_list)


def new_script_merge_webpages_to_liveblogs(folder, json_filename_first_parsed, json_filename_second_parsed):
    """

    :param folder: where we get and store data
    :param json_filename_first_parsed: the name of the file where the unmerged live blogs are
    :param json_filename_second_parsed: the name of the file where the new json file must be stored
    :return: NOTHING
    """

    res = []  # the result !
    parsed_webpages = open_converted_json_data(os.path.join(folder, json_filename_first_parsed))
    d_url_ind = get_d_url_ind(parsed_webpages)
    type_problem = 0
    l_webpage_to_keep = set()
    print "dictionnaire d_url_ind construit"
    for item in parsed_webpages:
        if "url" in item:
            url = item["url"]
            database_id = item["database_id"]
            rurl = remove_question_mark(item["url"])
            if rurl != url:  # it means that it's not a first page of something, if it's an other page of a main page
                if rurl in d_url_ind.keys():
                    d_first_page = parsed_webpages[d_url_ind[rurl]]
                    d_other_page = parsed_webpages[d_url_ind[url]]
                if "documents" in d_first_page and "documents" in d_other_page:
                    # it's due to a bad parsing
                    if d_first_page["documents"] is not None and d_other_page['documents'] is not None:
                        d_first_page["documents"].extend(d_other_page["documents"])
                        # what is added to the first page !
                        parsed_webpages[d_url_ind[rurl]]["documents"] = d_first_page["documents"]

                        d_first_page["summary"]["summary_with_bullets"].extend(d_other_page["summary"]["summary_with_bullets"])
                        parsed_webpages[d_url_ind[rurl]]["summary"]["summary_with_bullets"] = d_first_page["summary"]["summary_with_bullets"]

                        d_first_page["summary"]["summary_without_bullets"].extend(d_other_page["summary"]["summary_without_bullets"])
                        parsed_webpages[d_url_ind[rurl]]["summary"]["summary_without_bullets"] = d_first_page["summary"]["summary_without_bullets"]

                        d_first_page["summary"]["key_point_with_bullets"].extend(d_other_page["summary"]["key_point_with_bullets"])
                        parsed_webpages[d_url_ind[rurl]]["summary"]["key_point_with_bullets"] = d_first_page["summary"]["key_point_with_bullets"]

                        d_first_page["summary"]["key_point_without_bullets"].extend(d_other_page["summary"]["key_point_without_bullets"])
                        parsed_webpages[d_url_ind[rurl]]["summary"]["key_point_without_bullets"] = d_first_page["summary"]["key_point_without_bullets"]

                        if "other-urls" not in parsed_webpages[d_url_ind[rurl]]:
                            parsed_webpages[d_url_ind[rurl]]["other-urls"] = [{"url": url, "database_id": database_id}]
                        else:
                            parsed_webpages[d_url_ind[rurl]]["other-urls"].append({"url": url, "database_id": database_id})
                    else:
                        type_problem += 1
                else:
                    type_problem += 1
            else:
                l_webpage_to_keep.add(d_url_ind[rurl])
    for i in l_webpage_to_keep:
        res.append(parsed_webpages[i])
    print "merging achieved"
    # Text Normalisation
    for lb in res:
        lb["documents"] = sort_dates_hour_for_live_blog(lb["documents"])
        for doc in lb["documents"]:
            if type(doc["text"]) == list:
                text = ""
                for part in doc["text"]:
                    text += " " + part
                doc["text"] = text_normalization(text)
            elif type(doc["text"]) == unicode or type(doc["text"]) == str:
                lb["documents"]["text"] = text_normalization(lb["documents"]["text"])
            else:
                print "PROBLEM !!!!!!!!!!!"
    print "text normalisation done"
    store_converted_json_data(os.path.join(folder, json_filename_second_parsed), res)
    print "finished here"


def accept_extraction(live_blog):
    """
    USELESS
    Must be used if we want to have 100% useful live blogs in the parsed json file
    :param live_blog:
    :return:
    """
    assert type(live_blog) == dict
    return True  # len(live_blog["summary"]) != 0


def guardian_extractor_from_web(url="https://www.theguardian.com/business/blog/2014/jun/02/manufacturing-pmis-factory-output-china-germany-france-live"):
    """

    :param url: use
    :return:
    """
    webpage = get(url).text
    # print repr(webpage)
    # print webpage
    # the_guardian_extractor(url, webpage.content)
    with open("asupprimer.html", "w") as f:
        f.write(webpage.encode("utf8"))
    return webpage


def new_post_merge_process(folder, json_filename, output_json_filename):

    # parsed_liveblogs = open_converted_json_data(os.path.join(".", folder, json_filename))
    parsed_liveblogs = open_converted_json_data(os.path.join(folder, json_filename))

    lb_to_keep = []
    lb_to_keep_1 = []
    lb_to_keep_2 = []
    lb_to_keep_3 = []
    lb_to_keep_4 = []

    # Control variables
    azerty = 0
    for lb in parsed_liveblogs:
        if azerty % 100 == 0:
            print 'azerty', azerty
            print len(lb_to_keep_1)
            print len(lb_to_keep_2)
            print len(lb_to_keep_3)
            print len(lb_to_keep_4)
            # print "number_of_liveblog_removed_because_of_bad_title", number_of_liveblog_removed_because_of_bad_title
            # print "number_of_liveblog_removed_because_of_genre", number_of_liveblog_removed_because_of_genre
            # print "number_summary_with_bullets_0", number_summary_with_and_without_bullets_0
            # print "number_documents_less_5", number_documents_less_5
        azerty += 1
        if len(lb["summary"]["summary_with_bullets"]) != 0:
            lb["chosen_summary"] = lb["summary"]["summary_with_bullets"]
            lb["quality"] = 1
            lb_to_keep_1.append(lb)
        elif len(lb["summary"]["summary_without_bullets"]) != 0:
            lb["chosen_summary"] = lb["summary"]["summary_without_bullets"]
            lb["quality"] = 2
            lb_to_keep_2.append(lb)
        elif len(lb["summary"]["key_point_with_bullets"]) != 0:
            lb["chosen_summary"] = lb["summary"]["key_point_with_bullets"]
            lb["quality"] = 3
            lb_to_keep_3.append(lb)
        elif len(lb["summary"]["key_point_without_bullets"]) != 0:
            lb["chosen_summary"] = lb["summary"]["key_point_without_bullets"]
            lb["quality"] = 4
            lb_to_keep_4.append(lb)

        # if "chosen_summary" in lb:
        #     lb_to_keep.append(lb)

        # lb["summary"]["summary_without_bullets"]
        # lb["summary"]["key_point_with_bullets"]
        # lb["summary"]["key_point_without_bullets"]
    print "total", azerty
    # print "number_of_liveblog_removed_because_of_bad_title", number_of_liveblog_removed_because_of_bad_title
    # print "number_of_liveblog_removed_because_of_genre", number_of_liveblog_removed_because_of_genre
    # print "number_summary_with_bullets_0", number_summary_with_and_without_bullets_0
    # print "number_documents_less_5", number_documents_less_5
    # store_converted_json_data(os.path.join('.', folder, output_json_filename), lb_to_keep)
    store_converted_json_data(os.path.join('.', folder, "one_"+output_json_filename), lb_to_keep_1)
    store_converted_json_data(os.path.join('.', folder, "two_"+output_json_filename), lb_to_keep_2)
    store_converted_json_data(os.path.join('.', folder, "three_"+output_json_filename), lb_to_keep_3)
    store_converted_json_data(os.path.join('.', folder, "four_"+output_json_filename), lb_to_keep_4)
    print len(lb_to_keep)


def post_merge_process(folder, json_filename, output_json_filename, database):
    """
    (1) Key points on the top (the top key points may be informative, but not often and there are always at least one sentence which is just noise for us).
    (2) Key points on the left and linked to the blocks in the live blog (the key points are never correct sentences, the only interesting contents are the links to blocks)
        (a) Blocks have bullet points
             (i) Bullets have highlights (bold) text. (Consider the first sentence)
             (ii) No highlights then consider the first sentence
          (b) No bullets, then consider everything
    (3) Key points on the top linked to the blocks in the live blog.
          (a) Blocks have bullet points
             (i) Bullets have highlights (bold) text. (Consider the first sentence)
             (ii) No highlights then consider the first sentence
          (b) No bullets, then consider everything
    (4) If not the above look for the keywords as mentioned. (That case is really hard because defining the delimiters of the "summary" inside)
    (5) None of the above
    :param folder:
    :param json_filename:
    :param output_json_filename:
    :param database:
    :return:
    """
    def bad_title(title):
        if type(title) == list:
            return re.match("webchat", title[0]) is not None or re.match("Q&A", title[0]) is not None
        else:
            return re.match("webchat", title) is not None or re.match("Q&A", title) is not None

    def keep_live_blog_from_url(link):
        accepted_genres = ["business", "news", "politics", "uk-news", "us-news", "world", "technology"]
        genre = link.split("/")[3]
        return genre in accepted_genres

    def get_text_for_summary(text_html):
        # source_title = text_html.xpath('.//h2[@class="block-title"]/text()')
        lis = text_html.xpath('.//li')
        for_summary = []
        # links_for_summary =[]
        # for li in lis:
        #     strongs = li.xpath('.//strong')
        #     if len(strongs) != 0:
        #         # print html.tostring(li)
        #         sentence = sent_tokenize(li.text_content())  # BeautifulSoup(html.tostring(li), "html.parser").get_text()
        #         if len(sentence) != 0:
        #             for_summary.append(sentence[0])
        for li in lis:
            # print html.tostring(li)
            sentence = sent_tokenize(li.text_content())  # BeautifulSoup(html.tostring(li), "html.parser").get_text()
            if len(sentence) != 0:
                for_summary.append(sentence[0])
                # for link in strongs[0].xpath(".//a"):
                # print BeautifulSoup(html.tostring(li), "html.parser").get_text()
                # useless
                # lin = re.findall(r'https?://[a-z\.]+/[A-Za-z\-_0-9/]+', html.tostring(li))
                # lin.extend(re.findall(r'https?://[a-z\.]+/[A-Za-z\-_0-9/]+\.[a-z]{2,5}', html.tostring(li)))
                # if len(lin) == 1:
                #     links_for_summary.extend(lin)
        # print "source_title", source_title
        # print "for_summary", for_summary
        # print "links_for_summary", links_for_summary
        # print for_summary
        return for_summary

    def get_text_for_summary_without_bullet_point(text_html):
        article_body = text_html.xpath('.//div[@itemprop="liveBlogUpdate"]')
        for_summary = []
        # links_for_summary =[]
        # for li in lis:
        #     strongs = li.xpath('.//strong')
        #     if len(strongs) != 0:
        #         # print html.tostring(li)
        #         sentence = sent_tokenize(li.text_content())  # BeautifulSoup(html.tostring(li), "html.parser").get_text()
        #         if len(sentence) != 0:
        #             for_summary.append(sentence[0])
        for ab in article_body:
            # print html.tostring(li)
            for_summary.append(ab.text_content())
            # if ab.tag == "p":
            #     sentence = sent_tokenize(ab.text_content())  # BeautifulSoup(html.tostring(li), "html.parser").get_text()
            #     if len(sentence) != 0:
            #         for_summary.append(sentence[0])
            #         break
        # print for_summary
        return for_summary

    accepted_cases = [1, 2, 3] # The different cases we want for our corpus
    # complete_summaries formation
    conn = sqlite3.connect(os.path.join(".", folder, database))
    cursor = conn.cursor()
    parsed_liveblogs = open_converted_json_data(os.path.join(".", folder, json_filename))
    lb_to_keep = []
    print "dictionnaire d_url_ind construit"
    # Counters
    azerty = 0
    compteur_cas_3 = 0
    l_compteur = []
    s_compteur = set()
    compteur_ke = 0
    compteur_bloc_inaccessible = 0
    compteur_bloc_infructueux = 0
    compteur_cas_2 = 0
    l_nombre_potentiel_resume_avec_key_events = []
    s_nombre_potentiel_resume_avec_key_events = set()
    compteur_cas_1 = 0
    s_nombre_cas_1 = []
    compteur_cas_4 = 0
    # compteur_other_links = 0
    number_of_liveblog_removed_because_of_genre = 0
    number_of_liveblog_removed_because_of_bad_title = 0
    compteur_key_events = 0
    # number_bad_title = 0
    print len(parsed_liveblogs)
    for lb in parsed_liveblogs:
        url = lb["url"]
        # Measures
        if azerty % 100 == 0:
            print azerty
            print "compteur_cas_3 : ", compteur_cas_3
            print "compteur key event : ", compteur_ke
            print "bloc infructueux : ", compteur_bloc_infructueux
            print "compteur_bloc_inaccessible : ", compteur_bloc_inaccessible
            print "compteur_cas_2 : ", compteur_cas_2
            print "compteur_passe_cas_1", compteur_cas_1
            print "compteur_cas_4", compteur_cas_4
            # print "compteur_other_links", compteur_other_links
            print "compteur_key_events", compteur_key_events
            print "number_of_liveblog_removed_because_of_genre", number_of_liveblog_removed_because_of_genre
            print "number_of_liveblog_removed_because_of_bad_title", number_of_liveblog_removed_because_of_bad_title
        azerty += 1
        # pruning
        if not keep_live_blog_from_url(url):
            number_of_liveblog_removed_because_of_genre += 1
            continue
        if bad_title(lb["title"]):
            number_of_liveblog_removed_because_of_bad_title += 1
            continue
        if "other-urls" in lb:
            other_urls = lb["other-urls"]
        else:
            other_urls = []

        id_ = lb["database_id"]
        ids = [id_]
        blocks = [source["block_id"] for source in lb["documents"] if source["block_id"] is not None]
        # We retrieve the ids of the blocks
        blocks_webpage = []
        articles = []
        # we get the database id from the other pages of the live blog
        for o_url in other_urls:
            ids.append(o_url["database_id"])
        for i in ids:
            # database to get exactly what we want from the source
            cursor.execute("""SELECT webpage FROM THE_GUARDIAN_WEB_PAGES WHERE id=?""", (i, ))
            webpage = cursor.fetchone()
            if len(webpage) == 1:
                webpage = webpage[0]
            tree = html.fromstring(webpage)

            page_articles = tree.xpath('.//div[@itemprop="liveBlogUpdate"]')
            blocks_webpage.extend([article.get("id") for article in page_articles])
            articles.extend(page_articles)
            del webpage
            del tree
        # CASE 3
        # passe_other_links = False
        for line in lb["summary"]["head_summary"]:
            for link in line["link"]:
                if link is not None:
                    if remove_question_mar_and_number_sign(link) == url:
                        block = extract_source_block_gua(link)
                        if block in blocks and block in blocks_webpage:
                            index = blocks_webpage.index(block)
                            for_summary = get_text_for_summary(articles[index])  # case 3 a
                            for sent in for_summary:
                                lb["summary"]["complete_summary"].extend(sent_tokenize(text_normalization(sent)))
                            if len(for_summary) != 0:
                                pass
                            else:
                                for_summary = get_text_for_summary_without_bullet_point(articles[blocks_webpage.index(block)])  # case 3 b
                                for sent in for_summary:
                                    lb["summary"]["complete_summary"].extend(sent_tokenize(text_normalization(sent)))
                    else:
                        pass
                        # passe_other_links = True
                else:
                    # That case occurs when the link taken from the top is a link pointing to an other web page of
                    # the Guardian but not to a web page of the same live blog
                    print lb["summary"], lb["url"]
        if len(lb["summary"]["complete_summary"]) != 0:
            lb["summary"]["case"] = 3
            compteur_cas_3 += 1
            s_compteur.add(id_)
        # if passe_other_links:
        #     compteur_other_links += 1

        l_compteur.append(compteur_cas_3)
        # CASE 2
        for key_event_link in lb["summary"]["key_events_links_and_text"]:
            block = key_event_link["block"]
            if block in blocks and block in blocks_webpage:
                for_summary = get_text_for_summary(articles[blocks_webpage.index(block)])  # case 2 a
                for sent in for_summary:
                    lb["summary"]["key_events"].extend(sent_tokenize(text_normalization(sent)))
                if len(for_summary) != 0:
                    compteur_ke += 1
                else:
                    for_summary = get_text_for_summary_without_bullet_point(articles[blocks_webpage.index(block)])  # case 2 b
                    for sent in for_summary:
                        lb["summary"]["key_events"].extend(sent_tokenize(text_normalization(sent)))
                    if len(for_summary) != 0:
                        compteur_ke += 1
                    else:
                        compteur_bloc_infructueux += 1
            else:
                compteur_bloc_inaccessible += 1

        # if not case 3, then case 2
        if len(lb["summary"]["key_events"]) != 0:
            if len(lb["summary"]["complete_summary"]) == 0:
                lb["summary"]["complete_summary"] = lb["summary"]["key_events"]
                lb["summary"]["case"] = 2
                compteur_cas_2 += 1
                s_nombre_potentiel_resume_avec_key_events.add(id_)
            compteur_key_events += 1
        l_nombre_potentiel_resume_avec_key_events.append(compteur_key_events)

        # CASE 1
        if len(lb["summary"]["complete_summary"]) == 0:
            passe = False
            for line in lb["summary"]["head_summary"]:
                lb["summary"]["complete_summary"].extend(sent_tokenize(summary_normalization(line["text"])))
                passe = True
            if passe:
                s_nombre_cas_1.append(lb["database_id"])
                compteur_cas_1 += 1
                lb["summary"]["case"] = 1

        # CASE 4
        if len(lb["summary"]["complete_summary"]) == 0:
            compteur_cas_4 += 1
            lb["summary"]["case"] = 4
        # print lb["summary"]["complete_summary"], lb["database_id"], lb["summary"]["case"]

        if "case" in lb["summary"]:
            case = lb['summary']["case"]
            if case in accepted_cases:
                lb_to_keep.append(lb)



    print "merging for summaries achieved"
    store_converted_json_data(os.path.join('.', folder, output_json_filename), lb_to_keep)
    if True:  # TODO
        print date.today()
        maxi_ke = max(s_nombre_potentiel_resume_avec_key_events)
        print "s_nombre_potentiel_resume_avec_key_events max et url : ", maxi_ke
        maxi_compteur = max(s_compteur)
        print "s_compteur max et url :", maxi_compteur
        print "s_nombre_potentiel_resume_avec_key_events", len(s_nombre_potentiel_resume_avec_key_events)
        print "l_nombre_potentiel_resume_avec_key_events", len(l_nombre_potentiel_resume_avec_key_events)
        print "s_compteur", len(s_compteur)
        print "compteur_cas_3 : ", compteur_cas_3
        print "s_compteur inter s_nombre_potentiel_resume_avec_key_events", len(
            s_nombre_potentiel_resume_avec_key_events.intersection(s_compteur))
        print "s_nombre_cas_1", len(s_nombre_cas_1)
        print "compteur_cas_4", compteur_cas_4
        # print "compteur_other_links", compteur_other_links
        print "number_of_liveblog_removed_because_of_genre", number_of_liveblog_removed_because_of_genre
        print "number_of_liveblog_removed_because_of_bad_title", number_of_liveblog_removed_because_of_bad_title
        # print s_nombre_cas_1[:100]
        plt.plot(l_nombre_potentiel_resume_avec_key_events)
        plt.xlabel("Number of fetched the Guardian live blog urls")
        plt.ylabel('blabla')
        plt.title("Number of live blogs which have links in key events pointing to blocks with a successful extraction")
        plt.show()
        plt.plot(l_compteur)
        plt.xlabel("Number of fetched the Guardian live blog urls")
        plt.ylabel('blabla')
        plt.title("Number of live blogs who have links pointing to blocks with a successful extraction")
        plt.show()
    conn.close()


def summary_normalization(summary):
    try:
        summary = unicode(summary)
    except:
        pass
    if type(summary) == unicode or type(summary) == str:
        summary = re.sub("([.?!]);","\\1", summary)
        summary = re.sub(r'[\n\s\t\r_]+', ' ', summary)
        summary = re.sub(r"\.+", ".", summary)  # pas nécessairement bon
        summary = re.sub(r"[*]", "", summary)
        # summary = re.sub(r"\-+", "-", summary)
        summary = re.sub(r"\\u00A0", " ", summary)
        summary = re.sub(r"\u00A0", " ", summary)
        summary = re.sub(r'^ ', '', summary)  # spaces at the beginning are removed
        summary = re.sub(r' +$', '', summary)  # spaces at the end are removed
        summary = re.sub(r" {2,10}", ". ", summary)
        if summary != u"":
            last_character = summary[-1]
            summary = re.sub(r'[a-zA-Z]$', last_character+".", summary)  # sentences should finish with a point
        summary.replace(u'\xa0', u' ')
    else:
        print summary, type(summary)
    return summary


def text_normalization(text):
    """
    :param text:
    :return:
    """
    try:
        text = unicode(text)
    except:
        pass
    if type(text) == unicode or type(text) == str:
        text = re.sub(r'pic\.twitter\.com/[a-zA-Z0-9]+', "", text)
        text = re.sub("([.?!]);", "\\1", text)  # .; ?; !; are removed
        text = re.sub(r'[\n\s\t\r_]+', ' ', text)  # combination of newlines, tabs or other invisible characters are transformed into spaces
        text = re.sub(r"\.+", ".", text)  # sequences of points are just one point
        text = re.sub(r"[*]", "", text) # we rmove the stars
        text = re.sub(r"\-+", "-", text)  #minus and plus are removed
        text = re.sub(r"\\u00A0", " ", text)
        text = re.sub(r"\u00A0", " ", text)
        text = re.sub(r'^ +', '', text)  # spaces at the beginning are removed
        text = re.sub(r' +$', '', text)  # spaces at the end are removed
        text = re.sub(r" {2,10}", ". ", text)
        if text != u"":
            last_character = text[-1]
            text = re.sub(r'[a-zA-Z]$', last_character+".", text)  # sentences should finish with a point
        text.replace(u'\xa0', u' ')
    else:
        print "probleme", type(text)
    return text.strip()


def normalize_live_blogs_gua(folder, json_filename, normalized_json_filename):
    """
    use text_normalization to normalize the contents of fields inside the json file
    and add "genre" field"
    :param folder:
    :param json_filename:
    :param normalized_json_filename:
    :return:
    """
    parsed_liveblogs = open_converted_json_data(os.path.join(".", folder, json_filename))
    # parsed_liveblogs = new_open_converted_json_data(os.path.join(folder, json_filename))
    l_lb_to_keep = []
    c = 0
    for lb in parsed_liveblogs:
        if "other-urls" not in lb:
            lb["other-urls"] = []
        l = []

        for summaries in lb["chosen_summary"]:
            text = " ".join(summaries["text"])
            summaries["text"] = sent_tokenize(text)
            l.append(summaries)
        lb["chosen_summary"] = l

        #Les nouveaux changements sont après
        times = set()
        for doc in lb["documents"]:
            # print doc, type(doc)
            # if "time" in doc:
            #     print "ça a le champ time"
            #     print doc["time"]
            times.add("-".join([str(i) for i in doc["time"]]))
        if len(times) < 5:
            c += 1
            continue

        for i in range(len(lb["documents"])):
            lb["documents"][i]["time_rank"] = i
        lb["summary"]["summary_with_bullets"] = sort_dates_hour_for_live_blog(lb["summary"]["summary_with_bullets"])
        for i in range(len(lb["summary"]["summary_with_bullets"])):
            lb["summary"]["summary_with_bullets"][i]["time_rank"] = i
        lb["summary"]["summary_without_bullets"] = sort_dates_hour_for_live_blog(lb["summary"]["summary_without_bullets"])
        for i in range(len(lb["summary"]["summary_without_bullets"])):
            lb["summary"]["summary_without_bullets"][i]["time_rank"] = i
        lb["summary"]["key_point_with_bullets"] = sort_dates_hour_for_live_blog(lb["summary"]["key_point_with_bullets"])
        for i in range(len(lb["summary"]["key_point_with_bullets"])):
            lb["summary"]["key_point_with_bullets"][i]["time_rank"] = i
        lb["summary"]["key_point_without_bullets"] = sort_dates_hour_for_live_blog(lb["summary"]["key_point_without_bullets"])
        for i in range(len(lb["summary"]["key_point_without_bullets"])):
            lb["summary"]["key_point_without_bullets"][i]["time_rank"] = i

        lb["chosen_summary"] = sort_dates_hour_for_live_blog(lb["chosen_summary"])
        for i in range(len(lb["chosen_summary"])):
            lb["chosen_summary"][i]["time_rank"] = i

        l_lb_to_keep.append(lb)



        # compter le nombre de bloc qui n'a pas d'identifiant
        # times = set()
        # compteur_sans_bloc_id = 0
        # for doc in lb["documents"]:
        #     times.add(doc["time"]["complete"])
        #     if doc["block_id"] is None:
        #         compteur_sans_bloc_id += 1
        # l_compteur_sans_bloc_id.append(compteur_sans_bloc_id)
        # print "rapport lb"
        # print lb["database_id"], "sans bloc id", compteur_sans_bloc_id
        # print "nombre de temps différents : "+str(len(times))
        # print times
        # plt.hist(l_compteur_sans_bloc_id)
        # plt.xlabel('l_compteur_sans_bloc_id')
        # plt.ylabel(u'Number of live blogs')
        # plt.axis([0, 200, 0, 1000])
        # plt.grid(True)
        # # plt.savefig("days_bbc_liveblogs_through_years.png")
        # plt.show()
    print "nombre de lb supprimé à cause du temps mauvais", c
    print "nombre de live blogs conservés", len(l_lb_to_keep)
    store_converted_json_data(normalized_json_filename, l_lb_to_keep, folder)


def main1():
    script_extract_the_guardian_content(the_guardian_extractor, FOLDER, DATABASE, JSON_FILENAME,
                                        SUMMARY_PROBLEM)  # 18 minutes
    script_merge_webpages_to_liveblogs(FOLDER, JSON_FILENAME, JSON_LIVEBLOGS_FILENAME)
    keep_clean_parsed_liveblogs(FOLDER, JSON_LIVEBLOGS_FILENAME, GUA_JSON_CLEAN_LIVEBLOGS_FILENAME, "GUA")
    post_merge_process(FOLDER, JSON_LIVEBLOGS_FILENAME, GUA_JSON_POST_LIVEBLOGS_FILENAME, DATABASE)
    normalize_live_blogs_gua(FOLDER, GUA_JSON_CLEAN_LIVEBLOGS_FILENAME, GUA_JSON_NOR_LIVEBLOGS_FILENAME)


def main2():
    """
    # new_new_script_merge_webpages_to_liveblogs(FOLDER, JSON_FILENAME, JSON_LIVEBLOGS_FILENAME)
    :return:
    """
    new_script_extract_the_guardian_content(new_gua_extractor, FOLDER, DATABASE, JSON_FILENAME,
                                            SUMMARY_PROBLEM)
    new_script_merge_webpages_to_liveblogs(FOLDER, JSON_FILENAME, JSON_LIVEBLOGS_FILENAME)
    new_post_merge_process(FOLDER, JSON_LIVEBLOGS_FILENAME, GUA_JSON_POST_LIVEBLOGS_FILENAME)
    for i in ["one", "two", "three", "four"]:
        print i
        gua_keep_good_liveblogs(FOLDER, i+"_"+GUA_JSON_POST_LIVEBLOGS_FILENAME, i+"_"+GUA_JSON_CLEAN_LIVEBLOGS_FILENAME)
    for i in ["one", "two", "three", "four"]:
        print i
        normalize_live_blogs_gua(FOLDER, i+"_"+GUA_JSON_CLEAN_LIVEBLOGS_FILENAME, i+"_"+GUA_JSON_NOR_LIVEBLOGS_FILENAME)

if __name__ == "__main__":
    FOLDER = "guardian_extraction/data_guardian"  # where the data are stored
    JSON_FILENAME = "the_guardian_articles_parsed.json"  # file where all the interesting contents are put
    DATABASE = "THE_GUARDIAN_COMPLETE_live_blogs.db"  # database where the webpages of the Guardian
    SUMMARY_PROBLEM = "summary_problem.txt"
    TEXT_PROBLEM = "text_problem.txt"
    JSON_LIVEBLOGS_FILENAME = "the_guardian_parsed_liveblogs.json"

    GUA_JSON_POST_LIVEBLOGS_FILENAME = "post_the_guardian_liveblogs.json"
    GUA_JSON_CLEAN_LIVEBLOGS_FILENAME = "post_the_guardian_clean_liveblogs.json"

    GUA_JSON_NOR_LIVEBLOGS_FILENAME = "nor_post_the_guardian_clean_liveblogs.json"
    # test(extra_simpli, FOLDER, DATABASE)
    # guardian_extractor_from_web()
    main2()
    # normalize_live_blogs_gua(FOLDER, "one_"+GUA_JSON_CLEAN_LIVEBLOGS_FILENAME, "one_"+GUA_JSON_NOR_LIVEBLOGS_FILENAME)


