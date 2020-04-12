#-*-coding:utf-8-*-
from systemtools.hayj import *
from systemtools.location import *
from systemtools.basics import *
from systemtools.file import *
from systemtools.printer import *
from databasetools.mongo import *
from newstools.goodarticle.utils import *
from nlptools.preprocessing import *
from nlptools.news import parser as newsParser
from machinelearning.iterator import *
from twinews.utils import *

import pymongo
import json
import pandas as pd
import sys

from nltk.stem import WordNetLemmatizer
from nlptools.preprocessing import *
from nlptools.basics import *

logger = Logger(tmpDir('logs') + "/dssm_yf.log")

ConnUsers = getUsersCollection()
ConnNews = getNewsCollection()

userHistory = {}
negativeNewList = []

# read user with more than 30 news
for row in ConnUsers.find().limit(100):
    if len(row["news"]) >= 30:
        userHistory[row["user_id"]] = row["news"]
# get news for negative sampling
for row in ConnNews.find().limit(1000):
    negativeNewList.append(row["url"])

# composed of user_id, 20 history as query, 10 history as positive doc, 10 from neg as negative doc
dataUrls = []
for k in userHistory.keys():
    query20 = random.sample(userHistory[k], 20)
    doc10 = random.sample(list(set(userHistory[k]).difference(set(query20))), 10)
    dataUrls.append([k, query20, doc10])

assert len(negativeNewList) // len(userHistory.keys()) >= 10  # make sure we have enough negative sample

for k in range(len(dataUrls)):
    try:
        negTemp = []
        # if len(negativeNewList) > 10:
        negTemp = random.sample(list(set(negativeNewList).difference(set(userHistory[dataUrls[k][0]]))), 10)
        dataUrls[k].append(negTemp)
        negativeNewList = list(set(negativeNewList) ^ set(negTemp))
    except Exception as e:
        print(e)

# sampling and labeling
queryList = []
posList = []
negList = []

for i in range(len(dataUrls)):
    for j in range(len(dataUrls[i][1])):
        queryList.append(dataUrls[i][1][j])
    for k in range(len(dataUrls[i][2])):
        posList.append(dataUrls[i][2][k])
    for m in range(len(dataUrls[i][3])):
        negList.append(dataUrls[i][3][m])
urlsList = queryList + posList + negList

# get docs
sentences = getNewsSentences(urlsList, logger=logger)

# faltten
for i in range(len(sentences)):
    sentences[i] = flattenLists(sentences[i])
docs = sentences

# upper lower case
if True:
    for i in pb(list(range(len(docs))), logger=logger, message="Lower casing"):
        for u in range(len(docs[i])):
            docs[i][u] = docs[i][u].lower()

# lemmitization
if True:
    lemmatizer = WordNetLemmatizer()
    #pbar = ProgressBar(len(docs), logger=logger, message="Lemmatization")
    for i in range(len(docs)):
        for u in range(len(docs[i])):
            docs[i][u] = lemmatizer.lemmatize(docs[i][u])
        #pbar.tic()

# filtering with DF
docs = filterCorpus(docs, minDF=1/2000, maxDF=300,
                    removeEmptyDocs=False, allowEmptyDocs=False, logger=logger)
for doc in docs: assert len(doc) > 0

# to str
def toStr(sentencesList):
    for i in range(len(sentencesList)):
        sentencesList[i] = ' '.join(sentencesList[i])
    return sentencesList

corpus = toStr(docs)
for corp in corpus: assert len(corp) > 0

# dict url->doc
urlDocs = dict()
for i in range(len(urlsList)):
    urlDocs[urlsList[i]] = corpus[i]

# write to csv
h = ["sentence1","sentence2","label"]
with open('/home/yuting/PycharmProjects/data/dssm_test_train.csv', 'w', newline='') as csvfile:
    writer  = csv.writer(csvfile)
    writer.writerow(h)
    for i in range(len(dataUrls)):
        query = ""
        for j in range(len(dataUrls[i][1])):
            query += urlDocs[dataUrls[i][1][j]]
            for k in range(len(dataUrls[i][2])):
                posSamp = []
                pos = urlDocs[dataUrls[i][2][k]]
                posSamp.append(query)
                posSamp.append(pos)
                posSamp.append("1")
                writer.writerow(posSamp)
            for m in range(len(dataUrls[i][3])):
                negSamp = []
                neg = urlDocs[dataUrls[i][3][m]]
                negSamp.append(query)
                negSamp.append(neg)
                negSamp.append("0")
                writer.writerow(negSamp)






