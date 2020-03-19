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

def getEvalData(version):
	"""
		This function return the evaluation data with the right version in the right folder.
	"""
	if isUser("hayj"):
		if lri():
			return deserialize(nosaveDir() + "/twinews-splits/v" + str(version) + ".pickle.gzip")
		else:
			twinewsSplitsDir = tmpDir("twinews-splits")
			bash("rsync -avhuP --delete-after hayj@titanv.lri.fr:~/NoSave/twinews-splits/* " + twinewsSplitsDir)
			return deserialize(twinewsSplitsDir + "/v" + str(version) + ".pickle.gzip")
	elif "yuting" in getUser():
		directoryPath = homeDir() + "/PycharmProjects/data/twinews-splits"
		return deserialize(directoryPath + "/v" + str(version) + ".pickle")

def checkEvalData(trainUsers, testUsers, trainNews, testNews, candidates):
	"""
		This function check the shape of evaluation datas.
	"""
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
	userIds = random.sample(list(evalData['testUsers'].keys()), maxUsers)
	# Sub-sampling users:
	trainUsers = dictSelect(evalData['trainUsers'], userIds)
	testUsers = dictSelect(evalData['testUsers'], userIds)
	# Sub-sampling candidates:
	candidates = dictSelect(evalData['candidates'], userIds)
	# Getting urls:
	urls = set()
	for users in (trainUsers, testUsers):
		for userId, news in users.items():
			for n in news.keys():
				urls.add(n)
	for userId, bulks in candidates.items():
		for news in bulks:
			for n in news:
				urls.add(n)
	# Sub-sampling news:
	trainNews = set([n for n in evalData['trainNews'] if n in urls])
	testNews = set([n for n in evalData['testNews'] if n in urls])
	# Checking data:
	checkEvalData(trainUsers, testUsers, trainNews, testNews, candidates)
	# We return all sub samples:
	return (trainUsers, testUsers, trainNews, testNews, candidates)

def getExtraNews(trainNews, testNews, logger=None, verbose=True):
	"""
		This function return a list of urls (primary key of the news collection) that are not in testNews U trainNews
	"""
	newsCollection = getNewsCollection(logger=logger, verbose=verbose)
	news = trainNews.union(testNews)
	return set([e for e in newsCollection.distinct('url') if e not in news])