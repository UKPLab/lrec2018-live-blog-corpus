#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os, sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from nltk.tokenize import word_tokenize 
import summarize.sume as sume
from sume import Sentence, untokenize

from nltk.corpus import stopwords
from nltk.stem.snowball import SnowballStemmer

class SumeWrap():
    def __init__(self, language):
        self.s = sume.ConceptBasedILPSummarizer(" ", language)
        self.LANGUAGE = language
        self.stoplist = set(stopwords.words(self.LANGUAGE))
        self.stemmer = SnowballStemmer(self.LANGUAGE)

    def load_sume_sentences(self, docs, parse_type=None, parse_info=[]):
        """

        :param docs: the documents to load
        :param parse_type:
        :param parse_info:
        :return: list[Sentence]

        @type docs: list[tuple]
        @type parse_type: str
        @type parse_info: list
        """
        self.docs = docs
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
        return self.sentences

    def __call__(self, docs, length=100, units="WORDS", rejected_list=[], imp_list=[], parser_type=None):
        try:
            length = int(length)
        except:
            raise TypeError("argument 'length' could not be converted to int. It is of type '%s' and has value '%s'" % (type(length), length))
        # load documents with extension 'txt'
        self.s.sentences = self.load_sume_sentences(docs, parser_type)

        # compute the parameters needed by the model
        # extract bigrams as concepts
        self.s.extract_ngrams()

        # compute document frequency as concept weights
        self.s.compute_document_frequency()

        # solve the ilp model
        value, subset = self.s.solve_ilp_problem(summary_size=length, units=units)

        return [self.s.sentences[j].untokenized_form for j in subset]
