# coding: utf-8

import sys, os; sys.path.append("/".join(os.path.abspath(__file__).split("/")[0:-2]))

from datatools.url import *
from systemtools.basics import *
from systemtools.duration import *
from systemtools.file import *
from systemtools.logger import log, logInfo, logWarning, logError, Logger
from systemtools.location import *
from systemtools.hayj import *
from systemtools.system import *
from webcrawler.crawler import *
from hjwebbrowser.utils import *
from hjwebbrowser.browser import *
# from newstools.newsscraper import *
from databasetools.mongo import *
from newstools.newsurlfilter import *
from twitterarchiveorg.urlgenerator import *
from webcrawler.sample import __version__




def getUserCrawlDatascienceCollection():
    (user, password, host) = getMongoAuth(user="student", hostname="datascience01")
    collection = MongoCollection \
    (
        "twitter",
        "usercrawl",
        user=user, host=host, password=password,
        logger=logger,
    )
    return collection

def getShares(crawlOrScrap):
    if dictContains(crawlOrScrap, "scrap"):
        scrap = crawlOrScrap["scrap"]
    else:
        scrap = crawlOrScrap
    if dictContains(scrap, "tweets"):
        tweets = scrap["tweets"]
        for tweet in tweets:
            if dictContains(tweet, "shares"):
                for share in tweet["shares"]:
                    yield share

def getSharesUrls(crawlOrScrap):
    for share in getShares(crawlOrScrap):
        yield share["url"]

def test():
    collection = getUserCrawlDatascienceCollection()
    i = 0
    for crawl in collection.find():
        printLTS(list(getSharesUrls(crawl)))
        if i > 100:
            break
        i += 1

if __name__ == '__main__':

#     us = Unshortener()
#     us.
#
    logger = Logger("twitternewscrawler.log", remove=True)
#     proxies = getProxiesTest()
    test()
