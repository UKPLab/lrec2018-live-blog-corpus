import codecs
import json
import os
import re
from nltk.tokenize import word_tokenize

def load_data(data_path):
    """Load the live blogs corpus data

    Args:
        data_path: path to the json file

    return:
        doc_data: list of input documents represented as a list of sentences.
        summaries: list of summaries represented as a list of sentences. 

    """
    doc_data = []
    with codecs.open(data_path, "r", encoding='utf-8') as fp:
        json_text = fp.readline()
        json_data = json.loads(json_text)

        # Return if the summary is empty or the collection is of low quality
        if not json_data['summary'] or json_data['quality'] == 'low':
            return doc_data, []

        summaries = [ json_data['summary'] ]

        documents = json_data['documents']

        for doc in documents:
            if doc['is_key_event'] == False:
                doc_data.append(doc['text'])
    return doc_data, summaries


def extract_ngrams(sentence, stoplist, stemmer, language='english', n=2):
    """Extract the ngrams of words from the input text.

    Args:
        n (int): the number of words for ngrams, defaults to 2
    """
    concepts = []
    
    # for each ngram of words
    tokens = sent2tokens(sentence, language)
    for j in range(len(tokens)-(n-1)):

        # initialize ngram container
        ngram = []

        # for each token of the ngram
        for k in range(j, j+n):
            ngram.append(tokens[k].lower())

        # do not consider ngrams containing punctuation marks
        marks = [t for t in ngram if not re.search('[a-zA-Z0-9]', t)]
        if len(marks) > 0:
            continue

        # do not consider ngrams composed of only stopwords
        stops = [t for t in ngram if t in stoplist]
        if len(stops) == len(ngram):
            continue

        # stem the ngram
        ngram = [stemmer.stem(t) for t in ngram]

        # add the ngram to the concepts
        concepts.append(' '.join(ngram))
    return concepts

def untokenize(tokens):
    """Untokenizing a list of tokens. 

    Args:
        tokens (list of str): the list of tokens to untokenize.

    Returns:
        a string

    """
    text = u' '.join(tokens)
    text = re.sub(u"\s+", u" ", text.strip())
    text = re.sub(u" ('[a-z]) ", u"\g<1> ", text)
    text = re.sub(u" ([\.;,-]) ", u"\g<1> ", text)
    text = re.sub(u" ([\.;,-?!])$", u"\g<1>", text)
    text = re.sub(u" _ (.+) _ ", u" _\g<1>_ ", text)
    text = re.sub(u" \$ ([\d\.]+) ", u" $\g<1> ", text)
    text = text.replace(u" ' ", u"' ")
    text = re.sub(u"([\W\s])\( ", u"\g<1>(", text)
    text = re.sub(u" \)([\W\s])", u")\g<1>", text)
    text = text.replace(u"`` ", u"``")
    text = text.replace(u" ''", u"''")
    text = text.replace(u" n't", u"n't")
    text = re.sub(u'(^| )" ([^"]+) "( |$)', u'\g<1>"\g<2>"\g<3>', text)

    # times
    text = re.sub('(\d+) : (\d+ [ap]\.m\.)', '\g<1>:\g<2>', text)

    text = re.sub('^" ', '"', text)
    text = re.sub(' "$', '"', text)
    text = re.sub(u"\s+", u" ", text.strip())

    return text

def sent2tokens(sent, language='english', lower=True):
    '''
    Sentence to stemmed tokens
    Parameter arguments:
    words = list of words e.g. sent = '... The boy is playing.'

    return:
    list of tokens
    ['the', 'boy', 'is', 'playing','.']
    '''
    if lower == True:
        sent = sent.lower()
    words = word_tokenize(sent, language)
    return words
