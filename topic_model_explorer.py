# -*- coding: utf-8 -*-

import streamlit as st
from topics import TopicModel

import pandas as pd
import numpy as np

import heapq
import operator
import math

import itertools
import base64

from wordcloud import WordCloud
import matplotlib.pyplot as plt

import graphviz as graphviz

from io import StringIO

@st.cache(allow_output_mutation=True)
def load_corpus(url):
	return tm.load_corpus(url)

@st.cache(allow_output_mutation=True)
def lda_model(url, stopwords, number_of_topics):
	corpus = load_corpus(url)
	with st.spinner("Training the topic model ..."):
		print("*** Training the topic model: {}".format(number_of_topics))
		lda = tm.fit(corpus, number_of_topics)
		print("*** Training completed ***")
		return lda

# move this method to topics
def topics_to_csv(number_of_words):
	corpus = load_corpus(url)
	lda = lda_model(url, stopwords, number_of_topics)
	r = "topic, content\n"
	for index, topic in lda.show_topics(number_of_topics, number_of_words):
		line = "topic_{},".format(index)
		for w in topic:
			line += " " + corpus.dictionary[int(w[0])]
		r += line + "\n"
	return r

def read_topics(csv):
	return pd.read_csv(StringIO(csv))

def topics(number_of_words):
	return read_topics(topics_to_csv(number_of_words))

def download_link(dataframe, file_name, title="Download"):
	csv = dataframe.to_csv(index=False)
	download_link_from_csv(csv, file_name, title)

def download_link_from_csv(csv, file_name, title="Download"):
	b64 = base64.b64encode(csv.encode()).decode()  # some strings <-> bytes conversions necessary here
	href = "<a href='data:file/csv;base64,{}' download='{}'>{}</a>".format(b64, file_name, title)
	st.markdown(href, unsafe_allow_html=True)

def bow_top_keywords(bag_of_words, dictionary):
	keywords = []
	for wid, score in heapq.nlargest(3, bag_of_words, key=operator.itemgetter(1)):
		keywords.append("{}".format(dictionary[wid]))
	return keywords

def document_topics(i):
	corpus = load_corpus(url)
	lda = lda_model(url, stopwords, number_of_topics)
	return lda.get_document_topics(corpus.documents[i])
	# return [bow_top_keywords(document, dictionary) for document in corpus]
	# return lda[corpus[i]]

def topics_sparse_to_full(topics):
	topics_full = [0] * number_of_topics  # pythonic way of creating a list of zeros
	for topic, score in topics:
		topics_full[topic] = score
	return topics_full

def document_topics_matrix():
	corpus = load_corpus(url)
	lda = lda_model(url, stopwords, number_of_topics)
	dtm = []
	for document_bow in corpus.bow():
		dtm.append(topics_sparse_to_full(lda.get_document_topics(document_bow)))
	return dtm

def topic_coocurrence_matrix_(min_weight):
	dtm = document_topics_matrix()
	relationships = []
	for topic_weights in dtm:
		document_relationships = []
		for k in range(number_of_topics):
			if topic_weights[k] >= min_weight:
				document_relationships.append(k)
		relationships.append(document_relationships)
	return relationships

def topic_coocurrence_graph(min_weight, min_edges):
	dtm = document_topics_matrix()
	graph = graphviz.Graph()
	graph.attr('node', shape='circle', fixedsize='true')
	total_topic_weights = tally_columns(dtm)
	for i in range(number_of_topics):
		graph.node(str(i), width=str(2*math.sqrt(total_topic_weights[i])))
	edge = np.zeros((number_of_topics, number_of_topics))
	for topic_weights in dtm:
		topics = [k for k in range(number_of_topics) if topic_weights[k] >= min_weight]
		for i, j in list(itertools.combinations(topics, 2)):
			edge[i, j] = edge[i, j] + 1
	for i in range(number_of_topics):
		for j in range(number_of_topics):
			if edge[i, j] >= min_edges:
				graph.edge(str(i), str(j), 
					penwidth="{}".format(edge[i, j]))
	return graph

def normalize(df):
	df_new = df.copy()
	for topic in df.columns:
		topic_sum = df[topic].sum()
		df_new[topic] = df[topic]/topic_sum
	return df_new

def document_top_topics(i):
	lda = lda_model(url, stopwords, number_of_topics)
	return np.argsort(-np.array(topics_sparse_to_full(lda.get_document_topics)))	

# sum document frequencies for each topic and normalize
# thus, the column tallies add up to 1
def tally_columns(dtm):
	return [sum([row[k] for row in dtm])/len(dtm) for k in range(number_of_topics)]

def sort_by_topic(dtm, k):
	col_k = [row[k] for row in dtm]
	return np.argsort(-np.array(col_k))

def topic_words(k, number_of_words):
	r = {}
	corpus = load_corpus(url)
	lda = lda_model(url, stopwords, number_of_topics)
	for index, topic in lda.show_topics(number_of_topics, number_of_words):
		if index == k:
			for w in topic:
				s = corpus.dictionary[int(w[0])]
				r[s] = w[1]
			return r
	return {}

import re

def keyword_coocurrence_graph(selected_topic, min_edges):
	corpus = load_corpus(url)
	dtm = document_topics_matrix()
	document = corpus.documents['content'][sort_by_topic(dtm, selected_topic)[0]]
	print("*** keyword: {}".format(document))
	index = {}
	reverse_index = {}
	next_index = 0
	sentence_words = []
	for sentence in document.split(". "):
		sentence = re.sub(r'[^A-Za-z0-9]+', ' ', sentence)
		words = [word for word in sentence.lower().split(" ") 
			if word not in corpus.stopwords_en]
		words = set(words)
		for word in words:
			if word not in index:
				index[word] = next_index
				reverse_index[next_index] = word
				next_index = next_index + 1
		sentence_words.append(words)
	edge = np.zeros((len(index), len(index)))
	for words in sentence_words:
		for wi, wj in list(itertools.combinations(words, 2)):
			edge[index[wi], index[wj]] = edge[index[wi], index[wj]] + 1
	graph = graphviz.Graph()
	graph.attr('node', shape='plaintext')
	nodes = []
	for i in range(len(index)):
		for j in range(len(index)):
			if edge[i, j] >= min_edges:
				nodes.append(i)
				nodes.append(j)
				graph.edge(reverse_index[i], reverse_index[j], 
					penwidth="{}".format(math.sqrt(edge[i, j])))
	for i in nodes:
		graph.node(reverse_index[i])
	return graph

st.sidebar.title("Topic Model Explorer")
tm = TopicModel()

url = st.sidebar.file_uploader("Corpus", type="csv")

stopwords = st.sidebar.text_area("Stopwords (one per line)")
update_stopwords = st.sidebar.button("Update stopwords")

if update_stopwords:
	if url is not None:
		corpus = load_corpus(url)
		corpus.update_stopwords(stopwords)

show_documents = st.sidebar.checkbox("Show documents", value=True)

if show_documents:
	st.header("Corpus")
	if url is not None:
		corpus = load_corpus(url)
		if('name' not in corpus.documents or 'content' not in corpus.documents):
			st.markdown('''
		The corpus must have a *name* and a *content* column.
			''')
		st.dataframe(corpus.documents)
		download_link_from_csv("\n".join(corpus.stopwords), "stopwords.txt",
			"Download stopwords")
	else:
		st.markdown("Please upload a corpus.")

number_of_topics = st.sidebar.slider("Number of topics", 1, 50, 10)
show_topics = st.sidebar.checkbox("Show topics", value=False)

if show_topics:
	st.header("Topics")
	if url is not None:	
		corpus = load_corpus(url)	# needed for caching purposes (check)
		df = topics(5)
		st.table(df)
		download_link(df, "topic-keywords-{}.csv".format(number_of_topics),
			"Download topic keywords")
	else:
		st.markdown("No corpus.")

# show_correlation = st.sidebar.checkbox("Show correlation between topics and documents", value=False)
# if show_correlation:
# 	if url is not None:
# 		st.header("Correlation between topics and documents")
# 		corpus = load_corpus(url)
# 		st.markdown("Correlation for %d topics: %.2f" % 
# 			(number_of_topics, tm.cophenet(corpus, number_of_topics)))

show_wordcloud = st.sidebar.checkbox("Show word cloud", value=False)

if show_wordcloud:
	st.header("Word cloud")
	if url is not None:
		selected_topic = st.sidebar.slider("Topic", 0, number_of_topics - 1, 0)
		st.markdown('''
			The word cloud shows the 10 most frequent words for each topic.
		''')
		wordcloud = WordCloud(background_color="white", 
			max_font_size=28).fit_words(topic_words(selected_topic, 10))
		plt.imshow(wordcloud, interpolation='bilinear')
		plt.axis("off")
		plt.show()
		st.pyplot()
	else:
		st.markdown("No corpus.")

show_document_topic_matrix = st.sidebar.checkbox("Show document topics", value=False)

if show_document_topic_matrix:
	st.header("Document Topics")
	if url is not None:
		st.markdown('''
			The document topic matrix shows the topic weights for each document. 
		''')
		dtm = document_topics_matrix()
		corpus = load_corpus(url)
		dtm_df = pd.DataFrame(dtm)
		if "year" in corpus.documents:
			dtm_df.insert(0, "year", corpus.documents["year"])
		dtm_df.insert(0, "name", corpus.documents["name"])
		st.dataframe(dtm_df)
		download_link(dtm_df, "document-topics-{}.csv".format(number_of_topics),
			"Download document topics")
	else:
		st.markdown("No corpus.")

show_tally_topics = st.sidebar.checkbox("Show topics tally", value=False)

if show_tally_topics:
	st.header("Topics Tally")
	if url is not None:
		st.markdown('''
			This graph show the proportion of each topic across the corpus.
		''')
		dtm = document_topics_matrix()
		st.line_chart(tally_columns(dtm))
	else:
		st.markdown("No corpus.")

show_topic_coocurrence_graph = st.sidebar.checkbox("Show topic co-occurrences", value=False)

if show_topic_coocurrence_graph:
	st.header("Topic Co-occurrences")
	if url is not None:
		min_weight = st.sidebar.slider("Minimum weight", 0.0, 0.5, value=0.1)
		min_edges = st.sidebar.slider("Minimum number of edges", 1, 10, value=1)
		st.markdown('''
			We consider topics to co-occur in the same document if the weight of both 
			topics for that document are greater than *minimum weight*. The thickness of
			a line in the co-occurrance graph indicates how often two topics co-occur
			in a document (at least *minimum edges* times). Each node corresponds to a 
			topic. Node size represents the total weight of the topic.
		''')
		graph = topic_coocurrence_graph(min_weight, min_edges)
		st.graphviz_chart(graph)
	else:
		st.markdown("No corpus.")

# show_sorted_topics = st.sidebar.checkbox("Show sorted topics", value=False)

# if show_sorted_topics:
# 	selected_topic = st.sidebar.slider("Topic", 0, number_of_topics - 1, 0)
# 	st.header("Sorted topics")
# 	dtm = document_topics_matrix()
# 	# st.table(topics_d[sort_by_topic(dtm, 0)])
# 	st.table(sort_by_topic(dtm, selected_topic))

show_topic_trends = st.sidebar.checkbox("Show topics trends", value=False)

if show_topic_trends:
	st.header("Topic Trends")
	if url is not None:
		st.markdown('''
			This chart shows emerging topic trends. It plots the aggregated topic weights 
			and the contribution of each topic by year. Note: The corpus must have a *year*
			column. 
		''')
		dtm = document_topics_matrix()
		corpus = load_corpus(url)
		dtm_df = pd.DataFrame(dtm)
		if "year" in corpus.documents:
			dtm_df.insert(0, "year", corpus.documents["year"])
			dtm_df_sum = dtm_df.groupby("year").sum()
			st.bar_chart(dtm_df_sum)
	else:
		st.markdown("No corpus.")

show_keyword_matches = st.sidebar.checkbox("Show keyword matches", value=False)
if show_keyword_matches:
	keywords = st.sidebar.text_input("Keywords")
	st.header("Keyword Matches")
	st.markdown('''
		Show which documents contain how many of the keywords specified.
	''')
	if url is not None and keywords != "":
		corpus = load_corpus(url)
		list_of_keywords = keywords.split(" ")
		df = corpus.documents.copy()
		for keyword in list_of_keywords:
			df[keyword] = [keyword in document.lower() for document
				in corpus.documents['content']]
		df['score'] = df[list_of_keywords].sum(axis=1)
		st.dataframe(df)
	else:
		st.markdown("No corpus or missing keywords.")

show_keyword_coocurrences = st.sidebar.checkbox("Show keyword co-occurrences", value=False)

if show_keyword_coocurrences:
	st.header("Keyword Co-occurrences")
	if url is not None:
		selected_topic_keywords = st.sidebar.slider("Selected topic", 0, number_of_topics-1)
		min_edges_keywords = st.sidebar.slider("Minimum number of edges", 1, 10, value=3)
		graph = keyword_coocurrence_graph(selected_topic_keywords, min_edges_keywords)
		st.write(graph)
	else:
		st.markdown("No corpus.")


