# pew in student-venv python indexor.py
# pew in st-venv python /home/hayj/Workspace/Python/Datasets/TwitterNewsrec/twitternewsrec/indexor/indexor.py
# nn pew in twitternewsrec-venv python /home/hayj/wm-dist-tmp/TwitterNewsrec/twitternewsrec/indexor/indexor.py ; observe nohup.out
 
import sys, os; sys.path.append("/".join(os.path.abspath(__file__).split("/")[0:-3]))

# from domainduplicate import config as ddConf
# ddConf.useMongodb = False
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
from nlptools.preprocessing import *
import json

# We make the logger:
logger = Logger("indexor.log")
tt = TicToc(logger=logger)
tt.tic()

# TEST:
TEST = False
if isHostname("hjlat"):
	TEST = True
if TEST:
	logger.log("#"*30 + ">" + "\n" + "#"*20 + " TEST MODE>" + "\n" + "#"*30 + ">")

# We get the config:
currentDir = execDir(__file__)
config = fromJsonFile(currentDir + "/config.json")

# We find the dataDir:
if config["dataDir"] is None:
	dirs = sortedGlob(dataDir() + "/TwitterNewsrec/twitternewsrec*")
	theMax = -1
	for current in dirs:
		numbers = getAllNumbers(current)
		if numbers is not None and len(numbers) > 0:
			number = numbers[-1]
			if number > theMax:
				theMax = number
	config["dataDir"] = dataDir() + "/TwitterNewsrec/twitternewsrec" + str(theMax)
if not isDir(config["dataDir"]):
	raise Exception("Please set the data directory (absolute path) in the indexor config file.")
logger.log("Getting data in " + config["dataDir"])

# We set user and passwords:
if isHostname("datascience01") and config["user"] is None and config["password"] is None:
	(user, password, host) = getOctodsMongoAuth()
	config["user"] = user
	config["password"] = password

# We make all collections:
mongoCollectionKwargs = \
{
    "giveTimestamp": False,
    "giveHostname": False,
    "verbose": True,
    "logger": logger,
    "user": config["user"],
    "password": config["password"],
    "port": "27017",
    "host": config["host"],
}
newsCollection = MongoCollection\
(
	config["dbName"],
    "news",
    indexOn=["url"],
	indexNotUniqueOn=["lastUrlDomain"],
    **mongoCollectionKwargs,
)
usersCollection = MongoCollection\
(
	config["dbName"],
    "users",
    indexOn=["user_id"],
	indexNotUniqueOn=None,
    **mongoCollectionKwargs,
)

# Deleting collections:
security = False
if TEST:
	security = False
newsCollection.resetCollection(security=security)
usersCollection.resetCollection(security=security)

# We insert all news:
files = sortedGlob(config["dataDir"] + "/news/*.bz2")
pbar = ProgressBar(len(files), logger=logger, message="Inserting all news")
for filePath in files:
	ndj = NDJson(filePath)
	for current in ndj:
		scrap = current["scrap"]
		if dictContains(scrap, "text"):
			scrap["text"] = hardPreprocess(scrap["text"])
		newsCollection.insert(current)
	pbar.tic()

# We insert all users:
files = sortedGlob(config["dataDir"] + "/users/*.bz2")
pbar = ProgressBar(len(files), logger=logger, message="Inserting all users")
for filePath in files:
	ndj = NDJson(filePath)
	for current in ndj:
		if dictContains(current, "tweets"):
			for tweet in current["tweets"]:
				if dictContains(tweet, "text"):
					tweet["text"] = hardPreprocess(tweet["text"])
		usersCollection.insert(current)
	pbar.tic()

# We iterate all users to make the newsUsersMapping:
newsUsersMapping = dict()
ids = usersCollection.distinct("user_id")
pbar = ProgressBar(len(ids), logger=logger, message="Finding all users by news")
doneCount = 0
for id in ids:
	data = usersCollection.findOne({"user_id": id})
	for news in data["news"]:
		if news not in newsUsersMapping:
			newsUsersMapping[news] = []
		newsUsersMapping[news].append(id)
	pbar.tic()

# We insert the newsUsersMapping:
pbar = ProgressBar(len(newsUsersMapping), logger=logger, message="Inserting user list in all news rows")
for url, ids in newsUsersMapping.items():
	newsCollection.updateOne({"url": url}, {"$set": {"users": ids}})
	pbar.tic()

# END:
tt.toc()
