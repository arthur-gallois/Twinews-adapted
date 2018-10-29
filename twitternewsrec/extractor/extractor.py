# nn pew in st-venv python ~/Workspace/Python/Datasets/TwitterNewsrec/twitternewsrec/extractor/extractor.py

import sys, os; sys.path.append("/".join(os.path.abspath(__file__).split("/")[0:-3]))

# from domainduplicate import config as ddConf
# ddConf.useMongodb = False
from systemtools.basics import *
from systemtools.file import *
from systemtools.location import *
from systemtools.logger import *
from datatools.jsonutils import *
from twitternewsrec.user import config as uConf
from twitternewsrec.user.topuser import *
from twitternewsrec.user.twitteruser import *
from twitternewsrec.extractor.utils import *
from datastructuretools.processing import *
from datatools.url import *
from newstools.newsscraper import *
import json


"""
	Config file comments:

	 * version: if null, the version will automatically be calcultated according to existing datasets
	 * anonymize: not yet implemented



# TODO tar TODO comparer tar.gz vs tar avec des gz2 dedans
# Python tar.gz
# https://stackoverflow.com/questions/2018512/reading-tar-file-contents-without-untarring-it-in-python-script
# https://stackoverflow.com/questions/2032403/how-to-create-full-compressed-tar-file-using-python
# https://docs.python.org/3/library/tarfile.html

# TODO copyIndexor
# TODO addUserStatistics
# TODO anonymize (utiliser md5 pour les ids ?)

# TODO merger par titre si le meme titre se retrouve dans max 1% du domaine et que le titre est assez long

# TODO storeExtraNews stocker les news qui ne sont aos deja stockées et qui sont dans les mêmes domaines
"""


# We make the logger:
logger = Logger("extractor-" + getRandomStr() + ".log")
tt = TicToc(logger=logger)
tt.tic()

# TEST:
TEST = False
if isHostname("hjlat"):
	TEST = True
if TEST:
	# uConf.twitterUserScoreVersion = "0.0.11"
	logger.log("#"*30 + ">" + "\n" + "#"*20 + " TEST MODE>" + "\n" + "#"*30 + ">")

# We get the config:
currentDir = execDir(__file__)
config = jsonToDict(currentDir + "/config.json")

# We calclate the compresslevel:
if config["compress"]:
	compresslevel = config["compresslevel"]
else:
	compresslevel = 0

# We change the config for TEST:
indent = None
if TEST:
	indent = None
	config["version"] = 0
	config["maxUser"] = 10
	config["compress"] = True
	config["overlapBatchMaxSize"] = 50
	config["overlapSimilarityThreshold"] = 0.6
	config["maxUsersPerFile"] = 2
	config["maxNewsInRam"] = 10
	# config["domainsFilter"] = \
	# [
	# 	"ft.com",
	# 	"gizmodo.com",
	# 	"go.com",
	# 	"huffingtonpost.ca",
	# 	"huffingtonpost.com",
	# 	"huffingtonpost.co.uk",
	# 	"huffingtonpost.co.za",
	# 	"independent.co.uk",
	# 	"indiewire.com",
	# 	"japantimes.co.jp",
	# 	"koreatimes.co.kr",
	# 	"latimes.com",
	# ]

# We get all folder paths and the config:
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
if TEST and isDir(dataDir):
	removeDirSecure(dataDir)
mkdir(dataDir)
logger.p("Starting generation of the dataset v" + str(version) + " in " + dataDir)

# We copy indexor:
if config["copyIndexor"]:
	indexorDir = getParentDir(execDir(__file__)) + "/indexor"
	removeFile(indexorDir + "/indexor.log")
	copyDir(indexorDir, dataDir)

# We copy indexor:
if config["copyHjupdate"]:
	bs = BashScripts(logger=logger)
	hjupdate = bs.get("hjupdate")
	strToFile(hjupdate, dataDir + "/indexor/hjupdate.sh")

# We copy the README:
if config["copyReadme"]:
	copyFile(execDir(__file__) + "/README.md", dataDir + "/README.md")

# We copy the config file:
if config["copyConfig"]:
	copyFile(currentDir + "/config.json", dataDir + "/extractor-config.json")

# We init statistics:
statistics = dict()

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
logger.log("We got " + str(len(top)) + " top users.\n")
statistics["userCount"] = len(top)


# We get all good news:
logger.log("Getting all good news urls...")
newsCrawl = getNewsCrawlSingleton(logger=logger)

# domains = dict()
# i = 0
# for current in newsCrawl.find():
# 	domain = current["lastUrlDomain"]
# 	if domain not in domains:
# 		domains[domain] = newsCrawl.find({"lastUrlDomain": domain}).count()
# 	i += 1
# 	if i == 100000:
# 		break
# printLTS(sortByValue(domains))
# exit()
# db.getCollection('newscrawl').aggregate([{"$group" : {_id:"$lastUrlDomain", count:{$sum:1}}}, {$sort: {count: -1}}])

# Looks like {"nytimes.com": [<urls>], "washingtonpost.com": ..., ...}
newsUrls = dict()
i = 0
alreadySawUrls = set()
newsCount = 0
for userId in pb(top, logger=logger, message="Getting news urls", printRatio=0.01):
	u = TwitterUser(userId)
	for url in u.getNews(ignoreAlreadyCrawled=False):
		if url not in alreadySawUrls:
			if url in newsCrawl:
				newsData = newsCrawl.findOne({"url": url}, projection={"html": False})
				if config["domainsFilter"] is None or len(config["domainsFilter"]) == 0 or newsData["lastUrlDomain"] in config["domainsFilter"]:
					if isGoodNews(newsData, minMeanLineLength=config["newsMinMeanLineLength"], minTextLength=config["newsMinTextLength"], logger=logger):
						if "boilerpipe" in newsData["scrap"]:
							raise Exception("Old scrap")
						if newsData["lastUrlDomain"] not in newsUrls:
							newsUrls[newsData["lastUrlDomain"]] = []
						newsUrls[newsData["lastUrlDomain"]].append(url)
						newsCount += 1
		alreadySawUrls.add(url)
	i += 1
logger.p("We got " + str(newsCount) + " news urls.\n")

# We count urls per domain:
newsUrlsCount = dict()
for domain, urls in newsUrls.items():
	newsUrlsCount[domain] = len(urls)
newsUrlsCount = sortByValue(newsUrlsCount, desc=True)
newNewsUrlsCount = []
for current in newsUrlsCount:
	newNewsUrlsCount.append(current[0])
topNewsSource = newNewsUrlsCount

# We store all news per domain:
urlMapping = dict()
pbar = ProgressBar(len(topNewsSource), printRatio=0.00001, message="Storing news ", logger=logger)
for lastUrlDomain in topNewsSource:
	urlsForThisDomain = newsUrls[lastUrlDomain]
	urlsForThisDomainSubsets = splitMaxSized(urlsForThisDomain, config["maxNewsInRam"])
	currentPartIndex = 1
	newsCountForThisDomain = 0
	for urlsForThisDomain in urlsForThisDomainSubsets:
		log("Doing " + lastUrlDomain + " part " + str(currentPartIndex) + " with " + str(len(urlsForThisDomain)) + " urls", logger)
		
		# First we get all news:
		newsForThisDomain = []
		projection = None
		if config["removeHtml"]:
			projection = {"html": False}
		for url in urlsForThisDomain:
			# newsForThisDomain.append(newsCrawl[url])
			newsForThisDomain.append(newsCrawl.findOne({"url": url}, projection=projection))

		# We rescrap all:
		newsScraper = NewsScraper()
		if config["rescrap"]:
			for currentNewsData in newsForThisDomain:
				currentNewsData["scrap"] = newsScraper.smartScrap(currentNewsData["html"])

		log("We got all data for " + lastUrlDomain, logger)

		# We handle duplicates:
		newNewsForThisDomain, urlMappingForThisDomain = reduceDuplicates\
		(
			newsForThisDomain,
			logger=logger,
			verbose=True,
			similarityThreshold=config["overlapSimilarityThreshold"],
			ngramsMin=config["overlapNgramsMin"],
			batchMaxSize=config["overlapBatchMaxSize"],
			doOverlap=config["doOverlap"],
		)
		newsCountForThisDomain += len(newNewsForThisDomain)

		log("reduceDuplicates DONE for " + lastUrlDomain, logger)

		urlMapping = mergeDicts(urlMapping, urlMappingForThisDomain)

		log("urlMapping merging DONE for " + lastUrlDomain, logger)

		# We store all news in multiple json object files per domain:
		newsDir = dataDir + "/news"
		mkdir(newsDir)
		ndj = NDJson(lastUrlDomain + "-part" + str(currentPartIndex), newsDir, compresslevel=compresslevel, indent=indent, closeAtEachAppend=False)
		for newsData in newsForThisDomain:
			for field in config["newsCrawlFieldExcludes"]:
				if field in newsData:
					del newsData[field]
			ndj.append(newsData)
		ndj.close()
		currentPartIndex += 1
	pbar.tic(str(newsCountForThisDomain) + " news stored for " + lastUrlDomain)

newsCount = len(set(urlMapping.values()))
logger.p("We kept only " + str(newsCount) + " news urls.\n")
statistics["newsCount"] = newsCount

# We store all users:
splitedTop = splitMaxSized(top, config["maxUsersPerFile"])
pbar = ProgressBar(len(top), printRatio=0.01, message="Storing users ", logger=logger)
usersDir = dataDir + "/users"
mkdir(usersDir)
i = 0
for currentTop in splitedTop:
	ndj = NDJson("part" + str(i), usersDir, compresslevel=compresslevel, indent=indent)
	for userId in currentTop:
		# We get dat of the current user:
		u = TwitterUser(userId)
		data = u.getData()
		# We get scores and add it:
		scores = u.getScores()
		data["notBotScore"] = scores["notBotScore"]
		data["datasetRelevanceScore"] = scores["datasetRelevanceScore"]
		# We get crawled news:
		userNews = []
		for url in u.getShares():
			if url in urlMapping:
				url =  urlMapping[url]
				if url not in userNews:
					userNews.append(url)
		data["news"] = userNews
		# We remove fileds:
		for key in list(data.keys()):
			if key in config["userCrawlFieldExcludes"]:
				del data[key]
		# We remove shares and replace it by news (last urls):
		for tweet in data["tweets"]:
			if dictContains(tweet, "shares"):
				newsUrls = []
				for share in tweet["shares"]:
					share = share["url"]
					if share in urlMapping:
						newsUrls.append(urlMapping[share])
				tweet["news"] = newsUrls
				del tweet["shares"]
			for key in config["userTweetFieldExcludes"]:
				if dictContains(tweet, key):
					del tweet[key]
		# We store it:
		ndj.append(data)
		# We tic the progres bar:
		pbar.tic("User " + userId)
	i += 1
logger.p("We wrote all users.\n")

# We write statistics:
statistics["version"] = version
if config["generateStatistics"]:
	with open(dataDir + "/infos.json", 'w') as f:
		json.dump(statistics, f, indent=4, sort_keys=True)
	logger.p("We wrote statistics.\n")
tt.toc()




"""

###### EXECUTION NORMAL


Generating overlaps...
batchCount: 1
batchSize: 3
len(self.documents): 3
--> tictoc starts... | message: map: start
--> tictoc starts... | message: getOverlapsFromPairs: start
--> tictoc starts... | message: getOverlapsFromPairs: start
--> tic: 0s | message: getOverlapsFromPairs: step2
--> tic: 0s | message: getOverlapsFromPairs: step2
--> toc total duration: 0s | message: getOverlapsFromPairs: end
--> toc total duration: 0s | message: getOverlapsFromPairs: end
--> tictoc starts... | message: getOverlapsFromPairs: start
--> tic: 0s | message: getOverlapsFromPairs: step2
--> toc total duration: 0s | message: getOverlapsFromPairs: end
--> tictoc starts... | message: getOverlapsFromPairs: start
--> tic: 0s | message: getOverlapsFromPairs: step2
--> toc total duration: 0s | message: getOverlapsFromPairs: end
--> tictoc starts... | message: getOverlapsFromPairs: start
--> tic: 0s | message: getOverlapsFromPairs: step2
--> toc total duration: 0s | message: getOverlapsFromPairs: end
--> tictoc starts... | message: getOverlapsFromPairs: start
--> tic: 0s | message: getOverlapsFromPairs: step2
--> toc total duration: 0s | message: getOverlapsFromPairs: end
--> tictoc starts... | message: getOverlapsFromPairs: start
--> tic: 0s | message: getOverlapsFromPairs: step2
--> toc total duration: 0s | message: getOverlapsFromPairs: end
--> tictoc starts... | message: getOverlapsFromPairs: start
--> tic: 0s | message: getOverlapsFromPairs: step2
--> toc total duration: 0s | message: getOverlapsFromPairs: end
--> tic: 0s | message: map: start done, doing close
--> tic: 0s | message: map: close done, doing join
--> tic: 0.1s | message: map: join done, doing list(result)
--> toc total duration: 0.1s | message: map: end
--> tic: 0.15s | message: generateOverlaps: step3
--> tic: 0s | message: generateOverlaps: step4
--> tic: 0.15s | message: Overlaps generated.
--> toc total duration: 0.15s | message: generateOverlaps: end
--> tic: 0.15s | message: getOverlapScores: step2
--> tic: 0s | message: getOverlapScores: step3
--> toc total duration: 0.15s | message: getOverlapScores: end
--> tic: 0.15s | message: getMeanOverlapScores: We filter
--> toc total duration: 0.15s | message: getMeanOverlapScores: end
--> toc total duration: 0.15s | message: findDuplicates: end
--> tic: 0.15s | message: reduceDuplicates: o.findDuplicates done
--> tic: 0s | message: reduceDuplicates: mergeDuplicates done
--> tic: 0s | message: reduceDuplicates: step2 done
--> toc total duration: 0.88s | message: reduceDuplicates: end
reduceDuplicates DONE for thehill.com
urlMapping merging DONE for thehill.com
Storing news   38% [=======             ] 3 news stored for thehill.com (2m 9.343s left)
Doing independent.co.uk part 1 with 3 urls
We got all data for independent.co.uk
--> tictoc starts... | message: reduceDuplicates: findDuplicates start
--> tic: 0s | message: reduceDuplicates: findDuplicates done
Preprocessing for Overlap...
--> tictoc starts... | message: map: start
--> tic: 0s | message: map: start done, doing close
--> tic: 0s | message: map: close done, doing join
--> tic: 0.1s | message: map: join done, doing list(result)
--> toc total duration: 0.1s | message: map: end
--> tictoc starts... | message: map: start
--> tic: 0s | message: map: start done, doing close
--> tic: 0s | message: map: close done, doing join
--> tic: 0.1s | message: map: join done, doing list(result)
--> toc total duration: 0.1s | message: map: end
--> tictoc starts... | message: map: start
--> tic: 0.04s | message: map: start done, doing close
--> tic: 0s | message: map: close done, doing join
--> tic: 0.06s | message: map: join done, doing list(result)
--> toc total duration: 0.1s | message: map: end
--> tictoc starts... | message: map: start
--> tic: 0.01s | message: map: start done, doing close
--> tic: 0s | message: map: close done, doing join
--> tic: 0.09s | message: map: join done, doing list(result)
--> toc total duration: 0.1s | message: map: end
--> tictoc starts... | message: map: start
--> tic: 0s | message: map: start done, doing close
--> tic: 0s | message: map: close done, doing join
--> tic: 0.1s | message: map: join done, doing list(result)
--> toc total duration: 0.1s | message: map: end
--> tic: 0.72s | message: Preprocessing done.
Generating the inverted index...
--> tic: 0s | message: Inverted index generated.
--> tic: 0.72s | message: reduceDuplicates: o.findDuplicates start
--> tictoc starts... | message: findDuplicates: start
--> tictoc starts... | message: getMeanOverlapScores: start
--> tictoc starts... | message: getOverlapScores: start
--> tictoc starts... | message: generateOverlaps: start
--> tic: 0s | message: generateOverlaps: step2
Generating overlaps...
batchCount: 1
batchSize: 3
len(self.documents): 3
--> tictoc starts... | message: map: start
--> tictoc starts... | message: getOverlapsFromPairs: start
--> tic: 0s | message: getOverlapsFromPairs: step2
--> toc total duration: 0s | message: getOverlapsFromPairs: end
--> tictoc starts... | message: getOverlapsFromPairs: start
--> tic: 0s | message: getOverlapsFromPairs: step2
--> toc total duration: 0s | message: getOverlapsFromPairs: end
--> tictoc starts... | message: getOverlapsFromPairs: start
--> tic: 0s | message: getOverlapsFromPairs: step2
--> toc total duration: 0s | message: getOverlapsFromPairs: end
--> tictoc starts... | message: getOverlapsFromPairs: start
--> tic: 0s | message: getOverlapsFromPairs: step2
--> toc total duration: 0s | message: getOverlapsFromPairs: end
--> tictoc starts... | message: getOverlapsFromPairs: start
--> tic: 0s | message: getOverlapsFromPairs: step2
--> toc total duration: 0s | message: getOverlapsFromPairs: end
--> tictoc starts... | message: getOverlapsFromPairs: start
--> tic: 0s | message: getOverlapsFromPairs: step2
--> toc total duration: 0s | message: getOverlapsFromPairs: end
--> tictoc starts... | message: getOverlapsFromPairs: start
--> tic: 0s | message: getOverlapsFromPairs: step2
--> toc total duration: 0s | message: getOverlapsFromPairs: end
--> tictoc starts... | message: getOverlapsFromPairs: start
--> tic: 0s | message: getOverlapsFromPairs: step2
--> toc total duration: 0s | message: getOverlapsFromPairs: end
--> tic: 0.02s | message: map: start done, doing close
--> tic: 0s | message: map: close done, doing join
--> tic: 0.08s | message: map: join done, doing list(result)
--> toc total duration: 0.1s | message: map: end
--> tic: 0.14s | message: generateOverlaps: step3
--> tic: 0s | message: generateOverlaps: step4
--> tic: 0.14s | message: Overlaps generated.
--> toc total duration: 0.14s | message: generateOverlaps: end
--> tic: 0.14s | message: getOverlapScores: step2
--> tic: 0s | message: getOverlapScores: step3
--> toc total duration: 0.14s | message: getOverlapScores: end
--> tic: 0.14s | message: getMeanOverlapScores: We filter
--> toc total duration: 0.14s | message: getMeanOverlapScores: end
--> toc total duration: 0.14s | message: findDuplicates: end
--> tic: 0.14s | message: reduceDuplicates: o.findDuplicates done
--> tic: 0s | message: reduceDuplicates: mergeDuplicates done
--> tic: 0s | message: reduceDuplicates: step2 done
--> toc total duration: 0.87s | message: reduceDuplicates: end
reduceDuplicates DONE for independent.co.uk
urlMapping merging DONE for independent.co.uk
Storing news   38% [=======             ] 3 news stored for independent.co.uk (2m 6.802s left)
Doing time.com part 1 with 3 urls
We got all data for time.com
--> tictoc starts... | message: reduceDuplicates: findDuplicates start
--> tic: 0s | message: reduceDuplicates: findDuplicates done
Preprocessing for Overlap...
--> tictoc starts... | message: map: start
--> tic: 0s | message: map: start done, doing close
--> tic: 0s | message: map: close done, doing join
--> tic: 0.1s | message: map: join done, doing list(result)
--> toc total duration: 0.1s | message: map: end
--> tictoc starts... | message: map: start
--> tic: 0s | message: map: start done, doing close
--> tic: 0s | message: map: close done, doing join
--> tic: 0.11s | message: map: join done, doing list(result)
--> toc total duration: 0.11s | message: map: end
--> tictoc starts... | message: map: start
--> tic: 0.04s | message: map: start done, doing close
--> tic: 0s | message: map: close done, doing join
--> tic: 0.06s | message: map: join done, doing list(result)
--> toc total duration: 0.11s | message: map: end
--> tictoc starts... | message: map: start
--> tic: 0s | message: map: start done, doing close
--> tic: 0s | message: map: close done, doing join
--> tic: 0.1s | message: map: join done, doing list(result)
--> toc total duration: 0.11s | message: map: end
--> tictoc starts... | message: map: start
--> tic: 0s | message: map: start done, doing close
--> tic: 0s | message: map: close done, doing join
--> tic: 0.1s | message: map: join done, doing list(result)
--> toc total duration: 0.11s | message: map: end
--> tic: 0.75s | message: Preprocessing done.
Generating the inverted index...
--> tic: 0s | message: Inverted index generated.
--> tic: 0.75s | message: reduceDuplicates: o.findDuplicates start
--> tictoc starts... | message: findDuplicates: start
--> tictoc starts... | message: getMeanOverlapScores: start
--> tictoc starts... | message: getOverlapScores: start
--> tictoc starts... | message: generateOverlaps: start
--> tic: 0s | message: generateOverlaps: step2
Generating overlaps...
batchCount: 1
batchSize: 3
len(self.documents): 3
--> tictoc starts... | message: map: start
--> tictoc starts... | message: getOverlapsFromPairs: start
--> tic: 0s | message: getOverlapsFromPairs: step2
--> toc total duration: 0s | message: getOverlapsFromPairs: end
--> tictoc starts... | message: getOverlapsFromPairs: start
--> tic: 0s | message: getOverlapsFromPairs: step2
--> toc total duration: 0s | message: getOverlapsFromPairs: end
--> tictoc starts... | message: getOverlapsFromPairs: start
--> tic: 0s | message: getOverlapsFromPairs: step2
--> toc total duration: 0s | message: getOverlapsFromPairs: end
--> tictoc starts... | message: getOverlapsFromPairs: start
--> tic: 0s | message: getOverlapsFromPairs: step2
--> toc total duration: 0s | message: getOverlapsFromPairs: end
--> tictoc starts... | message: getOverlapsFromPairs: start
--> tic: 0s | message: getOverlapsFromPairs: step2
--> toc total duration: 0s | message: getOverlapsFromPairs: end
--> tictoc starts... | message: getOverlapsFromPairs: start
--> tic: 0s | message: getOverlapsFromPairs: step2
--> toc total duration: 0s | message: getOverlapsFromPairs: end
--> tictoc starts... | message: getOverlapsFromPairs: start
--> tic: 0s | message: getOverlapsFromPairs: step2
--> toc total duration: 0s | message: getOverlapsFromPairs: end
--> tictoc starts... | message: getOverlapsFromPairs: start
--> tic: 0s | message: getOverlapsFromPairs: step2
--> toc total duration: 0s | message: getOverlapsFromPairs: end
--> tic: 0.02s | message: map: start done, doing close
--> tic: 0s | message: map: close done, doing join
--> tic: 0.08s | message: map: join done, doing list(result)
--> toc total duration: 0.1s | message: map: end
--> tic: 0.15s | message: generateOverlaps: step3
--> tic: 0s | message: generateOverlaps: step4
--> tic: 0.15s | message: Overlaps generated.
--> toc total duration: 0.15s | message: generateOverlaps: end
--> tic: 0.15s | message: getOverlapScores: step2
--> tic: 0s | message: getOverlapScores: step3
--> toc total duration: 0.15s | message: getOverlapScores: end
--> tic: 0.15s | message: getMeanOverlapScores: We filter
--> toc total duration: 0.15s | message: getMeanOverlapScores: end
--> toc total duration: 0.15s | message: findDuplicates: end
--> tic: 0.15s | message: reduceDuplicates: o.findDuplicates done
--> tic: 0s | message: reduceDuplicates: mergeDuplicates done
--> tic: 0s | message: reduceDuplicates: step2 done
--> toc total duration: 0.91s | message: reduceDuplicates: end
reduceDuplicates DONE for time.com
urlMapping merging DONE for time.com
Storing news   39% [=======             ] 3 news stored for time.com (2m 4.381s left)
Doing ktnv.com part 1 with 3 urls
We got all data for ktnv.com
--> tictoc starts... | message: reduceDuplicates: findDuplicates start
--> tic: 0s | message: reduceDuplicates: findDuplicates done
Preprocessing for Overlap...
--> tictoc starts... | message: map: start
--> tic: 0s | message: map: start done, doing close
--> tic: 0s | message: map: close done, doing join
--> tic: 0.1s | message: map: join done, doing list(result)
--> toc total duration: 0.1s | message: map: end
--> tictoc starts... | message: map: start
--> tic: 0s | message: map: start done, doing close
--> tic: 0s | message: map: close done, doing join
--> tic: 0.1s | message: map: join done, doing list(result)
--> toc total duration: 0.11s | message: map: end
--> tictoc starts... | message: map: start
--> tic: 0.04s | message: map: start done, doing close
--> tic: 0s | message: map: close done, doing join
--> tic: 0.06s | message: map: join done, doing list(result)
--> toc total duration: 0.1s | message: map: end
--> tictoc starts... | message: map: start
--> tic: 0s | message: map: start done, doing close
--> tic: 0s | message: map: close done, doing join
--> tic: 0.1s | message: map: join done, doing list(result)
--> toc total duration: 0.1s | message: map: end
--> tictoc starts... | message: map: start
--> tic: 0s | message: map: start done, doing close
--> tic: 0s | message: map: close done, doing join
--> tic: 0.1s | message: map: join done, doing list(result)
--> toc total duration: 0.1s | message: map: end
--> tic: 0.72s | message: Preprocessing done.
Generating the inverted index...
--> tic: 0s | message: Inverted index generated.
--> tic: 0.72s | message: reduceDuplicates: o.findDuplicates start
--> tictoc starts... | message: findDuplicates: start
--> tictoc starts... | message: getMeanOverlapScores: start
--> tictoc starts... | message: getOverlapScores: start
--> tictoc starts... | message: generateOverlaps: start
--> tic: 0s | message: generateOverlaps: step2
Generating overlaps...
batchCount: 1
batchSize: 3
len(self.documents): 3
--> tictoc starts... | message: map: start
--> tictoc starts... | message: getOverlapsFromPairs: start
--> tictoc starts... | message: getOverlapsFromPairs: start
--> tic: 0s | message: getOverlapsFromPairs: step2
--> toc total duration: 0s | message: getOverlapsFromPairs: end
--> tictoc starts... | message: getOverlapsFromPairs: start
--> tictoc starts... | message: getOverlapsFromPairs: start
--> tic: 0s | message: getOverlapsFromPairs: step2
--> toc total duration: 0s | message: getOverlapsFromPairs: end
--> tic: 0s | message: getOverlapsFromPairs: step2
--> toc total duration: 0s | message: getOverlapsFromPairs: end
--> tictoc starts... | message: getOverlapsFromPairs: start
--> tic: 0s | message: getOverlapsFromPairs: step2
--> toc total duration: 0s | message: getOverlapsFromPairs: end
--> tictoc starts... | message: getOverlapsFromPairs: start
--> tic: 0s | message: getOverlapsFromPairs: step2
--> toc total duration: 0s | message: getOverlapsFromPairs: end
--> tictoc starts... | message: getOverlapsFromPairs: start
--> tic: 0s | message: getOverlapsFromPairs: step2
--> toc total duration: 0s | message: getOverlapsFromPairs: end
--> tic: 0s | message: getOverlapsFromPairs: step2
--> toc total duration: 0s | message: getOverlapsFromPairs: end
--> tictoc starts... | message: getOverlapsFromPairs: start
--> tic: 0s | message: getOverlapsFromPairs: step2
--> toc total duration: 0s | message: getOverlapsFromPairs: end
--> tic: 0s | message: map: start done, doing close
--> tic: 0s | message: map: close done, doing join
--> tic: 0.1s | message: map: join done, doing list(result)
--> toc total duration: 0.11s | message: map: end
--> tic: 0.14s | message: generateOverlaps: step3
--> tic: 0s | message: generateOverlaps: step4
--> tic: 0.14s | message: Overlaps generated.
--> toc total duration: 0.14s | message: generateOverlaps: end
--> tic: 0.14s | message: getOverlapScores: step2
--> tic: 0s | message: getOverlapScores: step3
--> toc total duration: 0.14s | message: getOverlapScores: end
--> tic: 0.14s | message: getMeanOverlapScores: We filter
--> toc total duration: 0.14s | message: getMeanOverlapScores: end
--> toc total duration: 0.14s | message: findDuplicates: end
--> tic: 0.14s | message: reduceDuplicates: o.findDuplicates done
--> tic: 0s | message: reduceDuplicates: mergeDuplicates done
--> tic: 0s | message: reduceDuplicates: step2 done
--> toc total duration: 0.87s | message: reduceDuplicates: end
reduceDuplicates DONE for ktnv.com
urlMapping merging DONE for ktnv.com
Storing news   40% [========            ] 3 news stored for ktnv.com (2m 1.956s left)
Doing pbs.org part 1 with 3 urls
We got all data for pbs.org
--> tictoc starts... | message: reduceDuplicates: findDuplicates start
--> tic: 0s | message: reduceDuplicates: findDuplicates done
Preprocessing for Overlap...
--> tictoc starts... | message: map: start
--> tic: 0s | message: map: start done, doing close
--> tic: 0s | message: map: close done, doing join
--> tic: 0.1s | message: map: join done, doing list(result)
--> toc total duration: 0.11s | message: map: end
--> tictoc starts... | message: map: start
--> tic: 0s | message: map: start done, doing close
--> tic: 0s | message: map: close done, doing join
--> tic: 0.1s | message: map: join done, doing list(result)
--> toc total duration: 0.11s | message: map: end
--> tictoc starts... | message: map: start
--> tic: 0.03s | message: map: start done, doing close
--> tic: 0s | message: map: close done, doing join
--> tic: 0.07s | message: map: join done, doing list(result)
--> toc total duration: 0.1s | message: map: end
--> tictoc starts... | message: map: start
--> tic: 0s | message: map: start done, doing close
--> tic: 0s | message: map: close done, doing join
--> tic: 0.1s | message: map: join done, doing list(result)
--> toc total duration: 0.11s | message: map: end
--> tictoc starts... | message: map: start
--> tic: 0s | message: map: start done, doing close
--> tic: 0s | message: map: close done, doing join
--> tic: 0.1s | message: map: join done, doing list(result)
--> toc total duration: 0.11s | message: map: end
--> tic: 0.77s | message: Preprocessing done.
Generating the inverted index...
--> tic: 0s | message: Inverted index generated.
--> tic: 0.77s | message: reduceDuplicates: o.findDuplicates start
--> tictoc starts... | message: findDuplicates: start
--> tictoc starts... | message: getMeanOverlapScores: start
--> tictoc starts... | message: getOverlapScores: start
--> tictoc starts... | message: generateOverlaps: start
--> tic: 0s | message: generateOverlaps: step2
Generating overlaps...
batchCount: 1
batchSize: 3
len(self.documents): 3
--> tictoc starts... | message: map: start
--> tictoc starts... | message: getOverlapsFromPairs: start
--> tic: 0s | message: getOverlapsFromPairs: step2
--> toc total duration: 0s | message: getOverlapsFromPairs: end
--> tictoc starts... | message: getOverlapsFromPairs: start
--> tic: 0s | message: getOverlapsFromPairs: step2
--> toc total duration: 0s | message: getOverlapsFromPairs: end
--> tictoc starts... | message: getOverlapsFromPairs: start
--> tictoc starts... | message: getOverlapsFromPairs: start
--> tic: 0s | message: getOverlapsFromPairs: step2
--> toc total duration: 0s | message: getOverlapsFromPairs: end
--> tictoc starts... | message: getOverlapsFromPairs: start
--> tic: 0s | message: getOverlapsFromPairs: step2
--> toc total duration: 0s | message: getOverlapsFromPairs: end
--> tictoc starts... | message: getOverlapsFromPairs: start
--> tic: 0s | message: getOverlapsFromPairs: step2
--> toc total duration: 0s | message: getOverlapsFromPairs: end
--> tictoc starts... | message: getOverlapsFromPairs: start
--> tic: 0s | message: getOverlapsFromPairs: step2
--> toc total duration: 0s | message: getOverlapsFromPairs: end
--> tic: 0s | message: getOverlapsFromPairs: step2
--> toc total duration: 0s | message: getOverlapsFromPairs: end
--> tictoc starts... | message: getOverlapsFromPairs: start
--> tic: 0s | message: getOverlapsFromPairs: step2
--> toc total duration: 0s | message: getOverlapsFromPairs: end
--> tic: 0.01s | message: map: start done, doing close
--> tic: 0s | message: map: close done, doing join
--> tic: 0.09s | message: map: join done, doing list(result)
--> toc total duration: 0.1s | message: map: end
--> tic: 0.14s | message: generateOverlaps: step3
--> tic: 0s | message: generateOverlaps: step4
--> tic: 0.14s | message: Overlaps generated.
--> toc total duration: 0.14s | message: generateOverlaps: end
--> tic: 0.14s | message: getOverlapScores: step2
--> tic: 0s | message: getOverlapScores: step3
--> toc total duration: 0.14s | message: getOverlapScores: end
--> tic: 0.14s | message: getMeanOverlapScores: We filter
--> toc total duration: 0.14s | message: getMeanOverlapScores: end
--> toc total duration: 0.14s | message: findDuplicates: end
--> tic: 0.14s | message: reduceDuplicates: o.findDuplicates done
--> tic: 0s | message: reduceDuplicates: mergeDuplicates done
--> tic: 0s | message: reduceDuplicates: step2 done
--> toc total duration: 0.93s | message: reduceDuplicates: end
reduceDuplicates DONE for pbs.org
urlMapping merging DONE for pbs.org
Storing news   41% [========            ] 3 news stored for pbs.org (1m 59.657s left)
Doing adweek.com part 1 with 3 urls
We got all data for adweek.com
--> tictoc starts... | message: reduceDuplicates: findDuplicates start

"""