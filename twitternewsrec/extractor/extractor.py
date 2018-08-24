# pew in st-venv python /home/hayj/Workspace/Python/Datasets/TwitterNewsrec/twitternewsrec/extractor/extractor.py
# nn pew in twitternewsrec-venv python /home/hayj/wm-dist-tmp/TwitterNewsrec/twitternewsrec/extractor/extractor.py ; observe nohup.out

import sys, os; sys.path.append("/".join(os.path.abspath(__file__).split("/")[0:-3]))

# from domainduplicate import config as ddConf
# ddConf.useMongodb = False
from systemtools.basics import *
from systemtools.file import *
from systemtools.location import *
from systemtools.logger import *
from datatools.jsonreader import *
from twitternewsrec.user.topuser import *
from twitternewsrec.user.twitteruser import *
from twitternewsrec.extractor.utils import *
from datastructuretools.processing import *


"""
	Config file comments:

	 * version: if null, the version will automatically be calcultated according to existing datasets
	 * anonymize: not yet implemented
"""


# We make the logger:
logger = Logger("extraction.log")
tt = TicToc(logger=logger)
tt.tic()

# TEST:
TEST = True
if TEST:
	logger.log("=========> TEST MODE <=========")

# We get all folder paths and the config:
currentDir = execDir(__file__)
config = jsonToDict(currentDir + "/config.json")
dataDir = dataDir() + config["dataSubDir"]
mkdir(dataDir)
version = config["version"]
if version is None:
	version = 0
	for current in sortedGlob(dataDir + "/" + config["datasetFolderName"] + "*"):
		firstNumber = getFirstNumber(current)
		if firstNumber is not None and firstNumber > version:
			version = firstNumber
	version += 1
dataDir += "/" + config["datasetFolderName"] + str(version)
mkdir(dataDir)
logger.p("Starting generation of the dataset v" + str(version) + " in " + dataDir)

# We change the config for TEST:
if TEST:
	config["maxUser"] = 20
	config["compress"] = False
	config["overlapBatchMaxSize"] = 50
	config["overlapSimilarityThreshold"] = 0.6

# We copy the config file:
if config["copyConfig"]:
	copyFile(currentDir + "/config.json", dataDir + "/extractor-config.json")

# We get top users:
logger.log("Getting top user according to datasetRelevanceScore...")
top = getTopUser\
(
	"datasetRelevanceScore",
	relevanceFieldThreshold=config["datasetRelevanceThreshold"],
	notBotThreshold=config["notBotThreshold"],
	logger=logger,
	verbose=True
)
top = top[:config["maxUser"]]
tt.tic("We got top users.")


# We get all good news:
logger.log("Getting all good news urls...")
def isGoodNews(data):
	try:
		if data["status"] not in \
		[
			REQUEST_STATUS.timeoutWithContent.name,
			REQUEST_STATUS.success.name,
		]:
			return False
		nuf = getNewsUrlFilterSingleton(logger=logger)
		newsCrawl = getNewsCrawlSingleton(logger=logger)
		url = data["url"]
		scrap = data["scrap"]
		if len(scrap["boilerpipe"]["text"]) < config["minNewsTextSize"]:
			return False
	except Exception as e:
		logException(e, logger)
		return False
	return True

newsCrawl = getNewsCrawlSingleton(logger=logger)
# Looks like {"nytimes.com": [<urls>], "washingtonpost.com": ..., ...}
newsUrls = dict()
i = 0
alreadySawUrls = set()
pb = ProgressBar(len(top), printRatio=0.05)
for userId in top:
	u = TwitterUser(userId)
	for url in u.getNews(ignoreAlreadyCrawled=False):
		if url not in alreadySawUrls:
			if url in newsCrawl:
				newsData = newsCrawl.findOne({"url": url}, projection={"html": False})
				if config["domainsFilter"] is None or len(config["domainsFilter"]) == 0 or newsData["lastUrlDomain"] in config["domainsFilter"]:
					if isGoodNews(newsData):
						if newsData["lastUrlDomain"] not in newsUrls:
							newsUrls[newsData["lastUrlDomain"]] = []
						newsUrls[newsData["lastUrlDomain"]].append(url)
		alreadySawUrls.add(url)
	pb.tic("Current user: " + str(userId))
	i += 1
tt.tic("We got " + str(len(alreadySawUrls)) + " news urls.")

exit()

# We store all news domain per domain:
for lastUrlDomain in newsUrls.keys():
	# First we get all news:
	logger.log("Getting all news data of " + lastUrlDomain + "...")
	urlsForThisDomain = news[lastUrlDomain]
	newsForThisDomain = []
	for url in urlsForThisDomain:
		newsForThisDomain.append(newsCrawl[url])
	tt.tic("We got all news data for " + lastUrlDomain + ".")


	# We handle duplicates:
	logger.log("We remove duplicates news...")
	newNews = dict()
	urlMapping = dict()
	# for lastUrlDomain, newsForThisDomain in news.items():
	# 	print(len(newsForThisDomain))
	# # exit()
	# print("\n" * 4)
	tt = TicToc()
	for lastUrlDomain, newsForThisDomain in news.items():
		# print(len(newsForThisDomain))
		tt.tic(display=False)
		newNewsForThisDomain, urlMappingForThisDomain = reduceDuplicates(newsForThisDomain, logger=logger, verbose=False, similarityThreshold=config["overlapSimilarityThreshold"], ngramsMin=config["overlapNgramsMin"], batchMaxSize=config["overlapBatchMaxSize"])
		tt.tic()
		urlMapping = mergeDicts(urlMapping, urlMappingForThisDomain)
		newNews[lastUrlDomain] = newNewsForThisDomain
		gc.collect()
		# print(len(urlMapping))
		# print(len(newNews))
		# print(objectSize(urlMapping))
		# print(objectSize(newNews))
	news = newNews
	tt.tic("Duplicates removed.")

	# We store all news in multiple json object files per domain:
	logger.log("We store all news...")
	newsDir = dataDir + "/news"
	mkdir(newsDir)
	for lastUrlDomain, newsForThisDomain in news.items():
		filePath = newsDir + "/" + strToFilename(lastUrlDomain) + ".json"
		fileContent = ""
		for newsData in newsForThisDomain:
			for field in config["newsCrawlFieldExcludes"]:
				if field in newsData:
					del newsData[field]
			if config["removeHtml"] and "html" in newsData:
				del newsData["html"]
			fileContent += json.dump(newsData) + "\n"
		strToFile(fileContent, filePath)
	tt.tic("News stored.")


# printLTS(reduceDictStr(news))

# We calculate duplicates:

# printLTS(urls)
# printLTS(lastUrls)




