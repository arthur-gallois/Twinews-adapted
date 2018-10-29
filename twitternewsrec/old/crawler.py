# coding: utf-8

# nn pew in newscrawler-venv python ~/wm-dist-tmp/NewsCrawler/newscrawler/crawler.py ; observe nohup.out

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
from systemtools.hayj import *
from newscrawler.twitteruser import *
from newscrawler.sharesgenerator import *
from newscrawler import __version__ as newsCrawlerVersion
from unshortener import config as unsConfig
from hjwebbrowser import config as wbConf

def alreadyCrawledFunct(crawlingElement):
    try:
        crawlingElement = tryUrlToCrawlingElement(crawlingElement)
        url = crawlingElement.data
        if newscrawlHas(url):
            log("This url is already in newscrawl: " + url, logger)
            return True
    except Exception as e:
        logException(e, logger, location="alreadyCrawledFunct")
    return False

def alreadyFailedFunct(crawlingElement):
    try:
        crawlingElement = tryUrlToCrawlingElement(crawlingElement)
        url = crawlingElement.data
        if failsSD.has(url) and failsSD[url] > maxRetryFailed:
            if getRandomFloat() > 0.95:
                log("Failed enough (and others): " + url, logger)
            return True
    except Exception as e:
        logException(e, logger, location="alreadyFailedFunct")
    return False

def failedCallback(data):
    try:
        url = data["url"]
        if failsSD.has(url):
            failsSD[url] += 1
        else:
            failsSD[url] = 1
        if "crawlingElement" in data:
            del data["crawlingElement"]
        failsDataSD[url] = data
        if failsSD[url] > maxRetryFailed:
            newsDone.add(url)
            printInfos("failed", url)
    except Exception as e:
        logException(e, logger, location="failedCallback")

def terminatedCallback(urlsFailedNotEnough, urlsFailedEnough):
    for text, currentFailed in [("urlsFailedNotEnough", urlsFailedNotEnough),
                                ("urlsFailedEnough", urlsFailedEnough)]:
        currentFailedText = ""
        for current in currentFailed:
            currentFailedText += str(current.data) + "\n"
        logInfo(text + ":\n" + currentFailedText, logger)

def printInfos(message=None, url=None):
    pass
#     if message is None:
#         message = ""
#     if url is None:
#         url = ""
#     if len(url + message) > 0:
#         log("printInfos: " + message + " " + url, logger)
#     log("newsDone size: " + str(len(newsDone)), logger)
#     log("newsAdded size: " + str(len(newsAdded)), logger)
#     log("crawler.queue size: " + str(crawler.queue.size()), logger)
#     log("crawler.processing size: " + str(len(crawler.processing)), logger)
#     log("crawler.browsers size: " + str(crawler.browsers.size()), logger)

def statusOK(status):
    if status is None:
        return False
    else:
        if not isinstance(status, str):
            status = status.name
        return status in\
        [
            REQUEST_STATUS.success.name,
            REQUEST_STATUS.error404.name,
            REQUEST_STATUS.timeoutWithContent.name,
        ]

def crawlingCallback(data, browser=None):
    try:
        if data is not None:
            if "crawlingElement" in data:
                del data["crawlingElement"]
            status = data["status"]
            # We log infos:
            url = data["url"]
            newsDone.add(url)
            printInfos("success", url)
            # if the status is ok:
            if statusOK(status):
                lastUrl = data["lastUrl"]
                # If this is a shortened url:
                if uns.isShortened(url):
                    # We add the data to  the unshortener:
                    uns.add(data)
                # If this is a news:
                if nufRO.isNews(lastUrl) or nufRO.isNews(url):
                    # And we add the news to the collection:
                    addToNewscrawl(data)
#                 if not uns.isShortened(url) and not nuf.isNews(lastUrl):
#                     logError("We got data from the crawler which is not a shortened url and not a news:" + lts(reduceDictStr(data)), logger)
    except Exception as e:
        logException(e, logger, location="crawlingCallback")

def newscrawlHas(url):
    return newscrawlCollection.has({"url": url})

def addToNewscrawl(data, fromUnshortener=False):
    """
        data can be a unshortener row or a httpbrowser response
    """
    try:
        data = copy.deepcopy(data)
        if statusOK(data["status"]):
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
        else:
            if "html" in data:
                del data["html"]
            logError("The status of\n" + lts(data) + "\nis not OK.", logger)
    except Exception as e:
        logException(e, logger, location="addToNewscrawl")


class NewsCrawlerGenerator:
    def __init__(self, logger=None, verbose=True, skipFactor=0.8, skipAmountAtStart=None):
        self.logger = logger
        self.verbose = verbose
        self.newsSharesGenerator = NewsSharesGenerator(sharesGeneratorParams=\
        {
            "notBotThreshold": notBotThreshold,
            "relevanceThreshold": relevanceThreshold,
        }, logger=logger)
        if newsCrawlerGeneratorUnshortenerReadOnly:
            self.nuf = nufRO
        else:
            self.nuf = nuf
        self.uns = unsRO
        self.skipFactor = skipFactor
        self.skipAmountAtStart = skipAmountAtStart
        if self.skipAmountAtStart is None:
            self.skipAmountAtStart = 0

    def __iter__(self):
        # For each url:
        urlCount = 0
        for url in self.newsSharesGenerator:
            urlCount += 1
            if urlCount % 1000 == 0:
                log("urlCount=" + str(urlCount), logger)
            if urlCount > self.skipAmountAtStart and getRandomFloat() > self.skipFactor:
                if url is not None and url not in newsAdded:
                    # If this is a news:
                    if self.nuf.isNews(url):
                        # And if we do not already crawled it:
                        if not newscrawlHas(url) and not alreadyFailedFunct(url):
                            # If we already crawled it through Unshortener, we add it:
                            gotItFromUnshortener = False
                            if self.uns.has(url):
                                data = self.uns.request(url)
                                if data is not None and dictContains(data, "html"):
                                    addToNewscrawl(data, fromUnshortener=True)
                                    gotItFromUnshortener = True
                            # Else we yield the url:
                            if not gotItFromUnshortener:
                                yield url
                                newsAdded.add(url)
                                printInfos("added", url)

class ShortenedUrlGenerator:
    def __init__(self, logger=None, verbose=True, maxShortenedUrlPerUser=4):
        self.maxShortenedUrlPerUser = maxShortenedUrlPerUser
        self.logger = logger
        self.verbose = verbose
        self.users = getShortenerLovers(verbose=False)
        self.uns = unsRO

    def __iter__(self):
        # For each user:
        for (userId, score) in self.users:
            currentUserUrlCount = 0
            # For each user, we get all shortened urls:
            currentUrls = set()
            for url in UserSharesGenerator(userId):
                if self.uns.isShortener(url):
                    currentUrls.add(url)
            # We count the number of urls which is already crawler:
            alreadyCrawledUrls = []
            notAlreadyCrawledUrls = []
            for url in currentUrls:
                if self.uns.has(url):
                    alreadyCrawledUrls.append(url)
                else:
                    notAlreadyCrawledUrls.append(url)
            # We get urls to yield:
            urlsToYield = []
            if len(alreadyCrawledUrls) >= self.maxShortenedUrlPerUser:
                continue
            else:
                urlsToCrawlAmount = self.maxShortenedUrlPerUser - len(alreadyCrawledUrls)
                for i in range(urlsToCrawlAmount):
                    if i < len(notAlreadyCrawledUrls):
                        urlsToYield.append(notAlreadyCrawledUrls[i])
            # We yield all:
            for current in urlsToYield:
                yield current
#             # We log all:
#             log("---------------", self)
#             log("userId, score: " + str(userId) + ", " + str(score), self)
#             log("alreadyCrawledUrls: " + lts(alreadyCrawledUrls), self)
#             log("notAlreadyCrawledUrls: " + lts(notAlreadyCrawledUrls), self)
#             log("urlsToYield: " + lts(urlsToYield), self)
#             log("---------------\n\n\n", self)

def failedYielder(minFailed=2):
    for url, data in failsSD.data.items():
        failedCount = data["value"]
        if failedCount >= minFailed:
            yield url

def testUnshortenerGenerator(max=300):
    count = 0
    for url in ShortenedUrlGenerator():
        print(url)
        count += 1
        if count >= max:
            break


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

STRATEGY = Enum("STRATEGY", "shortened news newsskip failed test")

if __name__ == '__main__':
    # CURRENT STRATEGY:
    theStrategy = STRATEGY.news
    TEST = False
    if isHostname("hjlat"):
        theStrategy = STRATEGY.test
        TEST = True
    if isHostname("tipi58"):
        theStrategy = STRATEGY.shortened
    elif isHostname("tipi57"):
        theStrategy = STRATEGY.failed
    elif isHostname("tipi59"):
        theStrategy = STRATEGY.newsskip
    elif isHostname("datascience01"):
        theStrategy = STRATEGY.news
    # Config:
    if TEST:
        unsConfig.hostname = "localhost"
        unsConfig.host = "localhost"
        unsConfig.user = None
    if isHostname("tipi"):
        from datastructuretools import config as dstConf
        (user, password, host) = getOctodsMongoAuth()
        dstConf.sdUser = user
        dstConf.sdPassword = password
        dstConf.sdHost = host
    # Misc:
    logger = Logger("newscrawler-" + getHostname() + "-" + str(theStrategy.name) + ".log")
    newsScraper = NewsScraper(logger=logger)
    # If we want to unshort some urls in good users (set it as False):
    newsCrawlerGeneratorUnshortenerReadOnly = True
    # To handle twitter user scores:
    notBotThreshold = 0.6
    relevanceThreshold = 0.6
    # Proxies:
    if TEST:
        proxies = getProxiesTest()
    else:
#         proxies = getProxiesRenew() # TODO set all proxies
        proxies = getAllProxies() # TODO set all proxies
#         logWarning("WARNING: pls set all proxies!!!!!!!!!!!!!", logger)
    # Mongo collection:
    if TEST:
        (user, password, host) = (None, None, "localhost")
        dbName = "twitter"
        collectionName = "newscrawl-test"
    else:
        (user, password, host) = getOctodsMongoAuth()
        dbName = "twitter"
        collectionName = "newscrawl"
    # We init global nuf and uns:
    nufRO = NewsURLFilter(unshortenerReadOnly=True,
                                 logger=logger)
    unsRO = Unshortener(readOnly=True, logger=logger)
    nuf = NewsURLFilter(unshortenerReadOnly=False,
                                 logger=logger)
    uns = Unshortener(readOnly=False, logger=logger)
    # Test:
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
    try:
        pass
#         failsSD.data.update({"value": {"$gt": 1}}, {"$inc": {"value": -1}})
    except Exception as e:
        logException(e, logger, location="failsSD inc")
    # Specific config:

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

    # We create some sets to retain which url done and added
    newsDone = set()
    newsAdded = set()
    # Selenium params:
    browsersDriverType = DRIVER_TYPE.phantomjs
    browsersHeadless = True
    ajaxSleep = 8
    # Crawler important params:
    maxRetryFailed = 2 # IMPORTANT
    if theStrategy == STRATEGY.failed:
        maxRetryFailed = 5
        failsSD.data.update({"value": {"$gt": maxRetryFailed - 1}}, {"$inc": {"value": -1}})
    banditRoundDuration = 300
    pageLoadTimeout = 50
    parallelRequests = [20, 30, 40] # TODO [20, 50, 100]
    if theStrategy == STRATEGY.failed:
        parallelRequests = [10, 30]
    elif theStrategy == STRATEGY.shortened:
        parallelRequests = [10, 20]
    queueMinSize = 500
    browserMaxDuplicatePerDomain = 10
    if theStrategy == STRATEGY.failed:
        browserMaxDuplicatePerDomain = 5
    loadImages = False
    if theStrategy == STRATEGY.failed:
        loadImages = True
    firstRequestSleepMin = 1
    firstRequestSleepMax = 50
    allRequestsSleepMin = 1
    allRequestsSleepMax = 8
    alpha = [0.99, 0.5]
    maxRetryWithTor = 2
    if theStrategy == STRATEGY.failed:
        maxRetryWithTor = 0
    if TEST:
        parallelRequests = [1]
        firstRequestSleepMin = 1
        firstRequestSleepMax = 2
        maxRetryFailed = 1
        pageLoadTimeout = 1
        banditRoundDuration = 30
    browserCount = [int(parallelRequests[-1] * 2.2)]
    if theStrategy == STRATEGY.failed:
        browserCount = [int(parallelRequests[-1] * 1.5)]
    useHTTPBrowser = True
    if theStrategy == STRATEGY.failed:
        useHTTPBrowser = False
    # We init tor services:
    torPortCount = 150
    if TEST:
        torPortCount = 2
    if theStrategy == STRATEGY.failed:
        torPortCount = 0
    wbConf.torPortCount = torPortCount
#     if maxRetryWithTor > 0:
#         getTorSingleton(portCount=torPortCount, logger=logger, verbose=True)

    # Urls:
    if theStrategy == STRATEGY.test:
        urlsGen = fileToStrList(execDir() + "/data/shortened-urls-sample.txt")[0:10]
#         urlsGen = testUrlsGenerator()
#         urlsGen = ["http://bit.ly/2DVd8jm"] + urlsGen
#         if isHostname("tipi"):
#             urlsGen = ShortenedUrlGenerator(logger=logger)
#         else:
#         urlsGen = NewsCrawlerGenerator(logger=logger, skipAmountAtStart=400000)
    elif theStrategy == STRATEGY.shortened:
        urlsGen = ShortenedUrlGenerator(logger=logger)
    elif theStrategy == STRATEGY.failed:
        urlsGen = failedYielder()
    elif theStrategy == STRATEGY.newsskip:
        urlsGen = NewsCrawlerGenerator(logger=logger, skipAmountAtStart=getRandomInt(200000, 400000))
    elif theStrategy == STRATEGY.news:
        urlsGen = NewsCrawlerGenerator(logger=logger)
    log("STRATEGY: " + str(theStrategy.name), logger)


#     allUrlsSD = SerializableDict("allUrlsSD")
#     for current in urlsGen:
#         if current not in allUrlsSD:
#             if not alreadyCrawledFunct(current) and not alreadyFailedFunct(current):
#                 allUrlsSD[current] = True
#                 if len(allUrlsSD) % 500 == 0:
#                     log(str(len(allUrlsSD)), logger)
#                     log(str(current), logger)
#     allUrlsSD.save()
#     log("Final news count: " + str(len(allUrlsSD)), logger)
#     exit()

#     for current in urlsGen:
#         log(current, logger)
#     exit()

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
            "browserCount": browserCount,
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
        sameBrowsersParallelRequestsCount=False,
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
        useHTTPBrowser=useHTTPBrowser,
        allowRestartTor=maxRetryWithTor > 0,
        browsersDriverType=browsersDriverType,
        browsersHeadless=browsersHeadless,
        ajaxSleep=ajaxSleep,
    )

    # We start the crawler:
    crawler.start()

