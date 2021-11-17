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
from sklearn.metrics.pairwise import cosine_similarity, pairwise_distances
import pymongo
import gridfs
from twinews.resources import *
from twinews import config as twinewsConf

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

def getMongoHost2():
	weAreOnOctods = False
	try:
		if octods():
			weAreOnOctods = True
	except: pass
	if weAreOnOctods:
		return '127.0.0.1'
	else:
		return '212.129.44.40'

def pruneScores(rk):
	if rk is None or len(rk) == 0:
		raise Exception("Rankings not valid")
	if isinstance(rk[0], tuple):
		return [e[0] for e in rk]
	else:
		return rk

def getMongoAuth(*args, user='student', **kwargs):
	if twinewsConf.mongoLocation == 'lri':
		password = getDataEncryptorSingleton()["mongoauth"]['titanv']
		return (user, password[user], getMongoHost())
	else:
		user = 'hayj'
		password = getDataEncryptorSingleton()["mongoauth"]['datascience01']
		return (user, password[user], getMongoHost2())

def getDominancesSD(logger=None, verbose=True):
	try:
		(user, password, host) = getMongoAuth(user='hayj')
		dominancesSD = SerializableDict('twinews-dominances', logger=logger, user=user, password=password, host=host, verbose=verbose, useMongodb=True)
		return dominancesSD
	except Exception as e:
		return dict()

def getCombinIds(splitVersion=None, noSubsampling=True):
	twinewsRankings = getTwinewsRankings(verbose=False)
	combinsSplit = set()
	for current in twinewsRankings.keys():
		if current.startswith('combin'):
			meta = twinewsRankings.getMeta(current)
			if not noSubsampling or meta['maxUsers'] is None:
				if splitVersion is None:
					combinsSplit.add(current)
				elif meta['splitVersion'] == splitVersion:
					combinsSplit.add(current)
	return combinsSplit

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
	if user is None or password is None or host is None:
		if user is None:
			(user, password, host) = getMongoAuth()
		else:
			(user, password, host) = getMongoAuth(user=user)
	kwargs['user'] = user
	kwargs['password'] = password
	kwargs['host'] = host
	kwargs['version'] = datasetVersion
	return kwargs

def getNewsCollection(*args, **kwargs):
	"""
		This function return the twinews.news collection.
	"""
	kwargs = makeMongoCollectionKwargs(*args, **kwargs)
	return MongoCollection\
	(
		"twinews", "news",
		indexOn=["url"],
		indexNotUniqueOn=["domain", "lastUrlDomain", "lastUrl", "isGoodArticle", "minTimestamp", "maxTimestamp"],
		**kwargs,
	)

def getUsersCollection(*args, **kwargs):
	"""
		This function return the twinews.users collection.
	"""
	kwargs = makeMongoCollectionKwargs(*args, **kwargs)
	return MongoCollection\
	(
		"twinews", "users",
		indexOn=["user_id"],
		indexNotUniqueOn=["datasetRelevanceScore", "notBotScore", "minTimestamp", "maxTimestamp"],
		**kwargs,
	)

def getTwinewsScores(logger=None, verbose=True):
	"""
		This function return the twinews.scores collection.
	"""
	user = 'hayj' if isUser('hayj') else 'student'
	(user, password, host) = getMongoAuth(user=user)
	kwargs = makeMongoCollectionKwargs(user=user, password=password, host=host, logger=logger, verbose=verbose, datasetVersion=None)
	twinewsScores = MongoCollection\
	(
		"twinews", "scores",
		**kwargs,
	)
	if user == 'hayj':
		twinewsScores.collection.create_index([("id", pymongo.ASCENDING), ("metric", pymongo.ASCENDING)], unique=True, background=True)
	return twinewsScores

def addTwinewsScore(modelKey, metric, score, *args, **kwargs):
	"""
		This function allows to add a new score.
		The primary key is on id (modelKey) and metric so the function can throw a `DuplicateKeyError`.
	"""
	score = float(score)
	if modelKey not in getTwinewsRankings():
		raise Exception(modelKey + " must be in the twinews-rankings GridFS")
	s = getTwinewsScores(*args, **kwargs)
	s.insert({'id': modelKey, 'metric': metric, 'score': score})

def getEvalData(version, maxExtraNews=0, maxUsers=None, logger=None, verbose=True):
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
substract
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
	for url in pb(urls, logger=logger, verbose=verbose):
		try:
			assert newsCollectionForGetNewsField is not None
			data = newsCollectionForGetNewsField[url]
			data = data[field]
			if asDict:
				result[url] = data
			else:
				result.append(data)
		except Exception as e:
			logError(url + " not found.", logger, verbose=verbose)
			logException(e, logger, verbose=verbose)
			result.append([])
	if isUnique:
		return result[0]
	else:
		return result
def getNewsText(*args, **kwargs):
	"""
		This function return the text of a list of urls from the news collection
	"""
	return getNewsField(*args, field='detokText', **kwargs)
def getNewsSentences(*args, **kwargs):
	return getNewsField(*args, field='sentences', **kwargs)
# def getNewsFilteredSentences(*args, **kwargs):
# 	return getNewsField(*args, field='filtered_sentences', **kwargs)
# def getNewsFilteredText(*args, **kwargs):
# 	return getNewsField(*args, field='filtered_text', **kwargs)


def getTwinewsRankings(logger=None, verbose=True):
	"""
		This function return the mongo GridFS corresponding to Twinews rankings.
		See this documentation to know how to retrieve rankings by requesting
		specific parameters you used for a specific model:
		https://github.com/hayj/DatabaseTools#mongofs
	"""
	(user, password, host) = getMongoAuth()
	return MongoFS\
	(
		user=user, password=password, host=host,
		dbName="twinews-rankings",
		logger=logger, verbose=verbose,
	)

def pruneRankings(modelKey):
	twinewsRankings = getTwinewsRankings(verbose=False)
	meta = twinewsRankings.getMeta(modelKey)
	key = meta['id']
	del meta['id']
	del twinewsRankings[modelKey]
	twinewsRankings.insert(key, None, **meta)

def removeRankingsAndScores(modelKey):
	twinewsRankings = getTwinewsRankings(verbose=False)
	twinewsScores = getTwinewsScores(verbose=False)
	del twinewsRankings[modelKey]
	twinewsScores.collection.delete_many({'id': modelKey})


def parseRankingConfig(modelName, config, logger=None, verbose=True):
	"""
		This function check a config and return a key with a new config.
	"""
	if 'splitVersion' not in config:
		raise Exception("You need to specify the split version in config using the `splitVersion` field")
	if 'maxUsers' not in config:
		raise Exception("You need to add the `maxUsers` field in config (can be None)")
	if 'model' in config:
		if config['model'] != modelName:
			raise Exception("The `model` field in config must be equal to modelName (first positional arg)")
	else:
		config['model'] = modelName
	configHash = objectToHash(config)[:5]
	key = modelName + '-' + configHash
	return (key, config)

def addRankings(*args, **kwargs):
	return addRanking(*args, **kwargs)
def addRanking(modelName, ranks, config, logger=None, verbose=True):
	"""
		This function add a ranking to the mongo GridFS.

		You need to choose a model name such as "lda", "dssm"...
		This model name will be set as the model name you gave plus 5 first letters of the hash of the config to ensure you do not erase you ranking with differents parameters.

		You give ranks that have the same structure as candidates in evaluation data but instead of sets for urls, it is lists to give the ranking.

		You also need to give the config of your model containing your parameters and, at least, splitVersion and maxUsers (for the sub-sampling).

		Warning: do not give the field `model` in config, it will be automatically added (modelName).
	"""
	(key, config) = parseRankingConfig(modelName, config, logger=logger, verbose=verbose)
	twinewsRankings = getTwinewsRankings(logger=logger, verbose=verbose)
	try:
		if rankingExistsButIsNone(modelName, config, logger=logger, verbose=verbose):
			del twinewsRankings[key]
			twinewsRankings.insert(key, ranks, **config)
		elif rankingExists(modelName, config, logger=logger, verbose=verbose):
			raise Exception(key + " is already in the database.",)
		else:
			twinewsRankings.insert(key, ranks, **config)
	except gridfs.errors.FileExists:
		logError(key + " is already in the database!", logger, verbose=verbose)
	except Exception as e:
		logException(e, logger, verbose=verbose)


def rankingExists(modelName, config, logger=None, verbose=True):
	"""
		Use this function to check if a rankings exists and to do not compute it again.
	"""
	(key, config) = parseRankingConfig(modelName, config, logger=logger, verbose=verbose)
	twinewsRankings = getTwinewsRankings(logger=logger, verbose=verbose)
	return key in twinewsRankings

def rankingExistsAndIsNotNone(modelName, config, logger=None, verbose=True):
	(key, config) = parseRankingConfig(modelName, config, logger=logger, verbose=verbose)
	log("Checking if " + str(key) + " exists...", logger, verbose=verbose)
	twinewsRankings = getTwinewsRankings(logger=logger, verbose=verbose)
	actuallyExists = False
	if key in twinewsRankings and twinewsRankings.collection.find_one({'id': key, 'length': {'$gt': 100}}) is not None:
		actuallyExists = True
	if actuallyExists:
		log(str(key) + " exists.", logger, verbose=verbose)
	else:
		log(str(key) + " does not exist.", logger, verbose=verbose)
	return actuallyExists


def rankingExistsButIsNone(modelName, config, logger=None, verbose=True):
	(key, config) = parseRankingConfig(modelName, config, logger=logger, verbose=verbose)
	twinewsRankings = getTwinewsRankings(logger=logger, verbose=verbose)
	if key in twinewsRankings and twinewsRankings.collection.find_one({'id': key, 'length': {'$gt': 100}}) is None:
		return True
	return False



def getNewsTitles(*args, **kwargs):
	return getNewsField(*args, field='title', **kwargs)


if __name__ == '__main__':
	evalData = getEvalData(1, maxExtraNews=0, maxUsers=100)
	bp(evalData.keys(), 5)
	log(b(evalData['meta']))