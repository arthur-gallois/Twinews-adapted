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
import random

# Config:
TEST = False
config = \
{
	"seed": 0,
	"test": TEST,
	"datasetVersionName": "twinews1",
	"maxUsers": 5 if TEST else 50,
	"minUsers": 1 if TEST else 50,
	"maxNewsPerUser": 5 if TEST else 50,
	"minNewsPerUser": 2 if TEST else 30,
	"removeAlreadySeenDomainPerUser": False,
}
configHash = objectToHash(config)
random.seed(config["seed"])
(user, password, host) = getLocalhostMongoAuth()
outputDir = tmpDir("twinews-usets") + "/" + configHash
remove(outputDir)
mkdir(outputDir)

# We make the logger:
logger = Logger("uset-extractor.log")
tt = TicToc(logger=logger)
tt.tic()

# We make all collections:
mongoCollectionKwargs = \
{
    "logger": logger,
    "user": user,
    "password": password,
    "host": host,
}
newsCollection = MongoCollection(config["datasetVersionName"], "news", **mongoCollectionKwargs)
usersCollection = MongoCollection(config["datasetVersionName"], "users", **mongoCollectionKwargs)

# We get the uset:
pbar = ProgressBar(config["maxUsers"], logger=logger, message="Collecting users...")
urlParser = URLParser()
uset = []
ids = list(usersCollection.distinct("user_id"))
ids = shuffle(ids)
usersCount = 0
alreadySeenNews = set()
usersIds = set()
for userId in ids:
	userData = usersCollection.findOne({"user_id": userId})
	news = userData['news']
	if dictContains(userData, 'news'):
		news = set(news)
		news = setSubstract(news, alreadySeenNews)
		newNews = []
		domains = set()
		for url in news:
			newsData = newsCollection.findOne({"url": url})
			if newsData is not None:
				currentDomain = newsData["lastUrlDomain"]
				if config["removeAlreadySeenDomainPerUser"]:
					if currentDomain not in domains:
						newNews.append(url)
						domains.add(currentDomain)
				else:
					newNews.append(url)
		news = newNews
		if len(news) >= config["minNewsPerUser"]:
			news = list(news)
			news = shuffle(news)
			news = news[:config["maxNewsPerUser"]]
			for url in news:
				newsData = newsCollection.findOne({"url": url})
				row = {"label": str(userId), 'url': url, 'sentences': newsData["scrap"]["sentences"], 'domain': newsData["lastUrlDomain"]}
				alreadySeenNews.add(url)
				uset.append(row)
				usersIds.add(userId)
			pbar.tic()
			usersCount += 1
	if usersCount >= config["maxUsers"]:
		break

# We print infos:
log("We got " + str(len(usersIds)) + " users:\n" + str(sorted(usersIds)), logger)
log("We got " + str(len(uset)) + " news", logger)
if len(usersIds) < config["minUsers"]:
	raise Exception("Not enough users")

# We store the uset:
file = NDJson(outputDir + "/0.ndjson.bz2")
file.append(uset)

# We store the config:
toJsonFile(config, outputDir + "/config.json")

# END:
tt.toc()
