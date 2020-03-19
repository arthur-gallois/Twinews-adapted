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
	if isUser("hayj"):
		if lri():
			return deserialize(nosaveDir() + "/twinews-splits/v" + str(version) + ".pickle.gzip")
		else:
			twinewsSplitsDir = tmpDir("twinews-splits")
			bash("rsync -avhuP --delete-after hayj@titanv.lri.fr:~/NoSave/twinews-splits/* " + twinewsSplitsDir)
			return deserialize(twinewsSplitsDir + "/v" + str(version) + ".pickle.gzip")
	elif "yuting" in getUser():

		directoryPath = "/home/yuting/PycharmProjects/data/twinews-splits/"
		return deserialize(directoryPath + "/v" + str(version) + ".pickle")