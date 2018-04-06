import pulp
import numpy as np

import sys
import os
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem.snowball import SnowballStemmer
import argparse
import logging

logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.misc import mkdirp
from utils.misc import set_logger
from utils.data_helpers import extract_ngrams
from utils.data_helpers import untokenize
from utils.data_helpers import load_data

class Sentence:
    """The sentence data structure.
    Args: 
        tokens (list of str): the list of word tokens.
        doc_id (str): the identifier of the document from which the sentence
          comes from.
        position (int): the position of the sentence in the source document.
    """
    def __init__(self, tokens, doc_id, position):

        self.tokens = tokens
        """ tokens as a list. """

        self.doc_id = doc_id
        """ document identifier of the sentence. """

        self.position = position
        """ position of the sentence within the document. """

        self.concepts = []
        """ concepts of the sentence. """

        self.untokenized_form = ''
        """ untokenized form of the sentence. """

        self.length = 0
        """ length of the untokenized sentence. """

class ExtractiveUpperbound():
    def __init__(self, language):
        self.sentences = []
        self.docs = []
        self.models = []
        self.doc_sent_dict = {}
        self.ref_ngrams = []
        self.LANGUAGE = language
        self.stemmer = SnowballStemmer(self.LANGUAGE)
        self.stoplist = set(stopwords.words(self.LANGUAGE))

    def __call__(self, docs, models, length, ngram_type=2):
        self.sum_length = int(length)
        self.load_data(docs, models)
        self.get_ref_ngrams(ngram_type)

        self.sentences_idx = range(len(self.sentences))
        self.ref_ngrams_idx = range(len(self.ref_ngrams))

        summary_idx = self.solve_ilp(ngram_type)
        summary_txt = self.get_summary_text(summary_idx)

        return summary_txt

    def load_data(self, docs, models):
        '''
        Load the data into
            :doc_sent_dict
            :sentences

        Parameters:
        docs: List of list of docs each doc is represented with its filename and sents
            [['sent1','sent2','sent3'],['sent1','sent2','sent3']]
        models: List of list of models each doc is represented with its filename and sents
            [['sent1','sent2','sent3'], ['sent1','sent2','sent3']]

        '''
        self.docs = docs
        self.models = models
        self.sentences = []
        self.doc_sent_dict = {}

        doc_id = 0
        for doc_id, doc in enumerate(docs):
            doc_sents = doc
            total = len(self.sentences)
            for sent_id, sentence in enumerate(doc_sents):
                token_sentence = word_tokenize(sentence, self.LANGUAGE)
                sentence_s = Sentence(token_sentence, doc_id, sent_id+1)

                untokenized_form = untokenize(token_sentence)
                sentence_s.untokenized_form = untokenized_form
                sentence_s.length = len(untokenized_form.split(' '))
                self.doc_sent_dict[total+sent_id] = "%s_%s" % (str(doc_id), str(sent_id))
                self.sentences.append(sentence_s)


    def get_ref_ngrams(self, N):
        for summary in self.models:
            self.ref_ngrams.extend(extract_ngrams(" ".join(summary), self.stoplist, self.stemmer, self.LANGUAGE, N))

    def get_summary_text(self, summary_idx):
        return [ self.sentences[idx].untokenized_form for idx in summary_idx]

    def solve_ilp(self, N):
        # build the A matrix: a_ij is 1 if j-th gram appears in the i-th sentence

        A = np.zeros((len(self.sentences_idx), len(self.ref_ngrams_idx)))
        for i in self.sentences_idx:
            sent = self.sentences[i].untokenized_form
            sngrams = list(extract_ngrams(sent, self.stoplist, self.stemmer, self.LANGUAGE, N))
            for j in self.ref_ngrams_idx:
                if self.ref_ngrams[j] in sngrams:
                    A[i][j] = 1

        # Define ILP variable, x_i is 1 if sentence i is selected, z_j is 1 if gram j appears in the created summary
        x = pulp.LpVariable.dicts('sentences', self.sentences_idx, lowBound=0, upBound=1, cat=pulp.LpInteger)
        z = pulp.LpVariable.dicts('grams', self.ref_ngrams_idx, lowBound=0, upBound=1, cat=pulp.LpInteger)

        # Define ILP problem, maximum coverage of grams from the reference summaries
        prob = pulp.LpProblem("ExtractiveUpperBound", pulp.LpMaximize)
        prob += pulp.lpSum(z[j] for j in self.ref_ngrams_idx)

        # Define ILP constraints, length constraint and consistency constraint (impose that z_j is 1 if j
        # appears in the created summary)
        prob += pulp.lpSum(x[i] * self.sentences[i].length for i in self.sentences_idx) <= self.sum_length

        for j in self.ref_ngrams_idx:
            prob += pulp.lpSum(A[i][j] * x[i] for i in self.sentences_idx) >= z[j]

        # Solve ILP problem and post-processing to get the summary
        try:
            prob.solve(pulp.CPLEX(msg=0))
        except:
            prob.solve(pulp.GLPK(msg=0))

        summary_idx = []
        for idx in self.sentences_idx:
            if x[idx].value() == 1.0:
                summary_idx.append(idx)

        return summary_idx


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

    scores = [score['rouge-1']['f'], score['rouge-1']['p'], score['rouge-1']['r'],\
     score['rouge-2']['f'], score['rouge-2']['p'], score['rouge-2']['r'], \
     score['rouge-l']['f'], score['rouge-l']['p'], score['rouge-l']['r']]

    return scores


def get_summary_scores(algo, docs, refs, summary_size, language, rouge):
    if algo == 'UB1':
        UB = ExtractiveUpperbound(language)
        summary = UB(docs, refs, summary_size, ngram_type=1)
    if algo == 'UB2':
        UB = ExtractiveUpperbound(language)
        summary = UB(docs, refs, summary_size, ngram_type=2)

    print_scores(algo_name, summary, refs, rouge)

def main():

    args = get_args()
    data_path = os.path.join(args.iobasedir, 'processed/downloads', args.data_set)
    log_path = os.path.join(args.iobasedir, 'logs')
    log_file = os.path.join(args.iobasedir, 'logs', 'UB.log')
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

        logger.info('Topic ID: %s ', topic)
        logger.info('###')
        logger.info('Summmary_len: %d', summary_size)

        algos = ['UB1', 'UB2']
        for algo in algos:
            get_summary_scores(algo, docs, refs, summary_size, language, rouge)

        logger.info('###')

if __name__ == '__main__':
    main()
