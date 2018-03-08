from lxml import html
import requests
import socket
from multiprocessing.pool import Pool
from multiprocessing.pool import ThreadPool
import hashlib
import os, errno
import re
import time
import argparse
import math
from itertools import izip
from itertools import repeat
import json
from selenium import webdriver

import os.path as path
import sys

base_dir = path.dirname(path.abspath(__file__))
driver_path = base_dir + '/driver/chromedriver'
sys.path.append(base_dir)

from utils.guardian import process_html_guardian, get_documents_guardian
from utils.bbc import process_html_bbc
from utils.misc import mkdirp
from utils.misc import ProgressBar

def WriteUrls(filename, urls):
    """Writes a list of URLs to a file.
    Args:
        filename: The filename to the file where the URLs should be written.
        urls: The list of URLs to write.
    """

    with open(filename, 'w') as f:
        f.writelines(url + '\n' for url in urls)

wayback_pattern = re.compile(r'web/([^/]*)/')

def WaybackUrl(urls, max_attempts=6):
    """Retrieves the URL for the latest historic copy using Wayback Machine.
    Args:
            urls: The URL for a specific page (canonical URL + forwarding URL's).
            max_attempts: The maximum attempts at requesting the URL.
    Returns:
            The URL or None if no copy is stored for the URL.
    Raises:
            RuntimeError: Failed to retrieve the URL.
    """

    if not urls:
            return None

    url = urls[0]

    index_collection_url = 'http://archive.org/wayback/available'

    payload = {'url': url}

    attempts = 0

    while attempts < max_attempts:
        try:
            entry_req = requests.get(index_collection_url, params=payload, 
                                     allow_redirects=False)

            if entry_req.status_code != requests.codes.ok:
                return WaybackUrl(urls[1:], max_attempts)

            entry = entry_req.json()

            if 'closest' not in entry['archived_snapshots']:
                return WaybackUrl(urls[1:], max_attempts)

            wayback_url = entry['archived_snapshots']['closest']['url']
            wayback_url = wayback_pattern.sub(r'web/\g<1>id_/', wayback_url, 1)
            return wayback_url

        except requests.exceptions.ConnectionError:
                pass

        # Exponential back-off.
        time.sleep(math.pow(2, attempts))
        attempts += 1

    raise RuntimeError('Failed to download URL for %s after %d attempts.'
                       'Please run the script again.' %
                       (url, max_attempts))

def Hashhex(s):
    """Returns a heximal formated SHA1 hash of the input string.
    Args:
        s: The string to hash.
    Returns:
        A heximal formatted hash of the input string.
    """

    h = hashlib.sha1()
    h.update(s)
    return h.hexdigest()

def ReadMultipleUrls(filename):
    """Reads a list of URL lists.
    Each line in the filename should contain a list of URLs separated by comma.
    Args:
        filename: The filename containing the URLs.
    Returns:
        A list of list of URLs.
    """
    with open(filename) as f:
        return [line.strip('\n').split(',') for line in f]


def GetNextPage(content, corpus):
    """Reads the content of a live blog and returns the url of the next page of the live blog.
    Args:
        content: html content of a live blog
        corpus: The corpus name of the live blog (eg. bbc, guardian)
    Returns:
        The url of the next page.
    """
    
    tree = html.fromstring(content)
    
    if corpus == 'guardian':
        older_part = tree.xpath('//div[@class="liveblog-navigation__older"]')
        
    url = ''
    if len(older_part) >= 1:
        older_part_link = older_part[0].xpath(".//a")[0].get("href")
        if older_part_link:
            if corpus == 'guardian':
                url = "http://www.theguardian.com" + older_part_link[:older_part_link.rfind('#')]
    return url

def extend_url(url, web_driver, corpus):
    """When the content is spread across multiple ajax pages.
    Reads the content of a bbc live blog and returns the html content of all the updates.
    Args:
        url: Url of a live blog
        driver: The selenium web driver to do dynamic crawling.
    Returns:
        The html content of the overall live blog.
    """
    
    web_driver.get(url)
    while(1):
        try:
            if corpus == 'bbc':
                web_driver.find_elements_by_xpath('//div[@class="lx-stream__show-more lx-stream-show-more"]/button')[0].click()
        except:
            break
    return web_driver.page_source
    

def extend_guardian_docs(url, content, corpus, json_docs):
    #Loop over next pages to append the documents list
    while(1):
        url = GetNextPage(content, corpus)
        if url:
            req = requests.get(url, allow_redirects=True, timeout=5)
            if req.status_code == requests.codes.ok:
                content = req.text.encode(req.encoding)
                tree = html.fromstring(content)
                block_data = get_documents_guardian(tree)
                for item in block_data:
                    json_docs.append(item)
        else:
            break
    return json_docs


def DownloadUrl(data_path, url, corpus, web_driver=None, max_attempts=5, timeout=5, ):
        """Downloads a URL.

        Args:
                url: The URL.
                corpus: The corpus of the URL.
                max_attempts: Max attempts for downloading the URL.
                timeout: Connection timeout in seconds for each attempt.

        Returns:
                The HTML at the URL or None if the request failed.
        """

        attempts = 0

        while attempts < max_attempts:
            try:
                hash_val = Hashhex(url)
                filename = '%s/downloads/%s/%s.json' % (data_path, corpus, hash_val)
                if os.path.exists(filename):
                    print('Skip, file already exists: %s' % (hash_val))
                    break
                
                if corpus == 'guardian':
                    req = requests.get(url, allow_redirects=True, timeout=timeout)
                    if req.status_code == requests.codes.ok:
                        content = req.text.encode(req.encoding) 
                        json_data = process_html_guardian(hash_val, url, content)
                        json_data['documents'] = extend_guardian_docs(url, content, corpus, json_data['documents'])
                    elif (req.status_code in [301, 302, 404, 503] and attempts == max_attempts - 1):
                        return None
                if corpus == 'bbc':
                    content = extend_url(url, web_driver, corpus)
                    json_data = process_html_bbc(hash_val, url, content)
                    
                with open(filename, 'w') as f:
                    f.write(json.dumps(json_data))
                        
                return json_data
                
            except requests.exceptions.ConnectionError:
                    pass
            except requests.exceptions.ContentDecodingError:
                    return None
            except requests.exceptions.ChunkedEncodingError:
                    return None
            except requests.exceptions.Timeout:
                    pass
            except socket.timeout:
                    pass

            # Exponential back-off.
            time.sleep(math.pow(2, attempts))
            attempts += 1

        return None


def UrlMode(data_path, corpus, request_parallelism):
    """Finds Wayback Machine URLs and writes them to disk.
    Args:
            corpus: A corpus.
            request_parallelism: The number of concurrent requests.
    """
    print 'Finding Wayback Machine URLs for the %s set:' % corpus
    old_urls_filename = '%s/urls/%s.txt' % (data_path, corpus)
    new_urls_filename = '%s/urls/wayback_%s_urls.txt' % (data_path, corpus)

    urls = ReadMultipleUrls(old_urls_filename)

    p = ThreadPool(request_parallelism)
    results = p.imap_unordered(WaybackUrl, urls)

    progress_bar = ProgressBar(len(urls))
    new_urls = []
    for result in results:
        if result:
            new_urls.append(result)

        progress_bar.Increment()

    WriteUrls(new_urls_filename, new_urls)

def DownloadMapper(t):
    """Downloads an URL and checks that metadata is available for the URL.
    Args:
            t: a tuple (data_path, url, corpus).
    Returns:
            A pair of URL and content.
    """

    data_path, url, corpus, web_driver = t

    return url, DownloadUrl(data_path, url, corpus, web_driver)

def ReadUrls(filename):
    """Reads a list of URLs.
    Args:
        filename: The filename containing the URLs.
    Returns:
        A list of URLs.
    """

    with open(filename) as f:
        return [line.strip('\n') for line in f]


def DownloadMode(data_path, corpus):
    """Downloads the URLs for the specified corpus.
    Args:
        corpus: A corpus.
        request_parallelism: The number of concurrent download requests.
    """
    web_driver = None
    if corpus == 'bbc':
        web_driver = webdriver.Chrome(driver_path)

    missing_urls = []
    
    print 'Downloading URLs for the %s set:' % corpus

    urls_filename = '%s/urls/%s_urls.txt' % (data_path, corpus)
    urls = ReadUrls(urls_filename)

    missing_urls_filename = '%s/urls/missing_%s_urls.txt' % (data_path, corpus)
    if os.path.exists(missing_urls_filename):
        print 'Only downloading missing URLs'
        urls = list(set(urls).intersection(ReadUrls(missing_urls_filename)))

    progress_bar = ProgressBar(len(urls))
    
    collected_urls = []
    try: 
        for url in urls:
            try:
                url, json_data = DownloadMapper((data_path, url, corpus, web_driver))
                collected_urls.append(url)
            except:
                pass
            progress_bar.Increment()
    
    except KeyboardInterrupt:
        if web_driver:
            web_driver.close()
        print 'Interrupted by user'

    missing_urls.extend(set(urls) - set(collected_urls))

    WriteUrls(missing_urls_filename, missing_urls)

    if missing_urls:
        print ('%d URLs couldn\'t be downloaded, see %s/missing_urls.txt.'
                     % (len(missing_urls), corpus))
        print 'Try and run the command again to download the missing URLs.'
                    
    if web_driver:
        web_driver.close()


def DownloadMode_parallel(data_path, corpus, request_parallelism):
    """Downloads the URLs for the specified corpus.
    Args:
        corpus: A corpus.
        request_parallelism: The number of concurrent download requests.
    """

    missing_urls = []

    print 'Downloading URLs for the %s set:' % corpus

    urls_filename = '%s/urls/wayback_%s_urls.txt' % (data_path, corpus)
    urls = ReadUrls(urls_filename)

    missing_urls_filename = '%s/missing_%s_urls.txt' % (data_path, corpus)
    if os.path.exists(missing_urls_filename):
        print 'Only downloading missing URLs'
        urls = list(set(urls).intersection(ReadUrls(missing_urls_filename)))

    p = ThreadPool(request_parallelism)
    results = p.imap_unordered(DownloadMapper, izip(repeat(data_path), urls, repeat(corpus)))

    progress_bar = ProgressBar(len(urls))

    collected_urls = []
    try:
        for url, story_html in results:
            if story_html:
                collected_urls.append(url)

            progress_bar.Increment()
    except KeyboardInterrupt:
        print 'Interrupted by user'

        missing_urls.extend(set(urls) - set(collected_urls))

    WriteUrls('%s/missing_urls.txt' % corpus, missing_urls)

    if missing_urls:
        print ('%d URLs couldn\'t be downloaded, see %s/missing_urls.txt.'
                     % (len(missing_urls), corpus))
        print 'Try and run the command again to download the missing URLs.'


def get_urls(corpus, tree, urls):
    """Given the content of a page and corpus type get all urls.
    Args:
        corpus: Name of the corpus (eg. bbc, guardian)
        tree: html content of the url
        urls: urls to be appended to
    Return:
        append the list of urls

    """

    if corpus == 'guardian':
        pattern = "www.theguardian.com"

    for item in tree.xpath("//a[@data-link-name='article']"):
        url = item.get("href")

        if re.search(pattern, url) and url not in urls: 
            urls.append(url)

    return urls

def BootCatUrls(seed_list):
    urls = []
    return urls

def FetchMode(data_path, corpus):
    """Get the URLs for the specified corpus.
    Args:
        corpus: A corpus.
    """
    urls = []
    urls_filename = '%s/urls/%s_urls.txt' % (data_path, corpus)

    if corpus == 'guardian':
        req_url = 'http://www.theguardian.com/tone/minutebyminute/?page=1'
        while(1): 
            print(req_url)
            req = requests.get(req_url, allow_redirects=True, timeout=5)
            if req.status_code == requests.codes.ok:
                content = req.text.encode(req.encoding) 
                tree = html.fromstring(content)    
                urls = get_urls(corpus, tree, urls)
                next_ref = tree.xpath("//a[@data-link-name='Pagination view next']")
                if next_ref:
                    req_url = next_ref[0].get("href")
                else:
                    break
            elif (req.status_code in [301, 302, 404, 503]):
                print(req.status_code)
                break  
    if corpus == 'bbc':
        urls = BootCatUrls()

    WriteUrls(urls_filename, list(set(urls)))

def main():
    parser = argparse.ArgumentParser(description='Generate the Summarization Corpus')
    parser.add_argument('--corpus', choices=['bbc', 'guardian'], required=True)
    parser.add_argument('--data_type', choices=['raw', 'processed'])
    parser.add_argument('--mode', choices=['fetch_urls', 'download', 'archive_urls'], required=True)
    parser.add_argument('--request_parallelism', type=int, default=1)
    args = parser.parse_args()

    if args.mode == 'fetch_urls':
        data_path = path.join(base_dir, 'data/%s/' % ('raw'))
        FetchMode(data_path, args.corpus)
    elif args.mode == 'download':
        data_path = path.join(base_dir, 'data/%s/' % (args.data_type))
        download_path = '%s/downloads/%s/' % (data_path, args.corpus)
        if not os.path.isdir(download_path):
            mkdirp(download_path)
        DownloadMode(data_path, args.corpus)
    elif args.mode == 'archive_urls':
        UrlMode(path.join(base_dir, 'data/processed/'), args.corpus, args.request_parallelism)

if __name__ == '__main__':
    main()
