import streamlit as st

import gensim as gs 
import gensim.parsing.preprocessing as pp

from gensim import models
from gensim.corpora import Dictionary

import pandas as pd
from io import StringIO

class TopicModel:
	def __init__(self):
		print("*** Initialize TopicModel")

	def gensim_version(self):
		return gs.__version__

	def load_corpus(self, url):
		if url is not None:
			print("*** Reading the corpus")
			documents = pd.read_csv(url)
			self.corpus = Corpus(documents)
		else:
			print("*** No url provided")
			self.corpus = Corpus([])	# exception
		self.corpus.preprocess()
		return self.corpus

	def fit(self, corpus, number_of_topics):
		self.corpus = corpus
		self.number_of_topics = number_of_topics
		self.lda = models.LdaModel(self.corpus.bow(), self.number_of_topics)
		return self.lda

	def show_topics(self, number_of_words):
		return self.lda.show_topics(num_topics=self.number_of_topics, 
			num_words=number_of_words, formatted=False)

#	def get_document_topics(document):
#		return lda.

	def topics_to_csv(self, number_of_words):
		print("*** TopicModel.Topics to csv")
		print(self.lda)
		r = "topic, content\n"
		for index, topic in self.show_topics(number_of_words):
			line = "topic_{},".format(index)
			for w in topic:
				line += " " + self.corpus.dictionary[int(w[0])]
			r += line + "\n"
		return r

	def read_topics(self, csv):
		return pd.read_csv(StringIO(csv))

	def topics(self, number_of_words):
		return self.read_topics(self.topics_to_csv(number_of_words))

class Corpus:
	def __init__(self, documents):
		self.documents = documents

	def preprocess(self):
		stopwords = self.read_stopwords('stopwords.txt')
		self.tokens = [[word for word in self.preprocess_document(document) 
				if word not in stopwords] 
			for document in self.documents['content']]
		self.dictionary = Dictionary(self.tokens)

	@st.cache
	def read_stopwords(self, file):
		file = open(file, 'r')
		return file.read().split('\n')

	def preprocess_document(self, document):
		return pp.strip_punctuation(document).lower().split()

	def bow(self):
		return [self.dictionary.doc2bow(doc) for doc in self.tokens]
