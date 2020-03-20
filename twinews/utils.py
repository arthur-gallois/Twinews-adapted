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

def getEvalDataPath(version):
	fileName = "v" + str(version) + ".pickle.gzip"
	if isUser("hayj"):
		if lri():
			evalDataPath = nosaveDir() + "/twinews-splits/" + fileName
		else:
			twinewsSplitsDir = tmpDir("twinews-splits")
			bash("rsync -avhuP --delete-after hayj@titanv.lri.fr:~/NoSave/twinews-splits/* " + twinewsSplitsDir)
			evalDataPath = twinewsSplitsDir + "/" + fileName
	elif "yuting" in getUser():
		rootDir = homeDir() + "/PycharmProjects/data"
		bash("rsync -avhuP -e \"ssh -p 2222\" student@212.129.44.40:/data/twinews-splits . " + rootDir)
		evalDataPath = rootDir + "/twinews-splits/" + fileName
	return evalDataPath

def getEvalData(version, extraNewsCount=None, maxUsers=None, logger=None, verbose=True):
	"""
		This function return the evaluation data with the right version in the right folder.
		Use `maxUsers` to sub-sample the dataset for test purposes.

		Usage example:

			evalData = getEvalData(1, extraNewsCount=100 if TEST else None, maxUsers=100 if TEST else None, logger=logger)
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
	evalData = deserialize(getEvalDataPath(version))
	assert evalData is not None
	# Sub-sampling:
	if maxUsers is not None and maxUsers > 0:
		evalData = subsampleEvalData(evalData, maxUsers=100)
	# Checking data:
	checkEvalData(evalData)
	# Getting extraNews:
	extraNews = getExtraNews(evalData['trainNews'].union(evalData['testNews']), logger=logger, limit=extraNewsCount)
	evalData['extraNews'] = extraNews
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
	userIds = random.sample(list(evalData['testUsers'].keys()), maxUsers)
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