# nn pew in st-venv python ~/Workspace/Python/Datasets/Twinews/twinews/indexor/indexor2.py

from systemtools.basics import *
from systemtools.file import *
from systemtools.location import *
from systemtools.logger import *
from systemtools.printer import *
from datatools.jsonutils import *
from databasetools.mongo import *
from machinelearning.iterator import *
from datatools.url import *
from newstools.newsscraper import *
from nlptools import preprocessing
import json
from nlptools.news.parser import *

# Config:
TEST = False
datasetVersionName = "twinews1"
(user, password, host) = getLocalhostMongoAuth()

# We make the logger:
logger = Logger("indexor.log")
tt = TicToc(logger=logger)
tt.tic()

# We find the dataDir:
dataRootPath = dataDir() + "/Twinews/" + datasetVersionName
assert isDir(dataRootPath)

# We make all collections:
mongoCollectionKwargs = \
{
	"giveTimestamp": False,
    "giveHostname": False,
    "verbose": True,
    "logger": logger,
    "user": user,
    "password": password,
    "host": host,
}
newsCollectionSingleton = None
def getNewsCollection():
	global newsCollectionSingleton
	global mongoCollectionKwargs
	if newsCollectionSingleton is None:
		newsCollectionSingleton = MongoCollection\
		(
			datasetVersionName,
		    "news",
			indexOn=["url"],
			indexNotUniqueOn=["lastUrlDomain"],
		    **mongoCollectionKwargs,
		)
	return newsCollectionSingleton
usersCollectionSingleton = None
def getUsersCollection():
	global usersCollectionSingleton
	global mongoCollectionKwargs
	if usersCollectionSingleton is None:
		usersCollectionSingleton = MongoCollection\
		(
			datasetVersionName,
		    "users",
		    indexOn=["user_id"],
			indexNotUniqueOn=None,
		    **mongoCollectionKwargs,
		)
	return usersCollectionSingleton
newsCollection = getNewsCollection()
usersCollection = getUsersCollection()

# Deleting collections:
newsCollection.resetCollection(security=False)
usersCollection.resetCollection(security=False)

def newsGenFunct(containers, logger=None, verbose=True):
	if not isinstance(containers, list):
		containers = [containers]
	for container in containers:
		for row in NDJson(container, logger=logger, verbose=verbose):
			raw_text = None
			isGood = False
			(text, sentences) = (None, None)
			try:
				scrap = row["scrap"]
				raw_text = newsPreclean(scrap["text"])
				isGood = isGoodArticle(raw_text)
				(text, sentences) = parseNews(raw_text)
			except Exception as e:
				logException(e, logger)
			if isGood and text is not None and raw_text is not None and sentences is not None and len(sentences) > 0:
				# scrap["raw_text"] = raw_text
				scrap["text"] = text
				scrap["sentences"] = sentences
				yield row
			else:
				yield None

# We insert all news:
files = sortedGlob(dataRootPath + "/news/*.bz2")
if TEST:
	files = files[:8]
mli = MLIterator(files, newsGenFunct, logger=logger, parallelProcesses=cpuCount())
notGoodCount = 0
totalCount = 0
for row in mli:
	if row is None:
		notGoodCount += 1
	else:
		newsCollection.insert(row)
	totalCount += 1
log("We removed " + str(int(notGoodCount / totalCount * 100)) + "% of news.", logger)
tt.tic("News indexed")


def usersGenFunct(containers, maxUsersPerContainer=None, logger=None, verbose=True):
	if not isinstance(containers, list):
		containers = [containers]
	for container in containers:
		usersCount = 0
		for row in NDJson(container, logger=logger, verbose=verbose):
			try:
				if dictContains(row, "tweets"):
					for tweet in row["tweets"]:
						if dictContains(tweet, "text"):
							tweet["text"] = preprocessing.preprocess\
							(
								tweet["text"], logger=logger,
								doQuoteNormalization=True,
								doReduceBlank=True,
								keepNewLines=True,
								stripAccents=True,
								doRemoveUrls=True,
								doLower=False,
								doBadlyEncoded=True,
								doReduceCharSequences=True,
								charSequencesMaxLength=3,
								replaceUnknownChars=True,
								unknownReplacer=" ",
								doSpecialMap=True,
								doNormalizeEmojis=True,
								doTokenizingHelp=True,
							)
				yield row
				usersCount += 1
				if usersCount >= maxUsersPerContainer:
					break
			except Exception as e:
				logException(e, logger)

# We insert all users:
files = sortedGlob(dataRootPath + "/users/*.bz2")
if TEST:
	files = files[:8]
mli = MLIterator(files, usersGenFunct, genKwargs={"maxUsersPerContainer": 30 if TEST else None},
	logger=logger, parallelProcesses=cpuCount())
for row in mli:
	usersCollection.insert(row)
tt.tic("Users indexed")


# We iterate all users to make the newsUsersMapping:
newsUsersMapping = dict()
ids = usersCollection.distinct("user_id")
for userId in pb(ids, logger=logger, message="Finding all users by news"):
	data = usersCollection.findOne({"user_id": userId})
	for news in data["news"]:
		if news not in newsUsersMapping:
			newsUsersMapping[news] = []
		newsUsersMapping[news].append(userId)
tt.tic("Users by news collected")

# We insert the newsUsersMapping:
for url, ids in pb(newsUsersMapping.items(), logger=logger, message="Inserting user list in all news rows"):
	newsCollection.updateOne({"url": url}, {"$set": {"users": ids}})
tt.tic("newsUsersMapping inserted")

# END:
tt.toc()
