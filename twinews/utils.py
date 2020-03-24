try:
	from systemtools.hayj import *
except: pass
from systemtools.basics import *
from systemtools.file import *
from systemtools.location import *
from systemtools.printer import *
from databasetools.mongo import *
from datatools.dataencryptor import *
from datastructuretools.hashmap import *
from newstools.goodarticle.utils import *
from nlptools.preprocessing import *
from nlptools.news import parser as newsParser
import copy
import pickle
import gzip
from math import log2
from math import sqrt
from numpy import asarray

def getMongoHost():
	weAreAtLRI = False
	try:
		if lri():
			weAreAtLRI = True
	except: pass
	if weAreAtLRI:
		return 'titanv.lri.fr'
	else:
		return '127.0.0.1'

def getMongoAuth(*args, user='student', **kwargs):
	password = getDataEncryptorSingleton()["mongoauth"]['titanv']
	return (user, password[user], getMongoHost())

def makeMongoCollectionKwargs\
(
	user=None,
	password=None,
	host=None,
	datasetVersion="1.0",
	logger=None,
	verbose=True,
):
	kwargs = \
	{
		"giveTimestamp": False,
		"giveHostname": False,
	}
	kwargs['logger'] = logger
	kwargs['verbose'] = verbose
	if user is None:
		(user, password, host) = getMongoAuth()
	kwargs['user'] = user
	kwargs['password'] = password
	kwargs['host'] = host
	kwargs['version'] = datasetVersion
	return kwargs

def getNewsCollection(*args, **kwargs):
	kwargs = makeMongoCollectionKwargs(*args, **kwargs)
	return MongoCollection\
	(
		"twinews", "news",
		indexOn=["url"],
		indexNotUniqueOn=["domain", "lastUrlDomain", "lastUrl", "isGoodArticle", "minTimestamp", "maxTimestamp"],
		**kwargs,
	)

def getUsersCollection(*args, **kwargs):
	kwargs = makeMongoCollectionKwargs(*args, **kwargs)
	return MongoCollection\
	(
		"twinews", "users",
		indexOn=["user_id"],
		indexNotUniqueOn=["datasetRelevanceScore", "notBotScore", "minTimestamp", "maxTimestamp"],
		**kwargs,
	)

def getEvalData(version, maxExtraNews=None, maxUsers=None, logger=None, verbose=True):
	"""
		This function return the evaluation data with the right version in the right folder.
		Use `maxUsers` to sub-sample the dataset for test purposes.

		Usage example:

			evalData = getEvalData(1, maxExtraNews=100 if TEST else None, maxUsers=100 if TEST else None, logger=logger)
			(trainUsers, testUsers, trainNews, testNews, candidates, extraNews) = \
			(evalData['trainUsers'], evalData['testUsers'], evalData['trainNews'],
			 evalData['testNews'], evalData['candidates'], evalData['extraNews'])
			bp(evalData.keys(), 5, logger)
			log(b(evalData['stats']), logger)
	"""
	# Creating tt:
	tt = TicToc(logger=logger)
	tt.tic(display=False)
	# Getting eval data:
	(user, password, host) = getMongoAuth()
	mfs = MongoFS(dbName="twinews-splits", user=user, password=password, host=host)
	evalData = mfs[version]
	assert evalData is not None
	evalData = mergeDicts(evalData, {'meta': mfs.getMeta(version)})
	tt.tic("Eval data loaded")
	# Sub-sampling:
	if maxUsers is not None and maxUsers > 0:
		evalData = subsampleEvalData(evalData, maxUsers=maxUsers)
	# Checking data:
	checkEvalData(evalData)
	# Getting extraNews (WARNING, here it's very long on the computer of Yuting because the function request the database):
	extraNews = getExtraNews(evalData['trainNews'].union(evalData['testNews']), logger=logger, limit=maxExtraNews)
	evalData['extraNews'] = extraNews
	if len(extraNews) > 0:
		tt.tic("Extra news downloaded")
	# Printing the duration:
	tt.toc("Got Twinews evaluation data")
	return evalData


def checkEvalData(evalData):
	"""
		This function check the shape of evaluation datas.
	"""
	(trainUsers, testUsers, trainNews, testNews, candidates) = \
	(evalData['trainUsers'], evalData['testUsers'], evalData['trainNews'],
	evalData['testNews'], evalData['candidates'])
	candidatesUrls = set()
	for userId, news in candidates.items():
		for n in news[0]:
			candidatesUrls.add(n)
	trainUsersUrls = set()
	for userId, news in trainUsers.items():
		for n in news:
			trainUsersUrls.add(n)
	testUsersUrls = set()
	for userId, news in testUsers.items():
		for n in news:
			testUsersUrls.add(n)
	assert len(trainNews) == len(trainUsersUrls)
	assert len(testUsersUrls.union(candidatesUrls)) == len(testNews)
	assert len(trainUsersUrls) + len(testUsersUrls) == len(trainUsersUrls.union(testUsersUrls))
	assert len(trainNews) + len(testNews) == len(trainNews.union(testNews))
	assert len(trainNews) + len(testNews) == len(trainNews.union(testNews).union(candidatesUrls))
	assert len(trainUsersUrls) + len(testUsersUrls) < len(trainNews.union(candidatesUrls))
	assert len(testUsersUrls) < len(candidatesUrls)

def subsampleEvalData(evalData, maxUsers=100):
	"""
		This function return a sub sample of evalData to execute models in test mode.

		Usage:

			(trainUsers, testUsers, trainNews, testNews, candidates) = subsampleEvalData(evalData, maxUsers=100)
	"""
	# Getting a sub-sample of user ids:
	rd = random.Random(0)
	userIds = rd.sample(sorted(list(evalData['testUsers'].keys())), maxUsers)
	# Sub-sampling users:
	evalData['trainUsers'] = dictSelect(evalData['trainUsers'], userIds)
	evalData['testUsers'] = dictSelect(evalData['testUsers'], userIds)
	# Sub-sampling candidates:
	evalData['candidates'] = dictSelect(evalData['candidates'], userIds)
	# Getting urls:
	urls = set()
	for users in (evalData['trainUsers'], evalData['testUsers']):
		for userId, news in users.items():
			for n in news.keys():
				urls.add(n)
	for userId, bulks in evalData['candidates'].items():
		for news in bulks:
			for n in news:
				urls.add(n)
	# Sub-sampling news:
	evalData['trainNews'] = set([n for n in evalData['trainNews'] if n in urls])
	evalData['testNews'] = set([n for n in evalData['testNews'] if n in urls])
	# We return all sub samples:
	return evalData

def getExtraNews(blackNews, limit=None, logger=None, verbose=True):
	"""
		This function return a list of urls (primary key of the news collection) that are not in testNews U trainNews
	"""
	if limit == 0:
		return set()
	newsCollection = getNewsCollection(logger=logger, verbose=verbose)
	extraNews = set()
	for n in newsCollection.distinct('url'):
		if n not in blackNews:
			extraNews.add(n)
			if limit is not None and len(extraNews) == limit:
				break
	return extraNews


newsCollectionForGetNewsField = None
def getNewsField(urls, field, asDict=False, logger=None, verbose=True):
	"""
		Takes a list of urls or a unique url
	"""
	global newsCollectionForGetNewsField
	isUnique = not isinstance(urls, list)
	assert not (isUnique and asDict)
	if not isinstance(urls, list):
		urls = [urls]
	if asDict:
		result = dict()
	else:
		result = []
	if newsCollectionForGetNewsField is None:
		newsCollectionForGetNewsField = getNewsCollection(logger=logger, verbose=verbose)
	for url in pb(urls, logger=logger):
		data = newsCollectionForGetNewsField[url][field]
		if asDict:
			result[url] = data
		else:
			result.append(data)
	if isUnique:
		return result[0]
	else:
		return result
def getNewsText(*args, **kwargs):
	"""
		This function return the text of a list of urls from the news collection
	"""
	return getNewsField(*args, field='text', **kwargs)
def getNewsSentences(*args, **kwargs):
	return getNewsField(*args, field='sentences', **kwargs)
def getNewsFilteredSentences(*args, **kwargs):
	return getNewsField(*args, field='filtered_sentences', **kwargs)
def getNewsFilteredText(*args, **kwargs):
	return getNewsField(*args, field='filtered_text', **kwargs)

def getDistances(xvectors, yvectors, metric='cosin', logger=None, verbose=False):
    """
        metric can be 'cosine', 'euclidean', 'kl', 'js'
    """
    # Kullback–Leibler and Jensen-Shannon divergence: 
    def kl_divergence(p, q):
        return sum(p[i] * log2(p[i]/q[i]) for i in range(len(p)))
    def js_divergence(p, q):
        m = 0.5 * (p + q)
        return 0.5 * kl_divergence(p, m) + 0.5 * kl_divergence(q, m)
    if metric == 'cosine':
        pass
    elif metric == 'euclidean':
        pass
    elif metric == 'kl':
        metric = kl_divergence
    elif metric == 'js':
        metric = js_divergence
    distances = pairwise_distances(xvectors, yvectors, metric=metric)
    return distances

if __name__ == '__main__':
	evalData = getEvalData(1, maxExtraNews=0, maxUsers=100)
	bp(evalData.keys(), 5)
	log(b(evalData['meta']))