import sys
import os
from rouge import Rouge
import argparse
import logging
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.misc import mkdirp
from utils.misc import set_logger
from utils.data_helpers import load_data

from summarize.upper_bound import ExtractiveUpperbound
from summarize.sume_wrap import SumeWrap
from summarize.sumy.nlp.tokenizers import Tokenizer
from summarize.sumy.parsers.plaintext import PlaintextParser
from summarize.sumy.summarizers.lsa import LsaSummarizer
from summarize.sumy.summarizers.kl import KLSummarizer
from summarize.sumy.summarizers.luhn import LuhnSummarizer
from summarize.sumy.summarizers.lex_rank import LexRankSummarizer
from summarize.sumy.summarizers.text_rank import TextRankSummarizer
from summarize.sumy.nlp.stemmers import Stemmer
from nltk.corpus import stopwords

logger = logging.getLogger(__name__)

def get_args():
    ''' This function parses and return arguments passed in'''

    parser = argparse.ArgumentParser(description='Upper Bound for Summarization')
    # -- summary_len: 100, 200, 400
    parser.add_argument('-s', '--summary_size', type=str, help='Summary Length', required=False)

    # --data_set: DUC2001, DUC2002, DUC2004
    parser.add_argument('-d', '--data_set', type=str, help='Data set ex: DUC2004', required=True)

    # --language: english, german
    parser.add_argument('-l', '--language', type=str, help='Language: english, german', required=False,
                        default='english')

    parser.add_argument('-io', '--iobasedir', type=str, help='IO base directory', required=False,
                        default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"))
    args = parser.parse_args()

    return args

def print_scores(algo_name, summary_sents, refs, rouge):
    hyps, refs = map(list, zip(*[[' '.join(summary_sents), ' '.join(model)] for model in refs]))
    score = rouge.get_scores(hyps, refs, avg=True)
    logger.info('%s: ROUGE-1: %4f %4f %4f, ROUGE-2: %4f %4f %4f, ROUGE-L: %4f %4f %4f' % (algo_name, \
        score['rouge-1']['f'], score['rouge-1']['p'], score['rouge-1']['r'], \
        score['rouge-2']['f'], score['rouge-2']['p'], score['rouge-2']['r'], \
        score['rouge-l']['f'], score['rouge-l']['p'], score['rouge-l']['r']))


def get_summary_scores(algo, docs, refs, summary_size, language, rouge):
    if algo == 'UB1':
        summarizer = ExtractiveUpperbound(language)
        summary = summarizer(docs, refs, summary_size, ngram_type=1)
    elif algo == 'UB2':
        summarizer = ExtractiveUpperbound(language)
        summary = summarizer(docs, refs, summary_size, ngram_type=2)
    elif algo == 'ICSI':
        summarizer = SumeWrap(language)
        summary = summarizer(docs, summary_size)
    else:
        doc_string = u'\n'.join([u'\n'.join(doc_sents) for doc_sents in docs]) 
        parser = PlaintextParser.from_string(doc_string, Tokenizer(language))
        stemmer = Stemmer(language)
        if algo == 'LSA':
            summarizer = LsaSummarizer(stemmer)
        if algo == 'KL':
            summarizer = KLSummarizer(stemmer)
        if algo == 'Luhn':
            summarizer = LuhnSummarizer(stemmer)
        if algo == 'LexRank':
            summarizer = LexRankSummarizer(stemmer)
        if algo == 'TextRank':
            summarizer = TextRankSummarizer(stemmer)

        summarizer.stop_words = frozenset(stopwords.words(language))
        summary = summarizer(parser.document, summary_size)

    print_scores(algo, summary, refs, rouge)


def main():

    args = get_args()
    rouge = Rouge()
    data_path = os.path.join(args.iobasedir, 'processed/downloads', args.data_set)
    log_path = os.path.join(args.iobasedir, 'logs')
    log_file = os.path.join(args.iobasedir, 'logs', 'baselines_%s.log' % args.data_set)
    mkdirp(log_path)
    set_logger(log_file)

    for filename in os.listdir(data_path):
        data_file =  os.path.join(data_path, filename)
        topic = filename[:-5]

        docs, refs = load_data(data_file)
        if not refs:
            continue

        if not args.summary_size:
            summary_size = len(' '.join(refs[0]).split(' '))
        else:
            summary_size = int(args.summary_size)

        logger.info('Topic ID: %s', topic)
        logger.info('###')
        logger.info('Summmary_len: %d', summary_size)

        algos = ['UB1', 'UB2', 'ICSI', 'Luhn', 'LexRank', 'TextRank', 'LSA', 'KL']
        for algo in algos:
            get_summary_scores(algo, docs, refs, summary_size, args.language, rouge)

        logger.info('###')

if __name__ == '__main__':
    main()
