# -*- coding: utf-8 -*-

import streamlit as st

import gensim as gs 

from gensim import models
from gensim.models.coherencemodel import CoherenceModel
# from gensim.models import ldamulticore
from gensim.corpora import Dictionary

import pandas as pd
import numpy as np
from scipy.optimize import linear_sum_assignment
import math

from io import StringIO
from re import sub

class TopicModel:
	def gensim_version(self):
		return gs.__version__

	def load_corpus(self, url, stopwords):
		if url is not None:
			url.seek(0)	 # move read head back to the start (StringIO behaves like a file)
			documents = pd.read_csv(url)
			corpus = Corpus(documents)
			corpus.preprocess(stopwords)
			return corpus
		else:
			return None

	def fit(self, corpus, number_of_topics, number_of_iterations=50, number_of_passes=1,
			number_of_chunks=1, alpha="symmetric"):
		if alpha == "talley":
			alpha = np.array([self.alpha(corpus, number_of_topics)] * number_of_topics)
		return LDA(models.LdaModel(corpus.bow(), number_of_topics, corpus.dictionary,
			iterations=number_of_iterations, passes=number_of_passes, 
			chunksize=self.chunksize(corpus, number_of_chunks), alpha=alpha))

	def alpha(self, corpus, number_of_topics):
		return 0.05 * corpus.average_document_length() / number_of_topics

	def chunksize(self, corpus, number_of_chunks):
		return math.ceil(len(corpus.documents) / number_of_chunks)

	# def show_topics(self, number_of_words):
	# 	return self.lda.show_topics(num_topics=self.number_of_topics, 
	# 		num_words=number_of_words, formatted=False)

	# def get_document_topics(document):
	# return lda.

	# def topics_to_csv(self, number_of_words):
	# 	print("*** TopicModel.Topics to csv")
	# 	print(self.lda)
	# 	r = "topic, content\n"
	# 	for index, topic in self.show_topics(number_of_words):
	# 		line = "topic_{},".format(index)
	# 		for w in topic:
	# 			line += " " + self.corpus.dictionary[int(w[0])]
	# 		r += line + "\n"
	# 	return r

	# def read_topics(self, csv):
	# 	return pd.read_csv(StringIO(csv))

	# def topics(self, number_of_words):
	# 	return self.read_topics(self.topics_to_csv(number_of_words))

class LDA:
	def __init__(self, lda):
		self.lda = lda

	def corpus(self):
		return lda.corpus  # bow representation, our corpus.bow()

	def number_of_topics(self):
		return lda.num_topics

	def chunksize(self):
		return lda.chunksize

	def show_topics(self, number_of_topics, number_of_words):
		return self.lda.show_topics(num_topics=number_of_topics, 
			num_words=number_of_words, formatted=False)

	def get_document_topics(self, document_bow):
		return self.lda.get_document_topics(document_bow)

	def coherence(self, corpus):
		coherence_model = CoherenceModel(model=self.lda, texts=corpus.tokens, 
			dictionary=corpus.dictionary, coherence='c_uci')
		return coherence_model.get_coherence()

	# return a difference matrix between two topic models
	# computes the average jaccard distance as defined by Greene (2014)
	def difference(self, other, n=10):
		return sum([self.jaccard(other, k) for k in range(n)]) / n

	def jaccard(self, other, k):
		diff, _ = self.lda.diff(other.lda, distance='jaccard', num_words=k)
		return diff

class TopicAlignment:
	def __init__(self, topic_model, corpus, number_of_topics, number_of_chunks, number_of_runs):
		self.topic_model = topic_model
		self.corpus = corpus
		self.number_of_topics = number_of_topics
		self.number_of_chunks = number_of_chunks
		self.number_of_runs = number_of_runs

	def fit(self, progress_update):
		lda_models = self.lda_model_runs(progress_update)
		self.topics = self.topics(lda_models)
		self.matches = self.matches(lda_models)

	# create a group of topic models with the same number of topics
	def lda_model_runs(self, progress_update):
		lda_models = []
		for run in range(self.number_of_runs):
			lda_models.append(self.topic_model.fit(self.corpus, self.number_of_topics, 
				number_of_chunks=self.number_of_chunks))
			progress_update(run)
		return lda_models

	# extract the topic words for each topic in all topic models
	def topics(self, lda_models):
		return pd.DataFrame([[" ".join([tw[0] for tw in lda_model.lda.show_topic(t, 10)]) 
			for lda_model in lda_models] for t in range(self.number_of_topics)])

	# compute the average Jaccard distance between the topic models
	def differences(self, lda_models):
		return [lda_models[0].difference(lda_models[i]) 
			for i in range(1, len(lda_models))]

	# fit topics between the first and each of the remaining topic models using
	# the Hungarian linear assignment method
	def matches(self, lda_models):
		diffs = self.differences(lda_models)
		matches = pd.DataFrame()
		# first column are the topics of the first topic model
		matches[0] = range(self.number_of_topics)
		# minimize the total misalignment between topics
		for i in range(1, len(lda_models)):
			_, cols = linear_sum_assignment(diffs[i-1])
			# each column contains the topics that align with the topics of the first topic
			matches[i] = cols
		return matches

class Corpus:
	def __init__(self, documents):
		self.documents = self.to_ascii(documents)

	def to_ascii(self, documents):
		# replace non-ascii symbols left by text processing software
		documents['content'] = [sub(r'[^A-Za-z0-9,\.?!]+', ' ', document)
			for document in documents['content']]
		return documents

	def preprocess(self, user_defined_stopwords):
		self.stopwords_en = self.read_stopwords("stopwords-en.txt")
		self.user_defined_stopwords = user_defined_stopwords.split('\n')
		self.stopwords = self.stopwords_en + self.user_defined_stopwords
		self.tokens = [[word for word in sub(r'[^A-Za-z0-9]+', ' ', document).lower().split() 
				if word not in self.stopwords] 
			for document in self.documents['content']]
		self.dictionary = Dictionary(self.tokens)

	def read_stopwords(self, file):
		file = open(file, 'r')
		return file.read().split('\n')

	def bow(self):
		return [self.dictionary.doc2bow(doc) for doc in self.tokens]

	def average_document_length(self):
		return np.mean(map(len, self.tokens))

