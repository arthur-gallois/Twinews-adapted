# coding: utf-8

# nn pew in twitternewsrec-venv python ~/wm-dist-tmp/TwitterNewsrec/twitternewsrec/newscrawler/crawler.py ; observe nohup.out

import sys, os; sys.path.append("/".join(os.path.abspath(__file__).split("/")[0:-3]))

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
from twitternewsrec.user.twitteruser import *
from twitternewsrec.user.topuser import *
from twitternewsrec.newscrawler import __version__ as newsCrawlerVersion
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
                if unsRO.isShortened(url):
                    # We add the data to  the unshortener:
                    unsUsedToAddData.add(data)
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
                data["scrap"] = newsScraper.smartScrap(data["html"], reduce=False)
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

def failedYielder(minFailed=3, maxFailedCount=None, defaultMaxAddFactor=2):
    if maxFailedCount is None:
        maxFailedCount = int(minFailed * defaultMaxAddFactor)
    for url, data in failsSD.data.items():
        failedCount = data["value"]
        if maxFailedCount >= failedCount >= minFailed:
            if nufRO.isNews(url) or unsRO.isShortener(url):
                log("==> " + url + " <==", logger)
                yield url

def crawlingSharesYielder(yielder, *args, logger=None, verbose=True, **kwargs):
    for url in yielder(*args, logger=logger, shuffle=True, verbose=verbose, **kwargs):
        if url is not None and url not in newsAdded:
            if not newscrawlHas(url) and not alreadyFailedFunct(url):
                if unsRO.has(url):
                    data = unsRO.request(url)
                    if data is not None and dictContains(data, "html") and statusOK(data["status"]):
                        addToNewscrawl(data, fromUnshortener=True)
                    else:
                        yield url
                        newsAdded.add(url)
                else:
                    yield url
                    newsAdded.add(url)

def toCompleteCrawlingSharesYielder(*args, **kwargs):
    return crawlingSharesYielder(toCompleteSharesYielder, *args, **kwargs)
    
def toEstimateCrawlingSharesYielder(*args, **kwargs):
    return crawlingSharesYielder(toEstimateSharesYielder, *args, **kwargs)

def toCompleteOnlyNewsCrawlingSharesYielder(*args, **kwargs):
    return crawlingSharesYielder(toCompleteOnlyNewsSharesYielder, *args, **kwargs)


# Avant la grosse maj le 14 aout 2018 il y avait 531905 news et 24390 unshortened urls

STRATEGY = Enum("STRATEGY", "toComplete toCompleteOnlyNews toEstimate failed test")
if __name__ == '__main__':
    # CURRENT STRATEGY:
    theStrategy = STRATEGY.test
    if isHostname("hjlat"):
        theStrategy = STRATEGY.test
    elif isHostname("tipi"):
        # From 56 to 63
        tipiNumber = getFirstNumber(getHostname())
        if 56 <= tipiNumber <= 57:
            theStrategy = STRATEGY.toComplete
        elif 58 <= tipiNumber <= 59:
            theStrategy = STRATEGY.toEstimate
        elif 60 <= tipiNumber <= 61:
            theStrategy = STRATEGY.toComplete
        elif 62 <= tipiNumber <= 62:
            theStrategy = STRATEGY.failed
        else:
            print("Wrong tipi number.")
            exit()
    elif isHostname("datascience01"):
        theStrategy = STRATEGY.toCompleteOnlyNews
    # Logger:
    logger = Logger("newscrawler-" + getHostname() + "-" + str(theStrategy.name) + ".log")
    # Config:
    if theStrategy == STRATEGY.test:
        unsConfig.hostname = "localhost"
        unsConfig.host = "localhost"
        unsConfig.user = None
    if isHostname("tipi") or isHostname("datascience01"):
        from datastructuretools import config as dstConf
        (user, password, host) = getOctodsMongoAuth()
        dstConf.sdUser = user
        dstConf.sdPassword = password
        dstConf.sdHost = host
    # Proxies:
    if theStrategy == STRATEGY.test:
        proxies = getProxiesTest()
    else:
        proxies = getAllProxies() # TODO set all proxies
    # Mongo collection:
    if theStrategy == STRATEGY.test:
        (user, password, host) = (None, None, "localhost")
        dbName = "twitter"
        collectionName = "newscrawl-test"
    else:
        (user, password, host) = getOctodsMongoAuth()
        dbName = "twitter"
        collectionName = "newscrawl"
    # We init global vars:
    newsScraper = NewsScraper(logger=logger)
    nufRO = NewsURLFilter(unshortenerReadOnly=True, logger=logger)
    unsRO = Unshortener(readOnly=True, logger=logger)
    unsUsedToAddData = Unshortener(readOnly=False, logger=logger)
    if theStrategy == STRATEGY.test:
        unsUsedToAddData = unsRO
    newsDone = set()
    newsAdded = set()
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
    # We set the max fail:
    maxRetryFailed = 3 # IMPORTANT
    # We decrease fails:
    # try:
    #     if time.time() < 1534445417 and isHostname("datascience01"):
    #         logWarning("Decrementation of the failsSD...", logger)
    #         failsSD.data.update({"value": {"$gte": maxRetryFailed}}, {"$inc": {"value": -1}})
    # except Exception as e:
    #     logException(e, logger, location="failsSD inc")
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
    # We reset the collection:
    if theStrategy == STRATEGY.test:
        if "-test" in collectionName:
            pass
            # newscrawlCollection.resetCollection(security=False)
    # Selenium params:
    browsersDriverType = DRIVER_TYPE.phantomjs
    browsersHeadless = True
    ajaxSleep = 8
    # Crawler important params:
    # if theStrategy == STRATEGY.failed:
    #     maxRetryFailed = 5
    #     failsSD.data.update({"value": {"$gt": maxRetryFailed - 1}}, {"$inc": {"value": -1}})
    queueMinSize = 250
    banditRoundDuration = 300
    pageLoadTimeout = 50 # IMPORTANT
    if theStrategy == STRATEGY.test:
        pageLoadTimeout = 10
    if theStrategy == STRATEGY.toCompleteOnlyNews: # IMPORTANT
        if isHostname("datascience01"):
            parallelRequests = [25, 30, 35]
        else:
            parallelRequests = [20, 22, 24]
    elif theStrategy == STRATEGY.failed:
        parallelRequests = [10, 11, 12]
    elif theStrategy == STRATEGY.test:
        parallelRequests = [2]
    else:
        parallelRequests = [8, 12]
    browserMaxDuplicatePerDomain = 10
    if theStrategy == STRATEGY.failed:
        browserMaxDuplicatePerDomain = 5
    loadImages = False
    if theStrategy == STRATEGY.failed:
        loadImages = True
    firstRequestSleepMin = 1
    firstRequestSleepMax = 60
    if theStrategy == STRATEGY.test:
        firstRequestSleepMax = 10
    allRequestsSleepMin = 1
    allRequestsSleepMax = 3
    alpha = [0.99, 0.5]
    if theStrategy == STRATEGY.failed:
        maxRetryWithTor = 1
    if isHostname("datascience01"): # IMPORTANT
        maxRetryWithTor = 0
    elif isHostname("tipi"):
        maxRetryWithTor = 0
    else:
        maxRetryWithTor = 0
    browserCount = [int(parallelRequests[-1] * 3.5)]
    if theStrategy == STRATEGY.failed:
        browserCount = [int(parallelRequests[-1] * 1.5)]
    useHTTPBrowser = True
    if theStrategy == STRATEGY.failed:
        useHTTPBrowser = True # IMPORTANT SELENIUUUUUUUUM
    # We init tor services:
    torPortCount = 150
    if theStrategy == STRATEGY.test:
        torPortCount = 2
    wbConf.torPortCount = torPortCount
    # if maxRetryWithTor > 0:
    #     getTorSingleton(portCount=torPortCount, logger=logger, verbose=True)

    # Urls:
    if theStrategy == STRATEGY.test:
        # urlsGen = fileToStrList(execDir() + "/data/shortened-urls-sample.txt")[0:10]
        urlsGen = toCompleteCrawlingSharesYielder(logger=logger)
    elif theStrategy == STRATEGY.toComplete:
        urlsGen = toCompleteCrawlingSharesYielder(logger=logger)
    elif theStrategy == STRATEGY.toEstimate:
        urlsGen = toEstimateCrawlingSharesYielder(logger=logger)
    elif theStrategy == STRATEGY.toCompleteOnlyNews:
        urlsGen = toCompleteOnlyNewsCrawlingSharesYielder(logger=logger)
    elif theStrategy == STRATEGY.failed:
        urlsGen = failedYielder(minFailed=maxRetryFailed, maxFailedCount=8)
    log("STRATEGY: " + str(theStrategy.name), logger)


    # i = 0
    # for current in toCompleteCrawlingSharesYielder(logger=logger):
    #     print(current)
    #     i += 1
    #     if i > 2000:
    #         break
    # exit()


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
            "portSet": ["80"],
            "retrySleep": 5.0,
            "displayTorWarning": False,
        },
        useHTTPBrowser=useHTTPBrowser,
        allowRestartTor=maxRetryWithTor > 0,
        browsersDriverType=browsersDriverType,
        browsersHeadless=browsersHeadless,
        ajaxSleep=ajaxSleep,
    )

    # We start the crawler:
    crawler.start()

