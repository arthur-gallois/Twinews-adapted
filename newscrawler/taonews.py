# coding: utf-8

import sys, os; sys.path.append("/".join(os.path.abspath(__file__).split("/")[0:-3]))


from datatools.url import *
from systemtools.basics import *
from systemtools.duration import *
from systemtools.file import *
from systemtools.logger import log, logInfo, logWarning, logError, Logger
from systemtools.location import *
from systemtools.hayj import *
from systemtools.system import *
import random
import re
from threading import Thread, Lock, Semaphore, active_count
from webcrawler.crawler import *
from hjwebbrowser.utils import *
from hjwebbrowser.browser import *
from newstools.newsscraper import *
from queue import *
from databasetools.mongo import *
from databasetools.mongo import *
from newstools.newsurlfilter import *
from twitterarchiveorg.urlgenerator import *
from webcrawler.sample import __version__


class MongoConnector:
    def __init__(self, dbName="test", collectionName="samehtml2", onlySuccess=False):
        if isHostname("hjlat"):
            (user, password, host) = (None, None, None)
        else:
            (user, password, host) = getMongoAuth(user="hayj", hostname="datascience01")
        self.collection = MongoCollection \
        (
            dbName,
            collectionName,
            user=user,
            password=password,
            host=host,
            indexNotUniqueOn=["last_url_domain", "normalized_url_domain"],
            indexOn=["normalized_url"],
        )
        if collectionName == "samehtml2":
            self.collection.resetCollection(security=False)
        self.urlParser = URLParser()
        self.onlySuccess = onlySuccess

    def printAll(self):
        data = self.collection.toDataFrame()
        print(data)

    def normalizedUrlExists(self, normalizedUrl):
        if self.onlySuccess:
            return self.collection.has({"normalized_url": normalizedUrl, "status": "success"})
        else:
            return self.collection.has({"normalized_url": normalizedUrl})

    def crawlingCallback(self, data, browser=None):

#         data["html"] = data["html"][0:5]
#         printLTS(data)
#         exit()
        normalizedUrl = data["crawlingElement"].data
        expandedUrl = data["crawlingElement"].extraData["twitter_expanded_url"]
        twitterUrl = data["crawlingElement"].extraData["twitter_url"]
        status = data["status"]
        if status == REQUEST_STATUS.success \
        or status == REQUEST_STATUS.error404 \
        or status == REQUEST_STATUS.timeoutWithContent:
            isToStore = None
            if status == REQUEST_STATUS.success:
                self.collection.deleteOne({"normalized_url": normalizedUrl})
                isToStore = True
            else:
                alreadyStored = self.collection.findOne({"normalized_url": normalizedUrl})
                if alreadyStored is None:
                    isToStore = True
                else:
                    if alreadyStored["status"] == "success":
                        isToStore = False
                    else:
                        self.collection.deleteOne({"normalized_url": normalizedUrl})
                        isToStore = True
            if isToStore:
                lastUrl = data["lastUrl"]
                html = data["html"]
                ns = NewsScraper(html)
                scrap = ns.scrapAll()
                toStore = {}
                toStore["normalized_url"] = normalizedUrl
                toStore["normalized_url_domain"] = self.urlParser.getDomain(normalizedUrl)
                toStore["status"] = status.name
                toStore["last_url"] = lastUrl
                toStore["last_url_domain"] = self.urlParser.getDomain(lastUrl)
                toStore["twitter_url"] = twitterUrl
                toStore["html"] = html
                toStore["scrap"] = scrap
                toStore["twitter_expanded_url"] = expandedUrl
                toStore["twitter_expanded_url_domain"] = self.urlParser.getDomain(expandedUrl)
                toStore["title"] = data["title"]
                toStore["crawling_version"] = __version__
                toStore = dictToMongoStorable(toStore)
                self.collection.insert(toStore)


# class TaoNewsUrlGeneratorFailed:
#     def __init__(self, mongoConnector):
#         self.mongoConnector = mongoConnector
#
#     def __iter__(self):
#         urlCount = 0
#         for current in self.mongoConnector.collection.find():
#             status = current["status"]
#             expandedUrl = current["twitter_expanded_url"]
#             normalizedUrl = current["normalized_url"]
#             twitterUrl = current["twitter_url"]
#             if status != "success":
#                 extraData = {"twitter_expanded_url": expandedUrl, "twitter_url": twitterUrl}
#                 toYield = CrawlingElement(normalizedUrl, extraData=extraData)
#                 yield toYield
#

class TaoNewsUrlGenerator:
    def __init__(self, dataPath, mongoConnector=None, doShuffle=True, maxUrls=None, doRandom=False, randomRate=0.69, logger=None, verbose=True):
        self.logger = logger
        self.verbose = verbose
        self.randomRate = randomRate
        self.doRandom = doRandom
        self.maxUrls = maxUrls
        self.doShuffle = doShuffle
        self.mongoConnector = mongoConnector
        self.taoUrlGenerator = NewsUrlGenerator(dataPath, doShuffle=self.doShuffle, logger=self.logger, verbose=self.verbose, unshortenerReadOnly=True)

    def __iter__(self):
        urlCount = 0
        for theDict in self.taoUrlGenerator:
            expandedUrl = theDict["twitter_expanded_url"]
            normalizedUrl = theDict["normalized_url"]
            twitterUrl = theDict["twitter_url"]
            if self.mongoConnector is None or not self.mongoConnector.normalizedUrlExists(normalizedUrl):
                if not self.doRandom or getRandomFloat() > self.randomRate:
                    extraData = {"twitter_expanded_url": expandedUrl, "twitter_url": twitterUrl}
                    toYield = CrawlingElement(normalizedUrl, extraData=extraData)
#                     logInfo(listToStr(toYield), logger)
                    yield toYield
                    urlCount += 1
                    if self.maxUrls is not None and urlCount > self.maxUrls:
                        break


def terminatedCallback(urlsFailedNotEnough, urlsFailedEnough):
    logInfo("urlsFailedNotEnough:", logger)
    logInfo(listToStr(urlsFailedNotEnough), logger)
    logInfo("urlsFailedEnough:", logger)
    logInfo(listToStr(urlsFailedEnough), logger)
    tt.toc()

# def failedCallback(crawlingElement):
#     tnug.popTwitterUrl(crawlingElement["data"])

if __name__ == '__main__':
    TEST = isHostname("hjlat")
    if TEST:
        logger = Logger("taonews-crawling-test.log")
    else:
        logger = Logger("taonews-crawling-prod.log", moWeightMax=100)
    logInfo("Starting...", logger)
    # Get all proxies:
    if TEST:
        proxiesPath = dataDir() + "/Misc/crawling/" + "proxies-test.txt"
    else:
        proxiesPath = dataDir() + "/Misc/crawling/" + "proxies-prod.txt"
    logInfo(listToStr(fileToStrList(proxiesPath)), logger)
    # Get mongo
    mongoConnector = MongoConnector("crawling", "taonews", onlySuccess=False) ###########
    # THE CRAWLER:
    tt = TicToc()
    tt.tic()
#     dataPath = dataDir() + "/TwitterArchiveOrg/Converted3.3/*.bz2"
    dataPath = dataDir() + "/TwitterArchiveOrg/Converted2/*.bz2"
    tnug = TaoNewsUrlGenerator(dataPath, mongoConnector, maxUrls=None, doRandom=False, randomRate=0.2, logger=logger)

#     for current in tnug:
#         print("--> " + current)
#     exit()

    if isHostname("hjlat"):
        browsersPhantomjsPath = None
        browsersHeadless = True
        driverType = DRIVER_TYPE.chrome
        browserCount = [2]
        parallelRequests = [2]
        useProxies = True
    elif isHostname("datas"):
        browsersPhantomjsPath = None
        browsersHeadless = True
        driverType = DRIVER_TYPE.chrome
        browserCount = [8]
        parallelRequests = [8]
#         browserCount = [50, 80, 120]
#         parallelRequests = [20, 60, 100]
        useProxies = True
    elif isHostname("tipi"):
        browsersPhantomjsPath = homeDir() + "/Programs/headlessbrowsers/phantomjs-2.1.1-linux-x86_64/bin/phantomjs"
        browsersHeadless = True
        driverType = DRIVER_TYPE.phantomjs
        browserCount = [50, 80, 120]
        parallelRequests = [20, 60, 100]
        useProxies = True

    crawler = Crawler \
    (
        tnug,
        paramsDomain = \
        {
            "proxyInstanciationRate":
            {
                "alpha": [0.05, 0.2, 0.5, 0.95, 0.99],
                "beta": [NormalizedLawBeta.LOG]
            },
            "browserCount": browserCount,
            "parallelRequests": parallelRequests,
        },
        proxiesPath=proxiesPath,
        pageLoadTimeout=30,
        crawlingCallback=mongoConnector.crawlingCallback,
        failedCallback=None,
        terminatedCallback=terminatedCallback,
        browsersVerbose=True,
        banditRoundDuration=300, # 500
        logger=logger,
        queueMinSize=50, # 300
        stopCrawlerAfterSeconds=300,
        maxRetryFailed=0,
        ajaxSleep=8.0,
        browserMaxDuplicatePerDomain=3,
        useProxies=useProxies,
        loadImages=True,
        browsersHeadless=browsersHeadless,
        browsersDriverType=driverType,
        browsersPhantomjsPath=browsersPhantomjsPath,
    )

    crawler.start()
    crawler.mainThread.join()

    # version 0.0.9 : starting of crawling all unshorted urls




