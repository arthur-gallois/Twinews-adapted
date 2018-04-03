# coding: utf-8

# nn pew in newscrawler-venv python ~/wm-dist-tmp/NewsCrawler/newscrawler/crawler.py

import sys, os; sys.path.append("/".join(os.path.abspath(__file__).split("/")[0:-2]))

from datatools.url import *
from systemtools.basics import *
from systemtools.duration import *
from systemtools.file import *
from systemtools.logger import *
from systemtools.location import *
from systemtools.hayj import *
from systemtools.system import *
from webcrawler.crawler import *
from hjwebbrowser.utils import *
from hjwebbrowser.browser import *
from newstools.newsscraper import *
from machinelearning.function import *
from databasetools.mongo import *
try:
    from systemtools.hayj import *
except: pass
from newscrawler.twitteruser import *
from newscrawler.sharesgenerator import *
from newscrawler import __version__ as newsCrawlerVersion

def alreadyCrawledFunct(crawlingElement):
    try:
        url = crawlingElement.data
        if newscrawlHas(url):
            log("This url is already in newscrawl: " + url, logger)
            return True
    except Exception as e:
        logException(e, logger, location="alreadyCrawledFunct")
    return False

def alreadyFailedFunct(crawlingElement):
    try:
        url = crawlingElement.data
        if failsSD.has(url) and failsSD[url] > crawler.maxRetryFailed:
            log("Failed enough in failsSD: " + url, logger)
            return True
    except Exception as e:
        logException(e, logger, location="alreadyFailedFunct")
    return False

def failedCallback(data):
    try:
        url = data["crawlingElement"].data
        if failsSD.has(url):
            failsSD[url] += 1
        else:
            failsSD[url] = 1
        if "crawlingElement" in data:
            del data["crawlingElement"]
        failsDataSD[url] = data
    except Exception as e:
        logException(e, logger, location="failedCallback")

def terminatedCallback(urlsFailedNotEnough, urlsFailedEnough):
    for text, currentFailed in [("urlsFailedNotEnough", urlsFailedNotEnough),
                                ("urlsFailedEnough", urlsFailedEnough)]:
        currentFailedText = ""
        for current in currentFailed:
            currentFailedText += str(current.data) + "\n"
        logInfo(text + ":\n" + currentFailedText, logger)


def crawlingCallback(data, browser=None):
    try:
        if data is not None:
            if "crawlingElement" in data:
                del data["crawlingElement"]
            status = data["status"]
            if status in [REQUEST_STATUS.success,
                          REQUEST_STATUS.error404,
                          REQUEST_STATUS.timeoutWithContent]:
                addToNewscrawl(data)
    except Exception as e:
        logException(e, logger, location="crawlingCallback")

def newscrawlHas(url):
    return newscrawlCollection.has({"url": url})

def addToNewscrawl(data, fromUnshortener=False):
    """
        data can be a unshortener row or a httpbrowser response
    """
    try:
        # We remove some elements:
        if "crawlingElement" in data:
            del data["crawlingElement"]
        if "scrap" in data:
            del data["scrap"]
        if "isShortener" in data:
            del data["isShortener"]
        # We get additional data (the version and hostname are already
        # added by the MongoCollection instance):
        data["fromUnshortener"] = fromUnshortener
        try:
            data["scrap"] = newsScraper.scrapAll(data["html"], reduce=False)
        except Exception as e:
            logException(e, logger, location="addToNewscrawl newsScraper.srcapAll")
        # Now we insert it:
        url = data["url"]
        if not newscrawlHas(url):
            newscrawlCollection.insert(data)
            del failsSD[url]
    except Exception as e:
        logException(e, logger, location="addToNewscrawl")

class NewsCrawlerGenerator:
    def __init__(self, logger=None, verbose=True):
        self.logger = logger
        self.verbose = verbose
        self.newsSharesGenerator = NewsSharesGenerator(sharesGeneratorParams=\
        {
            "notBotThreshold": notBotThreshold,
            "relevanceThreshold": relevanceThreshold,
        }, logger=logger)
        self.nuf = NewsURLFilter(unshortenerReadOnly=newsCrawlerGeneratorUnshortenerReadOnly,
                                 logger=logger)
        self.uns = Unshortener(readOnly=True, logger=logger)

    def __iter__(self):
        # For each url:
        for url in self.newsSharesGenerator:
            if url is not None:
                # If this is a news:
                if self.nuf.isNews(url):
                    # And if we do not already crawled it:
                    if not newscrawlHas(url):
                        # If we already crawled it throw Unshortener, we add it:
                        gotItFromUnshortener = False
                        if self.uns.has(url):
                            data = self.uns.request(url)
                            if data is not None and dictContains(data, "html"):
                                addToNewscrawl(data, fromUnshortener=True)
                                gotItFromUnshortener = True
                        # Else we yield the url:
                        if not gotItFromUnshortener:
                            yield url

def testUrlsGenerator(max=300):
#     (user, password, host) = getStudentMongoAuth()
#     taonews = MongoCollection("crawling", "taonews",
#                               user=user, password=password, host=host)
#     i = 0
#     for current in taonews.find(projection={"last_url": 1}):
#         yield current["last_url"]
#         if i == max:
#             raise StopIteration()
#         i += 1
    return fileToStrList(dataDir() + "/Misc/crawling/news-samples/taonews.txt")

if __name__ == '__main__':
    # TEST:
    TEST = isHostname("hjlat")
    # Misc:
    logger = Logger("newscrawler.log")
    newsScraper = NewsScraper(logger=logger)
    # If we want to unshort some urls in good users (set it as False):
    newsCrawlerGeneratorUnshortenerReadOnly = True
    # To handle twitter user scores:
    notBotThreshold = 0.93
    relevanceThreshold = 0.6
    # Proxies:
    if TEST:
        proxies = getProxiesTest()
    else:
        proxies = getAllProxies()[0:100] # TODO set all proxies
        logWarning("WARNING: pls set all proxies!!!!!!!!!!!!!", logger)
    # Mongo collection:
    if TEST:
        (user, password, host) = (None, None, "localhost")
        dbName = "twitter"
        collectionName = "newscrawl-test"
    else:
        (user, password, host) = getOctodsMongoAuth()
        dbName = "twitter"
        collectionName = "newscrawl"
    # We create a failed SerializableDict to retain which url has failed
    # So we can try with other ips and Selenium if necessary:
    failsSD = SerializableDict\
    (
        "newscrawlfails",
        logger=logger,
        cacheCheckRatio=0.0,
        limit=100000000,
        useMongodb=True,
        user=user, password=password, host=host,
        mongoIndex="url",
    )
    failsDataSD = SerializableDict\
    (
        "newscrawlfailsdata",
        logger=logger,
        cacheCheckRatio=0.0,
        limit=1000,
        useMongodb=True,
        user=user, password=password, host=host,
        mongoIndex="url",
    )
    # All global elements:
    newscrawlCollection = MongoCollection\
    (
        dbName,
        collectionName,
        indexOn=["url"],
        indexNotUniqueOn=["lastUrlDomain"],
        user=user, password=password, host=host,
        version=newsCrawlerVersion,
        giveHostname=True,
        giveTimestamp=True,
        logger=logger,
    )
    if TEST:
        if "-test" in collectionName:
            pass
            # newscrawlCollection.resetCollection(security=False)
    # Urls:
    if TEST:
        urlsGen = testUrlsGenerator()
        urlsGen = ["http://bit.ly/2DVd8jm"] + urlsGen
    else:
        urlsGen = NewsCrawlerGenerator(logger=logger)
    # Crawler important params:
    banditRoundDuration = 300
    pageLoadTimeout = 45
    parallelRequests = [10, 20, 50] # TODO [20, 50, 100]
    logWarning("WARNING: pls set parallelRequests!!!!!!!!!!!!!", logger)
    queueMinSize = 300
    maxRetryFailed = 2
    browserMaxDuplicatePerDomain = 15
    loadImages = False
    firstRequestSleepMin = 10
    firstRequestSleepMax = 30
    allRequestsSleepMin = 1
    allRequestsSleepMax = 2
    alpha = [0.99, 0.5]
    maxRetryWithTor = 1
    if TEST:
        parallelRequests = [2]
        firstRequestSleepMin = 1
        firstRequestSleepMax = 2
        maxRetryFailed = 1
        pageLoadTimeout = 1
        banditRoundDuration = 30
    # We init tor services:
    torPortCount = 150
    if TEST:
        torPortCount = 2
    if maxRetryWithTor > 0:
    	getTorSingleton(portCount=torPortCount, logger=logger, verbose=True)
    # Crawler:
    crawler = Crawler \
    (
        urlsGen,
        paramsDomain = \
        {
            "proxyInstanciationRate":
            {
                "alpha": alpha,
                "beta": [NormalizedLawBeta.LOG]
            },
            "browserCount": parallelRequests,
            "parallelRequests": parallelRequests,
        },
        proxies=proxies,
        pageLoadTimeout=pageLoadTimeout,
        failedCallback=failedCallback,
        crawlingCallback=crawlingCallback,
        terminatedCallback=terminatedCallback,
        browsersVerbose=True,
        banditRoundDuration=banditRoundDuration,
        logger=logger,
        queueMinSize=queueMinSize,
        stopCrawlerAfterSeconds=1000,
        maxRetryFailed=maxRetryFailed,
        browserMaxDuplicatePerDomain=browserMaxDuplicatePerDomain,
        useProxies=True,
        loadImages=loadImages,
        sameBrowsersParallelRequestsCount=True,
        firstRequestSleepMin=firstRequestSleepMin,
        firstRequestSleepMax=firstRequestSleepMax,
        allRequestsSleepMin=allRequestsSleepMin,
        allRequestsSleepMax=allRequestsSleepMax,
        alreadyCrawledFunct=alreadyCrawledFunct,
        alreadyFailedFunct=alreadyFailedFunct,
        httpBrowserParams=\
        {
            "maxRetryWithoutProxy": 0,
            "maxRetryIfTimeout": 1,
            "maxRetryIf407": 1,
            "maxRetryWithTor": maxRetryWithTor,
            "portSet": ["80", "55555"],
            "retrySleep": 5.0,
        },
        useHTTPBrowser=True,
        allowRestartTor=maxRetryWithTor > 0,
    )

    # We start the crawler:
    crawler.start()

