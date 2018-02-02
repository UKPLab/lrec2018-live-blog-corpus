from lxml import html
import requests
import socket
from multiprocessing.pool import Pool
from multiprocessing.pool import ThreadPool
import hashlib
import os
import re
import time
import argparse
import math
from itertools import chain
from itertools import izip
from itertools import repeat

import os.path as path
import sys
base_dir = path.dirname(path.dirname(path.abspath(__file__)))
sys.path.append(base_dir)

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
    tree = html.fromstring(content)
    
    if corpus == 'guardian':
        older_part = tree.xpath('//div[@class="liveblog-navigation__older"]')
    
    url = ''
    if len(older_part) >= 1:
        older_part_link = older_part[0].xpath(".//a")[0].get("href")
        if older_part_link:
            print(older_part_link)
            url = "http://www.theguardian.com" + older_part_link[:older_part_link.rfind('#')]
    return url

def DownloadUrl(data_path, url, corpus, max_attempts=5, timeout=5):
        """Downloads a URL.

        Args:
                url: The URL.
                corpus: The corpus of the URL.
                max_attempts: Max attempts for downloading the URL.
                timeout: Connection timeout in seconds for each attempt.

        Returns:
                The HTML at the URL or None if the request failed.
        """

        try:
            with open('%s/downloads/%s.html' % (corpus, Hashhex(url))) as f:
                return f.read()
        except IOError:
                pass

        attempts = 0

        while attempts < max_attempts:
            try:
                req = requests.get(url, allow_redirects=False, timeout=timeout)
                print(url)
                print('Status code', req.status_code)
                if req.status_code == requests.codes.ok:
                    content = req.text.encode(req.encoding)
                    hash_val = Hashhex(url)
                    
                    
                    
                    downloads_dir = "%s/downloads/%s/%s" %  (data_path, corpus, hash_val)
                    if not os.path.exists(downloads_dir):
                        os.mkdir(downloads_dir)
                    count = 0
                    with open('%s/downloads/%s/%s/%s.html' % (data_path, corpus, hash_val, str(count)), 'w') as f:
                        f.write(content)
                    
                    #Loop over next pages to append the documents list
                    while(1):
                        count += 1
                        url = GetNextPage(content, corpus)
                        print('URL: %s' % (url))
                        if url:
                            req = requests.get(url, allow_redirects=True, timeout=timeout)
                            print('Status code', req.status_code)
                            if req.status_code == requests.codes.ok:
                                content = req.text.encode(req.encoding)
                                filename = '%s/downloads/%s/%s/%s.html' % (data_path, corpus, hash_val, str(count))
                                print(filename)
                                with open(filename, 'w') as f:
                                    f.write(content)
                        else:
                            break
                    return content
                elif (req.status_code in [301, 302, 404, 503] and attempts == max_attempts - 1):
                    return None
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

class ProgressBar(object):
        """Simple progress bar.
        Output example:
                100.00% [2152/2152]
        """

        def __init__(self, total=100, stream=sys.stderr):
                self.total = total
                self.stream = stream
                self.last_len = 0
                self.curr = 0

        def Increment(self):
                self.curr += 1
                self.PrintProgress(self.curr)

                if self.curr == self.total:
                        print ''

        def PrintProgress(self, value):
                self.stream.write('\b' * self.last_len)
                pct = 100 * self.curr / float(self.total)
                out = '{:.2f}% [{}/{}]'.format(pct, value, self.total)
                self.last_len = len(out)
                self.stream.write(out)
                self.stream.flush()

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

    data_path, url, corpus = t

    return url, DownloadUrl(data_path, url, corpus)

def ReadUrls(filename):
    """Reads a list of URLs.
    Args:
        filename: The filename containing the URLs.
    Returns:
        A list of URLs.
    """

    with open(filename) as f:
        return [line.strip('\n') for line in f]


def DownloadModeNO(data_path, corpus):
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

    for url in urls:
        url, story = DownloadMapper((data_path, url, corpus))
        exit(0)


def DownloadMode(data_path, corpus, request_parallelism):
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

def main():
    parser = argparse.ArgumentParser(
                    description='Generate the Summarization Corpus')
    parser.add_argument('--corpus', choices=['bbc', 'guardian'], default='guardian')
    parser.add_argument(
                    '--mode', choices=['store', 'generate', 'download', 'urls', 'remove'],
                    default='generate')
    parser.add_argument('--request_parallelism', type=int, default=200)
    parser.add_argument('--context_token_limit', type=int, default=2000)
    args = parser.parse_args()

    """
    downloads_dir = '%s/downloads' % args.corpus
    if not os.path.exists(downloads_dir):
            os.mkdir(downloads_dir)
    """
    
    if args.mode == 'store':
        StoreMode(args.corpus)
    elif args.mode == 'generate':
        GenerateMode(args.corpus, args.context_token_limit)
    elif args.mode == 'download':
        data_path = path.join(base_dir, 'data/processed/')
        DownloadModeNO(data_path, args.corpus)
        #DownloadMode(data_path, args.corpus, args.request_parallelism)
    elif args.mode == 'urls':
        data_path = path.join(base_dir, 'data/processed/')
        UrlMode(data_path, args.corpus, args.request_parallelism)
    elif args.mode == 'remove':
            RemoveMode(args.corpus)

if __name__ == '__main__':
    main()


