from systemtools.basics import *
from systemtools.printer import *
from systemtools.file import *
from systemtools.location import *
from systemtools.system import *
from datatools.dataencryptor import *
from datastructuretools.hashmap import *

def getTipiStudentMongoAuth(*args, **kwargs):
    password = getDataEncryptorSingleton()["mongoauth"]['titanv']
    host = '127.0.0.1'
    return ('student', password['student'], host)

(user, password, host) = getTipiStudentMongoAuth()
from systemtools.hayj import *
from systemtools.basics import *
from systemtools.file import *
from systemtools.location import *
from systemtools.printer import *
from databasetools.mongo import *
from newstools.goodarticle.utils import *
from nlptools.preprocessing import *
from nlptools.news import parser as newsParser
import copy

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

