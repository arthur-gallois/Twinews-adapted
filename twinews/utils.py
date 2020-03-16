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

def makeMongoColletionKwargs\
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
		(user, password, host) = getTipiStudentMongoAuth()
	kwargs['user'] = user
	kwargs['password'] = password
	kwargs['host'] = host
	kwargs['version'] = datasetVersion
	return kwargs

def getNewsCollection(*args, **kwargs):
	kwargs = makeMongoColletionKwargs()
	return MongoCollection\
	(
		"twinews", "news",
		indexOn=["url"],
		indexNotUniqueOn=["domain", "lastUrlDomain", "lastUrl", "isGoodArticle"],
		**kwargs,
	)

def getUsersCollection(*args, **kwargs):
	kwargs = makeMongoColletionKwargs()
	return MongoCollection\
	(
		"twinews", "users",
		indexOn=["user_id"],
		indexNotUniqueOn=["datasetRelevanceScore", "notBotScore"],
		**kwargs,
	)

