# coding: utf-8

# nn pew in newscrawler-venv python /home/hayj/wm-dist-tmp/NewsCrawler/newscrawler/topuser.py ; observe nohup.out

import sys, os; sys.path.append("/".join(os.path.abspath(__file__).split("/")[0:-2]))

from datastructuretools.hashmap import *
from systemtools.basics import *
from systemtools.logger import *
from twitternewsrec.user import config as tuConf
from systemtools.system import *

TEST = False
if TEST:
	tuConf.twitterUserScoreVersion = "test1"

from twitternewsrec.user.utils import *
from twitternewsrec.newscrawler.utils import *
from twitternewsrec.user.twitteruser import *
import pymongo

def getToBeEstimatedTopUser(*args, unshortenedThreshold=3, **kwargs):
	return getTopUser("optimisticRelevanceScore", *args, filter={"value.unshortenedCount": {"$lt": unshortenedThreshold}}, **kwargs)

def getRelevantTopUser(*args, **kwargs):
	return getTopUser("relevanceScore", *args, **kwargs)

def getDatasetRelevantTopUser(*args, relevanceFieldThreshold=0.6, **kwargs):
	return getTopUser("datasetRelevanceScore", relevanceFieldThreshold=relevanceFieldThreshold, *args, **kwargs)

def getToBeCompletedOnlyNewsTopUser(*args, remainingThreshold=0, **kwargs):
	return getTopUser("relevanceScore", *args, filter={"value.remainingNewsCount": {"$gt": remainingThreshold}}, **kwargs)

def getToBeCompletedTopUser(*args, remainingThreshold=0, **kwargs):
	return getTopUser("estimatedRelevanceScore", *args, filter={"$or": [{"value.remainingNewsCount": {"$gt": remainingThreshold}}, {"value.remainingShortenedCount": {"$gt": remainingThreshold}}]}, **kwargs)

def getTopUser(relevanceField, relevanceFieldThreshold=0.28, notBotThreshold=0.28, filter={}, logger=None, verbose=True):
	# We get all data:
	topUserSD = getTopUserSD(logger=logger, verbose=verbose)
	twitterUserScoreSD = getTwitterUserScoreSD(logger=logger, verbose=verbose)
	# We create all indexes:
	# twitterUserScoreSD.data.dropAllIndexes() ; exit()
	twitterUserScoreSD.data.createCompoundIndex\
	(
		[
			("value." + relevanceField, pymongo.DESCENDING),
			("value.notBotScore", pymongo.DESCENDING),
		],
		unique=False,
	)
	# We construct the final filter:
	filter = mergeDicts\
	(
		{
			"value.notBotScore":
			{
				"$gt": notBotThreshold
			},
			"value." + relevanceField:
			{
				"$gt": relevanceFieldThreshold
			},
		},
		filter,
	)
	# We init the config:
	config = {}
	config["tuConf.twitterUserScoreVersion"] = tuConf.twitterUserScoreVersion
	config["twitterUserScoreSD.size()"] = twitterUserScoreSD.size()
	config["relevanceField"] = relevanceField
	config["filter"] = filter
	config["notBotThreshold"] = notBotThreshold
	config["relevanceFieldThreshold"] = relevanceFieldThreshold
	theHash = objectAsKey(config)
	top = None
	# If we already generate this top, we return it:
	if theHash in topUserSD:
		top = topUserSD[theHash]
	# Else we generate it:
	else:
		log("Requesting the databaseRequesting the database...", logger, verbose=verbose)
		top = []
		for row in twitterUserScoreSD.data.find\
		(
			filter,
			projection=\
			{
				"hash": True,
				"_id": False
			},
			sort=\
			[
				("value." + relevanceField, pymongo.DESCENDING),
				("value.notBotScore", pymongo.DESCENDING),
			]
		):
			top.append(row["hash"])
		topUserSD[theHash] = top
	log("The top for " + theHash + " is:\n" + reducedLTS(top, 15) + "\nwith a len of " + str(len(top)) + ".", logger, verbose=verbose)
	return top

def toEstimateSharesYielder(*args, logger=None, verbose=True, shuffle=False, unshortenedThreshold=3, shuffleUnshortenedUrls=True, **kwargs):
	top = getToBeEstimatedTopUser(*args, unshortenedThreshold=unshortenedThreshold, logger=logger, verbose=verbose, **kwargs)
	if shuffle:
		random.shuffle(top)
	for id in top:
		u = TwitterUser(id, logger=logger, verbose=verbose)
		log("==> Doing user " + id + "... <==", logger, verbose=verbose)
		scores = u.getScores(eraseCache=True, skipNotBotScore=True)
		toUnshortAmount = unshortenedThreshold - scores["unshortenedCount"]
		if toUnshortAmount < 0:
			toUnshortAmount = 0
		iterator = u.getShortened(ignoreAlreadyUnshortened=True)
		unshortenedUrls = []
		for current in iterator:
			unshortenedUrls.append(current)
		if shuffleUnshortenedUrls:
			random.shuffle(unshortenedUrls)
		for i in range(toUnshortAmount):
			if i < len(unshortenedUrls):
				url = unshortenedUrls[i]
				yield url

def toCompleteSharesYielder(*args, logger=None, verbose=True, shuffle=False, **kwargs):
	top = getToBeCompletedTopUser(*args, logger=logger, verbose=verbose, **kwargs)
	if shuffle:
		random.shuffle(top)
	for id in top:
		u = TwitterUser(id, logger=logger, verbose=verbose)
		log("==> Doing user " + id + "... <==", logger, verbose=verbose)
		iterator = u.getNews(ignoreAlreadyCrawled=True)
		for share in iterator:
			yield share
		iterator = u.getShortened(ignoreAlreadyUnshortened=True)
		for share in iterator:
			yield share

def toCompleteOnlyNewsSharesYielder(*args, logger=None, verbose=True, shuffle=False, **kwargs):
	top = getToBeCompletedOnlyNewsTopUser(*args, logger=logger, verbose=verbose, **kwargs)
	if shuffle:
		random.shuffle(top)
	for id in top:
		u = TwitterUser(id, logger=logger, verbose=verbose)
		log("==> Doing user " + id + "... <==", logger, verbose=verbose)
		iterator = u.getNews(ignoreAlreadyCrawled=True)
		for share in iterator:
			yield share




if __name__ == '__main__':
	# log(lts(getTopUser("relevanceScore")), logger)
	# log(lts(getToBeEstimatedTopUser()), logger)

	logger = Logger("topuser-test2.log")
	# getToBeCompletedTopUser(logger=logger)
	# getToBeEstimatedTopUser(logger=logger)
	getDatasetRelevantTopUser(logger=logger)

	# logger = Logger("topuser-test.log")
	# for current in toCompleteSharesYielder(logger=logger):
	# 	log(current, logger)
	
	


