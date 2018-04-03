# coding: utf-8

# nn pew in newscrawler-venv python ~/wm-dist-tmp/NewsCrawler/newscrawler/crawltest.py


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
from databasetools.mongo import *
from machinelearning.function import *



def getUrlsInTmpFile():
    """
        Use this to sync the file:
        rsync -avhu -e "ssh -p 2222" hayj@octods:~/tmp/newsurl-list.txt ~/tmp/
    """
    (user, password, host) = getStudentMongoAuth()
    collection = MongoCollection("crawling", "taonews",
                                 user=user, password=password, host=host)
    urls = []
    for row in collection.find(projection={"last_url": True}):
#         if getRandomFloat() > 0.01:
        urls.append(row["last_url"])
        if len(urls) > 10000:
            break
        print(len(urls))
    result = ""
    for url in urls:
        result += url + "\n"
    strToTmpFile(result, "/newsurl-list.txt")

def getUrls():
    urls = fileToStrList(tmpDir() + "/newsurl-list.txt")
    random.shuffle(urls)
    return urls

def crawlingCallback(data, browser=None):
    global collection
    global logger
    url = data["url"]
    if "fake.com" not in url:
        if not collection.has(url):
            collection.insert(data)

def failedCallback(data):
    pass

def terminatedCallback(urlsFailedNotEnough, urlsFailedEnough):
    for text, currentFailed in [("urlsFailedNotEnough", urlsFailedNotEnough),
                                ("urlsFailedEnough", urlsFailedEnough)]:
        currentFailedText = ""
        for current in currentFailed:
            currentFailedText += str(current.data) + "\n"
        logInfo(text + ":\n" + currentFailedText, logger)


def scrapSimilarity(scrap1, scrap2, testOverlapThreshold=100, totalOverlapTest=200, wordSize=20):
    scrap1 = scrap1.strip()
    scrap2 = scrap2.strip()
    if len(scrap1) > len(scrap2):
        sizeSim = len(scrap2) / len(scrap1)
    else:
        sizeSim = len(scrap1) / len(scrap2)
    if sizeSim > 0.6 and len(scrap2) > testOverlapThreshold:
        success = 0
        for i in range(totalOverlapTest):
            startIndex = getRandomInt(len(scrap1) - wordSize * 2)
            endIndex = startIndex + wordSize
            word = scrap1[startIndex:endIndex]
            if word in scrap2:
                success += 1
        overlapSim = success / totalOverlapTest
    else:
        if scrap1 == scrap2:
            overlapSim = 1.0
        else:
            overlapSim = 0.0
    return (sizeSim + overlapSim * 3) / 4.0


def showAllScraps():
    scrapLib = NewsScraper.SCRAPLIB.newspaper
    (user, password, host) = getOctodsMongoAuth()
    phantomjs = MongoCollection("test",
                                 "phantomjs",
                                 user=user,
                                 password=password,
                                 host=host,
                                 giveTimestamp=False,
                                 indexOn="url")
    http = MongoCollection("test",
                             "http",
                             user=user,
                             password=password,
                             host=host,
                             giveTimestamp=False,
                             indexOn="url")
    (user, password, host) = getStudentMongoAuth()
    taonews = MongoCollection("crawling",
                                 "taonews",
                                 user=user,
                                 password=password,
                                 host=host)
    separation = "\n" * 3 + "-" * 200 + "\n" * 3
    for httpRow in http.find().skip(111):
#         phantomjsRow = phantomjs.findOne({"url": httpRow["url"]})
        taonewsRow = taonews.findOne({"last_url": httpRow["url"]})
        taonewsScrap = taonewsRow["scrap"]["newspaper"]["text"]

#         if phantomjsRow is not None:
        result = ""
        result += listToStr(reduceDictStr(httpRow))
        result += separation
#         result += listToStr(reduceDictStr(phantomjsRow))
#         result += separation
        ns = NewsScraper()
        httpScrap = ns.scrap(httpRow["html"], scrapLib=scrapLib)
        httpScrap = httpScrap["newspaper"]["text"]
        result += httpScrap
        result += separation
        result += taonewsScrap
        result += separation
#         ns = NewsScraper(phantomjsRow["html"])
#         phantomjsScrap = ns.scrap(scrapLib=scrapLib)
#         phantomjsScrap = phantomjsScrap["newspaper"]["text"]
#         result += listToStr(phantomjsScrap)
        scrapSim = scrapSimilarity(httpScrap, taonewsScrap)
        if scrapSim < 0.8:
            print("We found different scraps for " + httpRow["url"])
            strToTmpFile(result, "crawltest-data.txt")
            print("scrapSim=" + str(scrapSim))
            input()
        else:
            print("OK: " + httpRow["url"])
#         else:
#             pass
#             print("phantomjsRow is None for " + httpRow["url"])


def crawl():
    global collection
    global logger
    useHTTPBrowser = True
    collectionName = "http"
    if not useHTTPBrowser:
        collectionName = "phantomjs"
    (user, password, host) = getOctodsMongoAuth()
    collection = MongoCollection("test",
                                 collectionName,
                                 user=user,
                                 password=password,
                                 host=host,
                                 giveTimestamp=False,
                                 indexOn="url")
    collection.show()
    startUrls = getUrls()[0:5000]
    newStartUrls = []
    for current in startUrls:
        if not collection.has(current):
            newStartUrls.append(current)
    startUrls = newStartUrls


#     startUrls = []
#     for i in range(1000):
#         startUrls.append("http://fake.com/" + str(i))

#     collection.resetCollection()
    proxies = getProxiesTest()
    logger = Logger()
    # We init the crawler:
    crawlerVerbose = True
    parallelCount = [20, 150]
    crawler = Crawler \
    (
        startUrls,
        paramsDomain = \
        {
            "proxyInstanciationRate":
            {
                "alpha": [0.99],
                "beta": [NormalizedLawBeta.LOG]
            },
            "browserCount": parallelCount,
            "parallelRequests": parallelCount,
        },
        verbose=crawlerVerbose,
        proxies=proxies,
        pageLoadTimeout=30, # 30
        failedCallback=failedCallback,
        crawlingCallback=crawlingCallback,
        logger=logger,
        terminatedCallback=terminatedCallback,
        browsersVerbose=crawlerVerbose,
        banditRoundDuration=30, # 500
        queueMinSize=50, # 300
        stopCrawlerAfterSeconds=20,
        maxRetryFailed=2,
        browserMaxDuplicatePerDomain=20,
        useProxies=True,
        loadImages=True,
        browsersHeadless=True,
        browsersDriverType=DRIVER_TYPE.phantomjs,
        sameBrowsersParallelRequestsCount=True,
        afterAjaxSleepCallback=None,
        beforeGetCallback=None,
        browserUseFastError404Detection=True,
        firstRequestSleepMin=0.1,
        firstRequestSleepMax=5,
        allRequestsSleepMin=0.1,
        allRequestsSleepMax=0.3,
        httpBrowserParams=\
        {
            "maxRetryWithoutProxy": 0,
            "maxRetryIfTimeout": 1,
            "maxRetryIf407": 1,
            "portSet": ["80", "55555"],
            "retrySleep": 1.0,
        },
        useHTTPBrowser=useHTTPBrowser,
    )


    # We start the crawler and we end:
    crawler.start()
    crawler.mainThread.join()
    log("End.", logger)



collection = None
logger = None

if __name__ == '__main__':
    crawl()
#     showAllScraps()








# CONCLUSION
# Globalement HTTPBrowser a l'air d'etre meilleur,
# mais peut-être qu'il se fera bloquer plus facilement...


























