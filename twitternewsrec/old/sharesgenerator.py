# coding: utf-8

# nn pew in newscrawler-venv python ~/wm-dist-tmp/NewsCrawler/newscrawler/sharesgenerator.py ; observe nohup.out

import sys, os; sys.path.append("/".join(os.path.abspath(__file__).split("/")[0:-2]))

from systemtools.basics import *
from datatools.jsonreader import *
from datatools.url import *
from datatools.csvreader import *
from systemtools.file import *
from systemtools.location import *
from systemtools.system import *
from systemtools.logger import *
from datatools.url import *
from newstools.newsurlfilter import *
from unshortener.unshortener import *
from nlptools.basics import *
from nlptools.tokenizer import *
import random
import copy
try:
    from systemtools.hayj import *
except: pass
import datetime


class UserSharesGenerator():
    def __init__(self, user, logger=None, verbose=True, removeDuplicates=False):
        """
            user can be userData or userId or a TwitterUser instance
        """
        self.removeDuplicates = removeDuplicates
        if isinstance(user, str):
            self.userData = TwitterUser(user).getUserData()
        elif isinstance(user, dict):
            self.userData = user
        else:
            self.userData = user.getUserData()
        self.urlParser = URLParser()
        if self.userData is not None and dictContains(self.userData, "scrap"):
            self.userData = self.userData["scrap"]

    def __iter__(self):
        shares = []
        if dictContains(self.userData, "tweets"):
            for tweet in self.userData["tweets"]:
                for share in tweet["shares"]:
                    url = share["url"]
                    url = self.urlParser.normalize(url)
                    shares.append(url)
        if len(shares) > 0:
            if self.removeDuplicates:
                shares = set(shares)
            for share in shares:
                yield share

class ScoreSharesGenerator():
    """
        This generator will find all shares across all already existing scores
        (previously calculated in SerializableDicts of TwitterUserScores)
        It can handle differents version.
        Warning : this generator can throw duplicates (because we can have same user
        scores across all SDs version and differents user can have same shares...
    """
    def __init__(self, logger=None, verbose=True,
                 notBotThreshold=0.95,
                 relevanceThreshold=0.85,
                 tuScoresPriorityVersion=["0.0.10"], # "0.0.3", "0.0.2"
                 unshortenerReadOnly=True):
        self.logger = logger
        self.verbose = verbose
        self.tuScoresPriorityVersion = tuScoresPriorityVersion
        self.relevanceThreshold = relevanceThreshold
        self.notBotThreshold = notBotThreshold
        self.unshortenerReadOnly = unshortenerReadOnly
        self.allTops = None

    def topYielder(self):
        if self.allTops is not None:
            for current in self.allTops:
                yield current
        else:
            self.allTops = []
            for sdVersion in self.tuScoresPriorityVersion:
                log("Initializing score SDs " + sdVersion, self)
                currentTuScores = TwitterUserScores\
                (
                    notBotThreshold=self.notBotThreshold,
                    relevanceThreshold=self.relevanceThreshold,
                    sdVersion=sdVersion,
                    # No need this because we just call top():
                    unshortenerReadOnly=self.unshortenerReadOnly,
                    logger=self.logger,
                    verbose=self.verbose,
                )
                currentTop = currentTuScores.top()
                self.allTops.append(currentTop)
                yield currentTop

    def __iter__(self):
        for top in self.topYielder():
            for row in top:
                userId = row[0]
                yield from UserSharesGenerator(userId, logger=self.logger, verbose=self.verbose)


class NewsSharesGenerator:
    def __init__(self, logger=None, verbose=True, unshortenerReadOnly=True,
                 sharesGeneratorParams={}, user=None):
        """
            user can be userData or userId or a TwitterUser instance
        """
        self.logger = logger
        self.verbose = verbose
        self.sharesGeneratorParams = sharesGeneratorParams
        self.unshortenerReadOnly = unshortenerReadOnly
        self.nuf = NewsURLFilter(logger=self.logger, verbose=self.verbose,
                                 unshortenerReadOnly=self.unshortenerReadOnly)
        if user is None:
            self.shares = ScoreSharesGenerator(logger=self.logger, verbose=self.verbose,
                                          unshortenerReadOnly=self.unshortenerReadOnly,
                                          **self.sharesGeneratorParams)
        else:
            self.shares = UserSharesGenerator(user, logger=self.logger, verbose=self.verbose)

    def __iter__(self):
        for url in self.shares:
            if url is not None:
                if self.nuf.isNews(url):
                    yield url






def testOne():
#     tu = TwitterUser("18746212")
#     tu = TwitterUser("250376045")
    tu = TwitterUser("476755076")
#     printLTS(list(NewsSharesGenerator(user=tu)))
    printLTS(list(UserSharesGenerator(user=tu)))
    print(tu.notBotScore())
    print(tu.relevanceScore())

def getShortenerLovers(logger=None, verbose=True):
    # To retain all, we create tuscSD:
    (user, password, host) = getOctodsMongoAuth()
    tuscSD = SerializableDict("tuscSD_v2", limit=100,
                              user=user, password=password, host=host,
                              logger=logger,
                              useMongodb=True)
    # Now we generate all keys to retain:
    tusc4TwitterUserScoresParams = sortByKey(\
    {
        "shortenedAsNews": False,
        "notBotThreshold": 0.6,
        "relevanceThreshold": 0.6,
        "sdVersion": "0.0.4",
        "unshortenerReadOnly": True,
    })
    tusc3TwitterUserScoresParams = sortByKey(\
    {
        "shortenedAsNews": False,
        "notBotThreshold": 0.6,
        "relevanceThreshold": 0.6,
        "sdVersion": "0.0.10",
        "unshortenerReadOnly": True,
    })
    tusc3Key = str(tusc3TwitterUserScoresParams) # The key for 0.0.3 top
    tusc4Key = str(tusc4TwitterUserScoresParams) # The key for 0.0.4 top
    topSubKey = tusc3Key + tusc4Key + "top4-top3" # The key for top4 - top3
    # Now we add the logger:
    for current in [tusc4TwitterUserScoresParams, tusc3TwitterUserScoresParams]:
        current["logger"] = logger
    # And if we already calculated this top, we get it:
    if topSubKey in tuscSD:
        shortenerLovers = tuscSD[topSubKey]
    else:
        # Else we calculate all:
        if tusc4Key in tuscSD:
            top4 = tuscSD[tusc4Key]
        else:
            tusc4 = TwitterUserScores(**tusc4TwitterUserScoresParams)
            top4 = tusc4.top()
            tuscSD[tusc4Key] = top4
        if tusc3Key in tuscSD:
            top3 = tuscSD[tusc3Key]
        else:
            tusc3 = TwitterUserScores(**tusc3TwitterUserScoresParams)
            top3 = tusc3.top()
            tuscSD[tusc3Key] = top3
        # We have to take users who are in tusc 0.0.4 but not in 0.0.10 so we know
        # they have a lot of shortened urls
        shortenerLovers = []
        for currentTop4 in top4:
            found = False
            for currentTop3 in top3:
                if currentTop4[0] == currentTop3[0]:
                    found = True
                    break
            if not found:
                shortenerLovers.append(currentTop4)
    # We print all:
    log("Top4 - top3:\n" + listToStr(shortenerLovers[0:20]) + "\n...\n" + listToStr(shortenerLovers[-20:]), logger, verbose=verbose)
    log("Total for top4 - top3: " + str(len(shortenerLovers)), logger, verbose=verbose)
    # And we retrun the result:
    return shortenerLovers

def generateScores():
    """"
        Execute several instances in octods server
    """
    if TEST:
        logger = None
    else:
        logger = Logger("sharesgen-generatescores-" + getRandomStr() + ".log")
    log("STARTING", logger)
    (user, password, host) = getStudentMongoAuth()
    collection = MongoCollection("twitter", "usercrawl", user=user, password=password, host=host)
    i = 0
    while True:
        try:
#             toSkip = 200
#             if isHostname("datas"):
#                 toSkip = int(collection.size() / 1)
            toSkip = 0
            log("Starting collection.find", logger)
            for current in collection.find(projection={"user_id": 1}).skip(getRandomInt(toSkip)):
                if TEST:
                    log("Trying one...", logger)
#                 if getRandomFloat() > 0.9:
                setCallTimeout(300)
                tu = TwitterUser(current["user_id"])
                tuNotBotScore = tu.notBotScore()
                tuRelevanceScore = tu.relevanceScore()
                resetCallTimeout()
                log("userId=" + str(tu.getUserId()), logger)
                log("tuNotBotScore=" + str(tuNotBotScore), logger)
                log("tuRelevanceScore=" + str(tuRelevanceScore), logger)
                log("\n\n", logger)
                if TEST:
                    input()
#                     i += 1
#                     if i > 100000:
#                         break
        except Exception as e:
            logException(e, logger, location="generateScores")
        log("C'est reparti pour un tour...", logger)
        time.sleep(20)
    resetCallTimeout()

def generateScoresSimple():
    """"
        Execute several instances in octods server
    """
    if TEST:
        logger = None
    else:
        logger = Logger("sharesgen-generatescoressimple-" + getRandomStr() + ".log")
    log("STARTING", logger)
    (user, password, host) = getStudentMongoAuth()
    while True:
        log("New loop.....", logger)
        collection = MongoCollection("twitter", "usercrawl", user=user, password=password, host=host)
#         userIdList = []
#         count = 0
        # ajouter projection={"user_id": 1} block à la fin du premier batch de 101 elements, bizarrre...
        for current in collection.find().sort([("timestamp", -1)]).skip(getRandomInt(10000)): # .skip(getRandomInt(10000))
            if getRandomFloat() > 0.8:
                userId = current["user_id"]
                try:
                    log("Trying " + str(userId) + "...", logger)
                    tu = TwitterUser(userId)
                    tuNotBotScore = tu.notBotScore()
                    tuRelevanceScore = tu.relevanceScore()
                    log("userId=" + str(tu.getUserId()), logger)
                    log("tuNotBotScore=" + str(tuNotBotScore), logger)
                    log("tuRelevanceScore=" + str(tuRelevanceScore), logger)
                    log("\n\n", logger)
                except Exception as e:
                    logException(e, logger, location="generateScores")
#                 userIdList.append()
#                 count += 1
#                 if count % 500 == 0:
#                     log(count, logger)
#                     log("adding " + str(current["user_id"]) + " and others...", logger)
#         log("userIdList=" + str(userIdList), logger)
#         for userId in userIdList:


def topTest():
    tuScoreSingleton = getTwitterUserScoresSingleton()
    printLTS(tuScoreSingleton.top()[0:100])

def generatorTest():
    for url in NewsSharesGenerator():
        print(url)
        time.sleep(0.1)


if __name__ == '__main__':
    # WARNING: set unshortenerReadOnly as False
#     generateScoresSimple()

#     if TEST:
#         logger = None
#     else:
#         logger = Logger("shortners-lovers.log")
#     getShortenerLovers(logger=logger)
    testOne()













###########################################################
###########################################################
###########################################################
###########################################################
######################## OLD TESTS ########################
###########################################################
###########################################################
###########################################################
###########################################################


def unshortenedCount():
    """
        This funct print the ratio of already unshortened urls
    """
    def printAll():
        logger.info("current user: " + str(i))
        logger.info("unshortenedUrlsCount=" + str(unshortenedUrlsCount))
        logger.info("totalShortenedUrls=" + str(totalShortenedUrls))
        logger.info("ratio of already unshortened urls: " + str(unshortenedUrlsCount / totalShortenedUrls))
        logger.info("alreadyShortenedDict:\n" + listToStr(sortBy(alreadyShortenedDict, desc=True)))
        logger.info("notAlreadyShortenedDict:\n" + listToStr(sortBy(notAlreadyShortenedDict, desc=True)))
        logger.info("\n" * 10)
    logger = Logger("count-already-unshortened.log")
    logger.info("STARTING")
    unshortenedUrlsCount = 0
    totalShortenedUrls = 0
    (user, password, host) = getStudentMongoAuth()
    collection = MongoCollection("twitter", "usercrawl", user=user, password=password, host=host)
    alreadyShortenedDict = dict()
    notAlreadyShortenedDict = dict()
    urlParser = URLParser()
    uns = Unshortener()
    i = 0
    for current in collection.find():
        tu = TwitterUser(current)
        try:
            for tweet in tu.userData["tweets"]:
                for share in tweet["shares"]:
                    url = share["url"]
                    if uns.isShortener(url):
                        domain = urlParser.getDomain(url)
                        totalShortenedUrls += 1
                        if uns.isAlreadyUnshortened(url):
                            if domain not in alreadyShortenedDict:
                                alreadyShortenedDict[domain] = 0
                            alreadyShortenedDict[domain] += 1
                            unshortenedUrlsCount += 1
                        else:
                            if domain not in notAlreadyShortenedDict:
                                notAlreadyShortenedDict[domain] = 0
                            notAlreadyShortenedDict[domain] += 1
        except Exception as e:
            logException(e, logger=logger)
        theModulo = 100
        if isHostname("hjlat"):
            theModulo = 50
        if i % theModulo == 0:
            printAll()
            if isHostname("hjlat"):
                input()
        i += 1
    logger.info("last print:")
    printAll()
    logger.info("END")

def tinyurlTest():
    # nn -n 0 -o tinycount.out pew in newscrawler-venv python ~/wm-dist-tmp/NewsCrawler/newscrawler/sharesgenerator.py
    logger = Logger("count-tiny.log")
    logger.info("STARTING")
    (user, password, host) = getStudentMongoAuth()
    collection = MongoCollection("twitter", "usercrawl", user=user, password=password, host=host)
    tinyUserCount = 0
    tinyCount = 0
    text = "tinyurl.com"
    userCount = 0
    for current in collection.find():
        userCount += 1
        userData = current["scrap"]
        try:
            hasTinyUrls = False
            for tweet in userData["tweets"]:
                for share in tweet["shares"]:
                    share = share["url"]
                    if text in share:
                        tinyCount += 1
                        hasTinyUrls = True
                        print(share)
            if hasTinyUrls:
                tinyUserCount += 1
            if userCount % 1000 == 0:
                logger.info("tinyUserCount=" + str(tinyUserCount))
                logger.info("tinyCount=" + str(tinyCount))
                logger.info("userCount=" + str(userCount))
                logger.info("ratio=" + str(tinyUserCount/userCount))
                logger.info("\n\n")
        except Exception as e:
            logException(e, logger=logger)
    logger.info("END")
